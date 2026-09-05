"""Konten: members, schedules, news, birthday, encyclopedia, glossary, motivations, search."""

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import and_, asc, desc, extract, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.models import (
    BirthdayWish, Encyclopedia, Glossary, Member, Motivation, News,
    Schedule, ScheduleMember, Contributor,
)
from src.verse import moderation
from src.verse.deps import require_user
from src.verse.helpers import (
    member_dict, news_dict, now_utc, schedule_dict, wib_midnight, wib_parts,
)

router = APIRouter()


# ===================== MEMBERS =====================
@router.get("/members")
async def list_members(
    status: Optional[str] = None,
    generation: Optional[int] = None,
    sort: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    conds = []
    if status in (None, "", "active"):
        conds.append(Member.status.in_(["regular", "trainee"]))
    elif status != "all":
        conds.append(Member.status == status)
    if generation:
        conds.append(Member.generation == generation)
    order = [asc(Member.name)]
    if sort == "generation":
        order = [asc(Member.generation), asc(Member.name)]
    elif sort == "status":
        order = [asc(Member.status), asc(Member.name)]
    rows = (
        await session.execute(
            select(Member).where(and_(*conds) if conds else True).order_by(*order)
        )
    ).scalars().all()
    return [member_dict(m) for m in rows]


@router.get("/members/id/{member_id}")
async def get_member_by_id(member_id: int, session: AsyncSession = Depends(get_session)):
    m = await session.get(Member, member_id)
    return member_dict(m) if m else None


@router.get("/members/slug/{slug}")
async def get_member_by_slug(slug: str, session: AsyncSession = Depends(get_session)):
    m = (
        await session.execute(select(Member).where(Member.slug == slug))
    ).scalar_one_or_none()
    if not m:
        return None
    d = member_dict(m)
    ids = (
        await session.execute(
            select(ScheduleMember.member_id, Schedule.id)
            .join(Schedule, Schedule.id == ScheduleMember.schedule_id)
            .where(ScheduleMember.member_id == m.id, Schedule.start_at >= now_utc())
            .order_by(asc(Schedule.start_at))
            .limit(10)
        )
    ).all()
    d["upcomingScheduleIds"] = [r[1] for r in ids]
    return d


@router.get("/members/id/{member_id}/schedules")
async def member_schedules(member_id: int, session: AsyncSession = Depends(get_session)):
    rows = (
        await session.execute(
            select(Schedule)
            .join(ScheduleMember, ScheduleMember.schedule_id == Schedule.id)
            .where(ScheduleMember.member_id == member_id, Schedule.start_at >= now_utc())
            .order_by(asc(Schedule.start_at))
            .limit(10)
        )
    ).scalars().all()
    return [schedule_dict(s) for s in rows]


# ===================== SCHEDULES =====================
@router.get("/schedules/upcoming")
async def upcoming_schedules(
    limit: int = 5, type: Optional[str] = None, session: AsyncSession = Depends(get_session)
):
    conds = [Schedule.start_at >= now_utc()]
    if type:
        conds.append(Schedule.type == type)
    rows = (
        await session.execute(
            select(Schedule).where(and_(*conds)).order_by(asc(Schedule.start_at)).limit(limit)
        )
    ).scalars().all()
    return [schedule_dict(s) for s in rows]


@router.get("/schedules/range")
async def schedules_in_range(
    start: str,
    end: str,
    type: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    from src.verse.helpers import dt

    conds = [Schedule.start_at >= dt(start), Schedule.start_at <= dt(end)]
    if type:
        conds.append(Schedule.type == type)
    rows = (
        await session.execute(
            select(Schedule).where(and_(*conds)).order_by(asc(Schedule.start_at))
        )
    ).scalars().all()
    return [schedule_dict(s) for s in rows]


@router.get("/schedules/{schedule_id}")
async def get_schedule(schedule_id: int, session: AsyncSession = Depends(get_session)):
    s = await session.get(Schedule, schedule_id)
    if not s:
        return None
    member_ids = (
        await session.execute(
            select(ScheduleMember.member_id).where(ScheduleMember.schedule_id == schedule_id)
        )
    ).scalars().all()
    out = schedule_dict(s, member_ids=list(member_ids))
    lineup = (
        await session.execute(
            select(Member)
            .join(ScheduleMember, ScheduleMember.member_id == Member.id)
            .where(ScheduleMember.schedule_id == schedule_id)
        )
    ).scalars().all()
    out["lineup"] = [member_dict(m) for m in lineup]
    import re as _re

    words = [w for w in _re.split(r"\s+", (s.title or "")) if len(w) > 4][:4]
    rel_conds = [
        or_(News.title.ilike(f"%{w}%"), News.summary.ilike(f"%{w}%"), News.body.ilike(f"%{w}%"))
        for w in words
    ]
    stmt = select(News)
    if rel_conds:
        stmt = stmt.where(or_(*rel_conds))
    related = (await session.execute(stmt.order_by(desc(News.published_at)).limit(4))).scalars().all()
    out["related"] = [news_dict(n) for n in related]
    return out


# ===================== NEWS =====================
@router.get("/news")
async def list_news(
    category: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    q: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    conds = []
    if category and category not in ("latest", "all"):
        conds.append(News.category == category)
    if q:
        like = f"%{q[:80]}%"
        conds.append(or_(News.title.ilike(like), News.body.ilike(like), News.summary.ilike(like)))
    rows = (
        await session.execute(
            select(News)
            .where(and_(*conds) if conds else True)
            .order_by(desc(News.published_at))
            .offset(offset)
            .limit(min(limit, 100))
        )
    ).scalars().all()
    return [news_dict(n) for n in rows]


@router.get("/news/highlighted")
async def highlighted_news(session: AsyncSession = Depends(get_session)):
    rows = (
        await session.execute(
            select(News)
            .where(News.is_highlighted.is_(True))
            .order_by(desc(News.published_at))
            .limit(3)
        )
    ).scalars().all()
    return [news_dict(n) for n in rows]


@router.get("/news/popular")
async def popular_news(session: AsyncSession = Depends(get_session)):
    rows = (
        await session.execute(
            select(News).order_by(desc(News.views), desc(News.published_at)).limit(5)
        )
    ).scalars().all()
    return [news_dict(n) for n in rows]


@router.get("/news/slug/{slug}")
async def get_news(slug: str, session: AsyncSession = Depends(get_session)):
    n = (
        await session.execute(select(News).where(News.slug == slug))
    ).scalar_one_or_none()
    if not n:
        return None
    await session.execute(update(News).where(News.id == n.id).values(views=News.views + 1))
    return news_dict(n)


# ===================== BIRTHDAY =====================
@router.get("/birthday/today")
async def birthday_today(session: AsyncSession = Depends(get_session)):
    p = wib_parts()
    rows = (
        await session.execute(
            select(Member).where(
                Member.show_birthday.is_(True),
                extract("month", Member.birth_date) == p["month"],
                extract("day", Member.birth_date) == p["day"],
            )
        )
    ).scalars().all()
    return [member_dict(m) for m in rows]


@router.get("/birthday/week")
async def birthday_this_week(session: AsyncSession = Depends(get_session)):
    p = wib_parts()
    monday = wib_midnight(p["year"], p["month"], p["day"]) - timedelta(days=p["weekday"])
    all_rows = (
        await session.execute(select(Member).where(Member.show_birthday.is_(True)))
    ).scalars().all()
    days = []
    for i in range(7):
        d = monday + timedelta(days=i)
        dp = wib_parts(d)
        days.append(
            {
                "key": f"{dp['year']:04d}-{dp['month']:02d}-{dp['day']:02d}",
                "month": dp["month"],
                "day": dp["day"],
                "date": d.isoformat(),
                "members": [
                    member_dict(m)
                    for m in all_rows
                    if m.birth_date and m.birth_date.month == dp["month"] and m.birth_date.day == dp["day"]
                ],
            }
        )
    return days


@router.get("/birthday/month/{month}")
async def birthdays_in_month(month: int, session: AsyncSession = Depends(get_session)):
    rows = (
        await session.execute(
            select(Member)
            .where(Member.show_birthday.is_(True), extract("month", Member.birth_date) == month)
            .order_by(asc(extract("day", Member.birth_date)))
        )
    ).scalars().all()
    return [member_dict(m) for m in rows]


@router.get("/birthday/{member_id}/wishes")
async def wishes_for(member_id: int, year: int, session: AsyncSession = Depends(get_session)):
    from src.verse.helpers import wish_dict

    rows = (
        await session.execute(
            select(BirthdayWish)
            .where(BirthdayWish.member_id == member_id, BirthdayWish.year == year)
            .order_by(desc(BirthdayWish.created_at))
            .limit(50)
        )
    ).scalars().all()
    return [wish_dict(w) for w in rows]


class WishIn(BaseModel):
    memberId: int
    message: str


@router.post("/birthday/wishes")
async def send_wish(
    data: WishIn,
    viewer: dict = Depends(require_user),
    session: AsyncSession = Depends(get_session),
):
    from src.verse.helpers import wish_dict

    if viewer["isBlocked"]:
        return {"ok": False, "error": "Akun kamu sedang diblokir.", "code": "ACCOUNT_BLOCKED"}
    text = data.message.strip()
    if not text or len(text) > 200:
        return {"ok": False, "error": "Ucapan 1–200 karakter."}
    blocked, _ = await moderation.check_text(session, text)
    if blocked:
        return {"ok": False, "error": "Ucapan mengandung kata yang tidak diperbolehkan.", "code": "MESSAGE_BLOCKED"}
    em_ok, bad_emoji = moderation.check_emoji(text)
    if not em_ok:
        return {"ok": False, "error": f"Emoji {bad_emoji} tidak diizinkan.", "code": "EMOJI_BLOCKED"}
    year = wib_parts()["year"]
    from sqlalchemy.exc import IntegrityError

    member = await session.get(Member, data.memberId)
    if not member:
        return {"ok": False, "error": "Member tidak ditemukan."}
    try:
        wish = BirthdayWish(
            member_id=data.memberId,
            user_seq=viewer["userId"],
            username=viewer["username"],
            message=text,
            year=year,
        )
        session.add(wish)
        await session.flush()
        return {"ok": True, "data": wish_dict(wish)}
    except IntegrityError:
        await session.rollback()
        return {"ok": False, "error": "Kamu sudah mengirim ucapan untuk member ini tahun ini."}


# ===================== WIKI: ENCYCLOPEDIA / GLOSSARY / MOTIVATION =====================
@router.get("/encyclopedia")
async def list_encyclopedia(session: AsyncSession = Depends(get_session)):
    rows = (
        await session.execute(select(Encyclopedia).order_by(asc(Encyclopedia.sort_order)))
    ).scalars().all()
    return [
        {
            "id": e.id, "slug": e.slug, "title": e.title, "content": e.content,
            "sortOrder": e.sort_order, "updatedAt": e.updated_at.isoformat() if e.updated_at else None,
        }
        for e in rows
    ]


@router.get("/encyclopedia/{slug}")
async def get_encyclopedia(slug: str, session: AsyncSession = Depends(get_session)):
    e = (
        await session.execute(select(Encyclopedia).where(Encyclopedia.slug == slug))
    ).scalar_one_or_none()
    if not e:
        return None
    return {
        "id": e.id, "slug": e.slug, "title": e.title, "content": e.content,
        "sortOrder": e.sort_order, "updatedAt": e.updated_at.isoformat() if e.updated_at else None,
    }


@router.get("/glossary")
async def list_glossary(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(Glossary).order_by(asc(Glossary.term)))).scalars().all()
    return [{"id": g.id, "term": g.term, "meaning": g.meaning} for g in rows]


@router.get("/motivation/daily")
async def daily_motivation(session: AsyncSession = Depends(get_session)):
    from datetime import date as _date

    from src.verse.helpers import wib_date_key

    today = _date.fromisoformat(wib_date_key())
    row = (
        await session.execute(
            select(Motivation).where(
                Motivation.is_published.is_(True),
                Motivation.featured_on == today,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        row = (
            await session.execute(
                select(Motivation)
                .where(Motivation.is_published.is_(True))
                .order_by(desc(Motivation.created_at))
                .limit(1)
            )
        ).scalar_one_or_none()
    return _motivation_dict(row) if row else None


@router.get("/motivation/list")
async def list_motivations(session: AsyncSession = Depends(get_session)):
    rows = (
        await session.execute(
            select(Motivation)
            .where(Motivation.is_published.is_(True))
            .order_by(desc(Motivation.created_at))
        )
    ).scalars().all()
    return [_motivation_dict(m) for m in rows]


def _motivation_dict(m) -> dict:
    return {
        "id": m.id, "quote": m.quote, "author": m.author, "template": m.template,
        "isPublished": m.is_published,
        "featuredOn": m.featured_on.isoformat() if m.featured_on else None,
        "createdAt": m.created_at.isoformat() if m.created_at else None,
    }


@router.get("/contributors")
async def list_contributors(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(Contributor))).scalars().all()
    return [
        {"id": c.id, "name": c.name, "role": c.role, "contribution": c.contribution}
        for c in rows
    ]


# ===================== STATS & GLOBAL SEARCH =====================
@router.get("/stats/counts")
async def stats_counts(session: AsyncSession = Depends(get_session)):
    from src.models import ChatMessage, User

    users_n = (await session.execute(select(func.count()).select_from(User))).scalar() or 0
    since = now_utc() - timedelta(days=1)
    chat_n = (
        await session.execute(
            select(func.count()).select_from(ChatMessage).where(ChatMessage.created_at >= since)
        )
    ).scalar() or 0
    return {"users": users_n, "chat24h": chat_n}


@router.get("/search")
async def global_search(q: str, session: AsyncSession = Depends(get_session)):
    term = f"%{q[:80]}%"
    ms = (
        await session.execute(
            select(Member)
            .where(
                or_(
                    Member.name.ilike(term), Member.nickname.ilike(term), Member.jikoshoukai.ilike(term)
                )
            )
            .limit(6)
        )
    ).scalars().all()
    ns = (
        await session.execute(
            select(News)
            .where(or_(News.title.ilike(term), News.summary.ilike(term), News.body.ilike(term)))
            .order_by(desc(News.published_at))
            .limit(5)
        )
    ).scalars().all()
    ss = (
        await session.execute(
            select(Schedule)
            .where(or_(Schedule.title.ilike(term), Schedule.location.ilike(term)))
            .order_by(asc(Schedule.start_at))
            .limit(5)
        )
    ).scalars().all()
    es = (
        await session.execute(
            select(Encyclopedia).where(or_(Encyclopedia.title.ilike(term), Encyclopedia.content.ilike(term)))
            .limit(4)
        )
    ).scalars().all()
    gs = (
        await session.execute(
            select(Glossary).where(or_(Glossary.term.ilike(term), Glossary.meaning.ilike(term))).limit(4)
        )
    ).scalars().all()
    mo = (
        await session.execute(select(Motivation).where(Motivation.quote.ilike(term)).limit(3))
    ).scalars().all()
    return {
        "members": [member_dict(m) for m in ms],
        "news": [news_dict(n) for n in ns],
        "schedules": [schedule_dict(s) for s in ss],
        "encyclopedia": [
            {"id": e.id, "slug": e.slug, "title": e.title, "content": e.content,
             "sortOrder": e.sort_order, "updatedAt": e.updated_at.isoformat() if e.updated_at else None}
            for e in es
        ],
        "glossary": [{"id": g.id, "term": g.term, "meaning": g.meaning} for g in gs],
        "motivations": [_motivation_dict(m) for m in mo],
    }
