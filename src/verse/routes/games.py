"""Games: quiz, guess member, oshi sorter, leaderboard — scoring otoritatif server."""

import random
import secrets
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.models import (
    ActivityLog, GameScore, GameSession, GuessQuestion, Member,
    Notification, QuizQuestion, SorterResult, User,
)
from src.verse.deps import get_viewer, require_user
from src.verse.helpers import now_utc, wib_date_key, wib_midnight, wib_parts

router = APIRouter()

QUIZ_COUNT = {"easy": 10, "medium": 20, "hard": 30}
QUIZ_POINTS = {"easy": 30, "medium": 60, "hard": 90}


def _shuffle(arr):
    a = list(arr)
    random.shuffle(a)
    return a


async def _record_score(session: AsyncSession, user_seq: int, game: str, score: int, detail: str):
    session.add(GameScore(user_seq=user_seq, game=game, score=score, detail=detail))
    user = (
        await session.execute(select(User).where(User.seq == user_seq))
    ).scalar_one_or_none()
    if not user:
        return
    today = wib_date_key()
    streak = user.streak
    bonus = 0
    if user.last_daily_date != today:
        yesterday = wib_date_key(now_utc() - timedelta(days=1))
        if str(user.last_daily_date) == yesterday:
            streak = user.streak + 1
        else:
            streak = 1
        if streak == 7:
            bonus = 50
        if streak == 30:
            bonus = 200
        if streak == 100:
            bonus = 1000
        if bonus:
            session.add(GameScore(user_seq=user_seq, game="daily", score=bonus, detail=f"streak {streak}"))
            session.add(
                Notification(
                    user_seq=user_seq,
                    type="GAME_BADGE",
                    title=f"Streak {streak} hari! +{bonus} poin",
                    href="/games",
                )
            )
    user.points = (user.points or 0) + score + bonus
    user.streak = streak
    user.last_daily_date = __import__("datetime").date.fromisoformat(today)
    session.add(ActivityLog(user_seq=user_seq, action=f"game:{game}", detail=f"{score} poin ({detail})"))


# ===================== QUIZ =====================
@router.post("/games/quiz/start")
async def start_quiz(
    level: str = "easy",
    viewer: dict = Depends(get_viewer),
    session: AsyncSession = Depends(get_session),
):
    lv = level if level in QUIZ_COUNT else "easy"
    pool = (
        await session.execute(select(QuizQuestion).where(QuizQuestion.active.is_(True)))
    ).scalars().all()
    if not pool:
        return {"ok": False, "error": "Bank soal kosong."}
    preferred = _shuffle([q for q in pool if q.level == lv])
    filler = _shuffle([q for q in pool if q.level != lv])
    chosen = (preferred + filler)[: QUIZ_COUNT[lv]]
    ids = [q.id for q in chosen]
    gid = secrets.token_hex(12)
    session.add(
        GameSession(
            id=gid,
            user_seq=viewer.get("userId"),
            game="quiz",
            level=lv,
            question_ids=ids,
        )
    )
    q = chosen[0]
    return {
        "ok": True,
        "data": {
            "sessionId": gid,
            "level": lv,
            "q": _quiz_view(q, 0, len(ids)),
        },
    }


def _quiz_view(q, index: int, total: int) -> dict:
    return {
        "id": q.id,
        "question": q.question,
        "options": q.options or [],
        "index": index,
        "total": total,
        "category": q.category,
    }


class QuizAnswerIn(BaseModel):
    sessionId: str
    questionId: int
    answerIndex: int


@router.post("/games/quiz/answer")
async def answer_quiz(data: QuizAnswerIn, session: AsyncSession = Depends(get_session)):
    s = await session.get(GameSession, data.sessionId)
    if not s or s.finished:
        return {"ok": False, "error": "Sesi tidak valid."}
    qid = (s.question_ids or [])[s.current_index]
    if qid != data.questionId:
        return {"ok": False, "error": "Urutan soal tidak sesuai."}
    q = await session.get(QuizQuestion, qid)
    secs = (now_utc() - (s.question_shown_at or now_utc())).total_seconds()
    correct = q.correct_index == data.answerIndex
    base = QUIZ_POINTS.get(s.level or "easy", 30)
    gained = base + max(0, 10 - int(secs / 3)) if correct else 0
    next_index = s.current_index + 1
    finished = next_index >= len(s.question_ids or [])
    score = s.score + gained
    s.score = score
    s.correct = s.correct + (1 if correct else 0)
    s.current_index = next_index
    s.finished = finished
    s.question_shown_at = now_utc()
    next_q = None
    if not finished:
        nq = await session.get(QuizQuestion, s.question_ids[next_index])
        next_q = _quiz_view(nq, next_index, len(s.question_ids))
    elif s.user_seq:
        await _record_score(session, s.user_seq, "quiz", score, f"level {s.level}")
    return {
        "ok": True,
        "data": {
            "correct": correct,
            "correctIndex": q.correct_index,
            "gained": gained,
            "score": score,
            "next": next_q,
            "finished": finished,
        },
    }


# ===================== GUESS MEMBER =====================
async def _guess_view(session: AsyncSession, gid: str) -> Optional[dict]:
    s = await session.get(GameSession, gid)
    if not s:
        return None
    g = await session.get(GuessQuestion, (s.question_ids or [])[s.current_index])
    m = await session.get(Member, g.member_id)
    others_rows = (
        await session.execute(
            select(Member.id, Member.name)
            .where(Member.status.in_(["regular", "trainee"]), Member.id != m.id)
            .limit(200)
        )
    ).all()
    others = [{"id": r.id, "name": r.name} for r in _shuffle(others_rows)[:5]]
    seed = (s.question_ids or [])[s.current_index] % 6
    opts = [*others[:seed], {"id": m.id, "name": m.name}, *others[seed:]]
    import re as _re

    jiko = m.jikoshoukai or ""
    if m.nickname:
        jiko = _re.sub(_re.escape(m.nickname), "▮▮▮", jiko, flags=_re.IGNORECASE)
    first = m.name.split(" ")[0]
    jiko = _re.sub(_re.escape(first), "▮▮▮", jiko, flags=_re.IGNORECASE)
    return {
        "sessionId": gid,
        "jiko": jiko,
        "hints": (g.hints or [])[: s.hints_used],
        "hintsUsed": s.hints_used,
        "options": [{"id": o["id"], "name": o["name"]} for o in opts],
        "index": s.current_index,
        "total": len(s.question_ids or []),
        "score": s.score,
    }


@router.post("/games/guess/start")
async def start_guess(viewer: dict = Depends(get_viewer), session: AsyncSession = Depends(get_session)):
    pool = (
        await session.execute(
            select(GuessQuestion)
            .join(Member, Member.id == GuessQuestion.member_id)
            .where(GuessQuestion.active.is_(True), Member.status.in_(["regular", "trainee"]))
        )
    ).scalars().all()
    if len(pool) < 4:
        return {"ok": False, "error": "Bank soal Guess Member belum cukup."}
    chosen = _shuffle([g.id for g in pool])[:5]
    gid = secrets.token_hex(12)
    session.add(
        GameSession(id=gid, user_seq=viewer.get("userId"), game="guess", question_ids=chosen)
    )
    await session.flush()
    return {"ok": True, "data": await _guess_view(session, gid)}


class SessionIn(BaseModel):
    sessionId: str


@router.post("/games/guess/hint")
async def guess_hint(data: SessionIn, session: AsyncSession = Depends(get_session)):
    s = await session.get(GameSession, data.sessionId)
    if not s or s.finished:
        return {"ok": False, "error": "Sesi tidak valid."}
    if s.hints_used >= 3:
        return {"ok": False, "error": "Maksimal 3 hint."}
    s.hints_used += 1
    await session.flush()
    return {"ok": True, "data": await _guess_view(session, data.sessionId)}


class GuessAnswerIn(BaseModel):
    sessionId: str
    memberId: int


@router.post("/games/guess/answer")
async def answer_guess(data: GuessAnswerIn, session: AsyncSession = Depends(get_session)):
    s = await session.get(GameSession, data.sessionId)
    if not s or s.finished:
        return {"ok": False, "error": "Sesi tidak valid."}
    g = await session.get(GuessQuestion, (s.question_ids or [])[s.current_index])
    m = await session.get(Member, g.member_id)
    secs = (now_utc() - (s.question_shown_at or now_utc())).total_seconds()
    correct = m.id == data.memberId
    gained = (max(0, 100 - 20 * s.hints_used) + max(0, 20 - int(secs))) if correct else 0
    next_index = s.current_index + 1
    finished = next_index >= len(s.question_ids or [])
    score = s.score + gained
    s.score = score
    s.correct = s.correct + (1 if correct else 0)
    s.current_index = next_index
    s.finished = finished
    s.hints_used = 0
    s.question_shown_at = now_utc()
    if finished and s.user_seq:
        await _record_score(session, s.user_seq, "guess", score, "5 soal")
    next_view = None if finished else await _guess_view(session, data.sessionId)
    return {
        "ok": True,
        "data": {
            "correct": correct,
            "answer": m.name,
            "gained": gained,
            "score": score,
            "finished": finished,
            "next": next_view,
        },
    }


# ===================== SORTER =====================
class SorterIn(BaseModel):
    ranking: list[int]


@router.post("/games/sorter")
async def save_sorter(
    data: SorterIn,
    viewer: dict = Depends(require_user),
    session: AsyncSession = Depends(get_session),
):
    session.add(SorterResult(user_seq=viewer["userId"], ranking=data.ranking[:100]))
    session.add(
        ActivityLog(user_seq=viewer["userId"], action="sorter", detail=f"{len(data.ranking)} member")
    )
    return {"ok": True}


# ===================== LEADERBOARD =====================
@router.get("/games/leaderboard/daily")
async def daily_leaderboard(
    game: Optional[str] = None, limit: int = 10, session: AsyncSession = Depends(get_session)
):
    p = wib_parts()
    start = wib_midnight(p["year"], p["month"], p["day"])
    conds = [GameScore.created_at >= start]
    if game:
        conds.append(GameScore.game == game)
    rows = (
        await session.execute(
            select(
                GameScore.user_seq,
                User.username,
                User.avatar_seed,
                User.streak,
                func.sum(GameScore.score).label("total"),
            )
            .join(User, User.seq == GameScore.user_seq)
            .where(and_(*conds))
            .group_by(GameScore.user_seq, User.username, User.avatar_seed, User.streak)
            .order_by(desc(func.sum(GameScore.score)))
            .limit(limit)
        )
    ).all()
    return [
        {
            "userId": r.user_seq,
            "username": r.username,
            "avatarSeed": r.avatar_seed,
            "streak": r.streak,
            "total": int(r.total or 0),
        }
        for r in rows
    ]


@router.get("/games/leaderboard/all-time")
async def all_time_leaderboard(
    game: str, limit: int = 20, session: AsyncSession = Depends(get_session)
):
    rows = (
        await session.execute(
            select(
                GameScore.user_seq,
                User.username,
                User.avatar_seed,
                User.streak,
                func.sum(GameScore.score).label("total"),
                func.count().label("plays"),
            )
            .join(User, User.seq == GameScore.user_seq)
            .where(GameScore.game == game)
            .group_by(GameScore.user_seq, User.username, User.avatar_seed, User.streak)
            .order_by(desc(func.sum(GameScore.score)))
            .limit(limit)
        )
    ).all()
    return [
        {
            "userId": r.user_seq,
            "username": r.username,
            "avatarSeed": r.avatar_seed,
            "streak": r.streak,
            "total": int(r.total or 0),
            "plays": int(r.plays or 0),
        }
        for r in rows
    ]


@router.get("/games/{game}/players")
async def player_count(game: str, session: AsyncSession = Depends(get_session)):
    n = (
        await session.execute(
            select(func.count(func.distinct(GameScore.user_seq))).where(GameScore.game == game)
        )
    ).scalar() or 0
    return {"n": n}
