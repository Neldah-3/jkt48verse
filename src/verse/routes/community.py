"""Komunitas: chat, notifikasi, bookmark, reminder, oshi, profil, aktivitas."""

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import delete, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.models import (
    ActivityLog, Bookmark, ChatMessage, ChatReaction, Notification,
    Report, ScheduleReminder, User, UserOshi,
)
from src.verse import moderation
from src.verse.deps import get_viewer, require_user
from src.verse.helpers import notification_dict, now_utc

router = APIRouter()


def _viewer_role(v: dict) -> str:
    return v.get("role", "GUEST")


# ===================== CHAT =====================
@router.get("/chat")
async def recent_chat(
    limit: int = 50,
    viewer: dict = Depends(get_viewer),
    session: AsyncSession = Depends(get_session),
):
    since = now_utc() - timedelta(days=3)
    rows = (
        await session.execute(
            select(ChatMessage)
            .where(ChatMessage.is_hidden.is_(False), ChatMessage.created_at >= since)
            .order_by(desc(ChatMessage.created_at))
            .limit(min(limit, 100))
        )
    ).scalars().all()
    ids = [r.id for r in rows]
    reacts: list = []
    parents: list = []
    if ids:
        reacts = (
            await session.execute(select(ChatReaction).where(ChatReaction.message_id.in_(ids)))
        ).scalars().all()
        parent_ids = [r.parent_id for r in rows if r.parent_id]
        if parent_ids:
            parents = (
                await session.execute(
                    select(ChatMessage.id, ChatMessage.username, ChatMessage.body).where(
                        ChatMessage.id.in_(parent_ids)
                    )
                )
            ).all()
    out = []
    for r in reversed(rows):
        rs = [x for x in reacts if x.message_id == r.id]
        grouped: dict[str, int] = {}
        for x in rs:
            grouped[x.emoji] = grouped.get(x.emoji, 0) + 1
        parent = next(({"id": p.id, "username": p.username, "body": p.body} for p in parents if p.id == r.parent_id), None) if r.parent_id else None
        out.append(
            {
                "id": r.id,
                "userId": r.user_seq,
                "username": r.username,
                "role": r.role,
                "avatarSeed": r.avatar_seed,
                "body": r.body,
                "parentId": r.parent_id,
                "isPinned": r.is_pinned,
                "isHidden": r.is_hidden,
                "createdAt": r.created_at.isoformat() if r.created_at else None,
                "reactions": [
                    {"emoji": emoji, "n": n, "mine": any(x.emoji == emoji and x.user_seq == viewer.get("userId") for x in rs)}
                    for emoji, n in grouped.items()
                ],
                "parent": parent,
            }
        )
    return out


@router.get("/chat/pinned")
async def pinned_chat(session: AsyncSession = Depends(get_session)):
    rows = (
        await session.execute(
            select(ChatMessage)
            .where(ChatMessage.is_pinned.is_(True), ChatMessage.is_hidden.is_(False))
            .order_by(desc(ChatMessage.created_at))
            .limit(3)
        )
    ).scalars().all()
    return [
        {"id": r.id, "username": r.username, "body": r.body, "createdAt": r.created_at.isoformat()}
        for r in rows
    ]


class ChatIn(BaseModel):
    body: str
    parentId: Optional[int] = None


@router.post("/chat")
async def send_chat(
    data: ChatIn,
    viewer: dict = Depends(require_user),
    session: AsyncSession = Depends(get_session),
):
    from src.models import ModerationLog
    from src.redis_client import redis_instance

    if viewer["isBlocked"]:
        return {"ok": False, "error": "Akun kamu sedang diblokir.", "code": "ACCOUNT_BLOCKED"}
    muted_until = (viewer.get("user") or {}).get("mutedUntil")
    if viewer["isMuted"]:
        return {"ok": False, "error": f"Kamu sedang di-mute hingga {muted_until} WIB.", "code": "MUTED"}
    text = data.body.strip()
    if not text:
        return {"ok": False, "error": "Pesan kosong."}
    if len(text) > 500:
        return {"ok": False, "error": "Maksimal 500 karakter."}

    # slow-mode 5 detik via redis/memory
    rkey = moderation.rate_key(viewer)
    last = await redis_instance.get(rkey)
    if last:
        return {"ok": False, "error": "Slow-mode aktif. Tunggu 5 detik.", "code": "SLOW_MODE"}
    await redis_instance.set(rkey, "1", ttl=5)

    em_ok, bad_emoji = moderation.check_emoji(text)
    if not em_ok:
        return {"ok": False, "error": f"Emoji {bad_emoji} tidak diizinkan. Gunakan emoji whitelist.", "code": "EMOJI_BLOCKED"}
    blocked, _ = await moderation.check_text(session, text)
    if blocked:
        session.add(
            ModerationLog(user_seq=viewer["userId"], kind="MESSAGE_BLOCKED", detail=text[:120])
        )
        return {"ok": False, "error": "Pesan mengandung kata yang tidak diperbolehkan. Mari jaga ruang chat tetap nyaman.", "code": "MESSAGE_BLOCKED"}

    msg = ChatMessage(
        user_seq=viewer["userId"],
        username=viewer["username"],
        role=_viewer_role(viewer),
        avatar_seed=viewer.get("avatarSeed", 1),
        body=text,
        parent_id=data.parentId,
    )
    session.add(msg)
    await session.flush()

    # mentions → notifikasi
    import re as _re

    mentions = [m.lower() for m in _re.findall(r"@([a-zA-Z0-9]{3,20})", text)]
    if mentions:
        targets = (
            await session.execute(select(User).where(func.lower(User.username).in_(mentions)))
        ).scalars().all()
        for t in targets:
            prefs = t.notif_prefs or {}
            if t.seq != viewer.get("userId") and prefs.get("CHAT_MENTION", True):
                session.add(
                    Notification(
                        user_seq=t.seq,
                        type="CHAT_MENTION",
                        title=f"{viewer['username']} menyebut kamu di chat",
                        body=text[:120],
                        href="/chat",
                    )
                )
    session.add(ActivityLog(user_seq=viewer["userId"], action="chat", detail=text[:80]))
    return {"ok": True, "data": {"id": msg.id}}


class ReactIn(BaseModel):
    emoji: str


@router.post("/chat/{message_id}/react")
async def react_chat(
    message_id: int,
    data: ReactIn,
    viewer: dict = Depends(require_user),
    session: AsyncSession = Depends(get_session),
):
    if data.emoji not in moderation.EMOJI_WHITELIST:
        return {"ok": False, "error": "Emoji tidak diizinkan."}
    existing = (
        await session.execute(
            select(ChatReaction).where(
                ChatReaction.message_id == message_id,
                ChatReaction.user_seq == viewer["userId"],
            )
        )
    ).scalar_one_or_none()
    if existing and existing.emoji == data.emoji:
        await session.delete(existing)
    elif existing:
        existing.emoji = data.emoji
    else:
        session.add(ChatReaction(message_id=message_id, user_seq=viewer["userId"], emoji=data.emoji))
    return {"ok": True}


class ReportIn(BaseModel):
    reason: str
    description: Optional[str] = None


@router.post("/chat/{message_id}/report")
async def report_chat(
    message_id: int,
    data: ReportIn,
    viewer: dict = Depends(require_user),
    session: AsyncSession = Depends(get_session),
):
    m = await session.get(ChatMessage, message_id)
    if not m:
        return {"ok": False, "error": "Pesan tidak ditemukan."}
    session.add(
        Report(
            message_id=message_id,
            reporter_seq=viewer["userId"],
            target_user_seq=m.user_seq,
            target_username=m.username,
            reason=data.reason,
            description=(data.description or "")[:300],
        )
    )
    n = (
        await session.execute(
            select(func.count(func.distinct(Report.reporter_seq))).where(
                Report.message_id == message_id,
                Report.created_at >= now_utc() - timedelta(minutes=10),
            )
        )
    ).scalar() or 0
    if n >= 5:
        m.is_hidden = True
    return {"ok": True}


@router.delete("/chat/{message_id}")
async def delete_chat(
    message_id: int,
    viewer: dict = Depends(get_viewer),
    session: AsyncSession = Depends(get_session),
):
    m = await session.get(ChatMessage, message_id)
    if not m:
        return {"ok": False, "error": "Tidak ditemukan."}
    own = viewer.get("userId") and m.user_seq == viewer.get("userId")
    if not own and viewer.get("role") not in ("ADMIN", "MODERATOR"):
        return {"ok": False, "error": "Tidak diizinkan."}
    m.is_hidden = True
    return {"ok": True}


@router.post("/chat/{message_id}/pin")
async def pin_chat(
    message_id: int,
    viewer: dict = Depends(get_viewer),
    session: AsyncSession = Depends(get_session),
):
    if viewer.get("role") != "ADMIN":
        return {"ok": False, "error": "Hanya ADMIN yang dapat menyematkan."}
    m = await session.get(ChatMessage, message_id)
    if not m:
        return {"ok": False, "error": "Tidak ditemukan."}
    if not m.is_pinned:
        n = (
            await session.execute(
                select(func.count()).select_from(ChatMessage).where(ChatMessage.is_pinned.is_(True))
            )
        ).scalar() or 0
        if n >= 3:
            return {"ok": False, "error": "Maksimal 3 pin aktif."}
    m.is_pinned = not m.is_pinned
    return {"ok": True}


# ===================== NOTIFICATIONS =====================
@router.get("/notifications")
async def list_notifications(
    limit: int = 50,
    viewer: dict = Depends(require_user),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        await session.execute(
            select(Notification)
            .where(Notification.user_seq == viewer["userId"])
            .order_by(desc(Notification.created_at))
            .limit(min(limit, 100))
        )
    ).scalars().all()
    return [notification_dict(n) for n in rows]


@router.get("/notifications/unread-count")
async def unread_count(
    viewer: dict = Depends(get_viewer),
    session: AsyncSession = Depends(get_session),
):
    if not viewer.get("userId"):
        return {"n": 0}
    n = (
        await session.execute(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_seq == viewer["userId"], Notification.is_read.is_(False))
        )
    ).scalar() or 0
    return {"n": n}


@router.post("/notifications/read-all")
async def mark_all_read(
    viewer: dict = Depends(require_user),
    session: AsyncSession = Depends(get_session),
):
    await session.execute(
        update(Notification)
        .where(Notification.user_seq == viewer["userId"], Notification.is_read.is_(False))
        .values(is_read=True)
    )
    return {"ok": True}


# ===================== BOOKMARKS =====================
@router.get("/bookmarks/check")
async def is_bookmarked(
    type: str,
    id: int,
    viewer: dict = Depends(get_viewer),
    session: AsyncSession = Depends(get_session),
):
    if not viewer.get("userId"):
        return {"on": False}
    b = (
        await session.execute(
            select(Bookmark).where(
                Bookmark.user_seq == viewer["userId"],
                Bookmark.entity_type == type,
                Bookmark.entity_id == id,
            )
        )
    ).scalar_one_or_none()
    return {"on": b is not None}


class BookmarkIn(BaseModel):
    entityType: str
    entityId: int


@router.post("/bookmarks/toggle")
async def toggle_bookmark(
    data: BookmarkIn,
    viewer: dict = Depends(require_user),
    session: AsyncSession = Depends(get_session),
):
    existing = (
        await session.execute(
            select(Bookmark).where(
                Bookmark.user_seq == viewer["userId"],
                Bookmark.entity_type == data.entityType,
                Bookmark.entity_id == data.entityId,
            )
        )
    ).scalar_one_or_none()
    if existing:
        await session.delete(existing)
        return {"ok": True, "data": {"on": False}}
    session.add(
        Bookmark(user_seq=viewer["userId"], entity_type=data.entityType, entity_id=data.entityId)
    )
    return {"ok": True, "data": {"on": True}}


# ===================== SCHEDULE REMINDERS =====================
@router.get("/schedules/reminders")
async def reminder_set(
    viewer: dict = Depends(get_viewer),
    session: AsyncSession = Depends(get_session),
):
    if not viewer.get("userId"):
        return {"ids": []}
    rows = (
        await session.execute(
            select(ScheduleReminder.schedule_id).where(ScheduleReminder.user_seq == viewer["userId"])
        )
    ).scalars().all()
    return {"ids": list(rows)}


class ReminderToggleIn(BaseModel):
    scheduleId: int


@router.post("/schedules/reminders/toggle")
async def toggle_reminder(
    data: ReminderToggleIn,
    viewer: dict = Depends(require_user),
    session: AsyncSession = Depends(get_session),
):
    schedule_id = data.scheduleId
    from src.models import Schedule

    if not await session.get(Schedule, schedule_id):
        return {"ok": False, "error": "Jadwal tidak ditemukan."}
    existing = (
        await session.execute(
            select(ScheduleReminder).where(
                ScheduleReminder.user_seq == viewer["userId"],
                ScheduleReminder.schedule_id == schedule_id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        await session.delete(existing)
        return {"ok": True, "data": {"on": False}}
    session.add(ScheduleReminder(user_seq=viewer["userId"], schedule_id=schedule_id))
    session.add(
        Notification(
            user_seq=viewer["userId"],
            type="SCHEDULE_REMINDER",
            title="Pengingat diaktifkan",
            body="Kamu akan diingatkan 30 & 5 menit sebelum acara dimulai.",
            href=f"/schedule/{schedule_id}",
        )
    )
    return {"ok": True, "data": {"on": True}}


# ===================== OSHI =====================
@router.get("/account/oshi")
async def get_oshi(
    viewer: dict = Depends(require_user),
    session: AsyncSession = Depends(get_session),
):
    from src.models import Member
    from src.verse.helpers import member_dict

    rows = (
        await session.execute(
            select(UserOshi, Member)
            .join(Member, Member.id == UserOshi.member_id)
            .where(UserOshi.user_seq == viewer["userId"])
            .order_by(UserOshi.rank)
        )
    ).all()
    return [{"m": member_dict(m), "rank": o.rank} for o, m in rows]


class OshiIn(BaseModel):
    kami: int = 0
    others: list[int] = []


@router.post("/account/oshi")
async def set_oshi(
    data: OshiIn,
    viewer: dict = Depends(require_user),
    session: AsyncSession = Depends(get_session),
):
    others = [x for x in data.others if x and x != data.kami][:5]
    await session.execute(
        delete(UserOshi).where(UserOshi.user_seq == viewer["userId"])
    )
    if data.kami:
        session.add(UserOshi(user_seq=viewer["userId"], member_id=data.kami, rank=0))
    for i, mid in enumerate(others):
        session.add(UserOshi(user_seq=viewer["userId"], member_id=mid, rank=i + 1))
    return {"ok": True}


# ===================== PROFILE / SETTINGS / ACTIVITY =====================
class ProfileIn(BaseModel):
    bio: Optional[str] = None
    avatarSeed: Optional[int] = None


@router.patch("/account/profile")
async def update_profile(
    data: ProfileIn,
    viewer: dict = Depends(require_user),
    session: AsyncSession = Depends(get_session),
):
    user = (
        await session.execute(select(User).where(User.seq == viewer["userId"]))
    ).scalar_one_or_none()
    if not user:
        return {"ok": False, "error": "User tidak ditemukan."}
    if data.bio is not None:
        user.bio = data.bio[:160]
    if data.avatarSeed is not None:
        user.avatar_seed = min(6, max(1, data.avatarSeed))
    return {"ok": True}


class SettingsIn(BaseModel):
    theme: Optional[str] = None
    lang: Optional[str] = None
    multiLiveLayout: Optional[str] = None
    isPrivate: Optional[bool] = None
    hideOshi: Optional[bool] = None
    notifPrefs: Optional[dict] = None


@router.patch("/account/settings")
async def update_settings(
    data: SettingsIn,
    viewer: dict = Depends(require_user),
    session: AsyncSession = Depends(get_session),
):
    user = (
        await session.execute(select(User).where(User.seq == viewer["userId"]))
    ).scalar_one_or_none()
    if not user:
        return {"ok": False, "error": "User tidak ditemukan."}
    if data.theme is not None:
        user.theme = data.theme
    if data.lang is not None:
        user.lang = data.lang
    if data.multiLiveLayout is not None:
        user.multi_live_layout = data.multiLiveLayout
    if data.isPrivate is not None:
        user.is_private = data.isPrivate
    if data.hideOshi is not None:
        user.hide_oshi = data.hideOshi
    if data.notifPrefs is not None:
        user.notif_prefs = data.notifPrefs
    return {"ok": True}


@router.get("/account/activity")
async def account_activity(
    limit: int = 50,
    viewer: dict = Depends(require_user),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        await session.execute(
            select(ActivityLog)
            .where(ActivityLog.user_seq == viewer["userId"])
            .order_by(desc(ActivityLog.created_at))
            .limit(min(limit, 100))
        )
    ).scalars().all()
    return [
        {
            "id": r.id,
            "userId": r.user_seq,
            "action": r.action,
            "detail": r.detail,
            "createdAt": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


# ===================== RINGKASAN & RIWAYAT AKUN =====================
@router.get("/account/summary")
async def account_summary(
    viewer: dict = Depends(require_user),
    session: AsyncSession = Depends(get_session),
):
    from src.models import ActivityLog, GameScore, UserOshi, Member
    from src.verse.helpers import member_dict

    user_seq = viewer["userId"]
    games = (
        await session.execute(
            select(func.count()).select_from(GameScore).where(GameScore.user_seq == user_seq)
        )
    ).scalar() or 0
    interactions = (
        await session.execute(
            select(func.count()).select_from(ActivityLog).where(ActivityLog.user_seq == user_seq)
        )
    ).scalar() or 0
    oshi_rows = (
        await session.execute(
            select(UserOshi, Member)
            .join(Member, Member.id == UserOshi.member_id)
            .where(UserOshi.user_seq == user_seq)
            .order_by(UserOshi.rank)
        )
    ).all()
    return {
        "gameSessions": games,
        "interactions": interactions,
        "oshi": [{"m": member_dict(m), "rank": o.rank} for o, m in oshi_rows],
    }


@router.get("/account/overview")
async def account_overview(
    viewer: dict = Depends(require_user),
    session: AsyncSession = Depends(get_session),
):
    """Data lengkap untuk halaman /account/activity."""
    from datetime import timedelta

    from src.models import (
        ActivityLog, Bookmark, ChatMessage, Encyclopedia, GameScore,
        LoginHistory, Member, News, RefreshToken, Schedule, SorterResult, User,
    )

    user = (
        await session.execute(select(User).where(User.seq == viewer["userId"]))
    ).scalar_one_or_none()
    if not user:
        return {
            "sessions": [], "loginLogs": [], "activity": [], "bookmarks": [],
            "gameScores": [], "chat": [], "sorter": [],
        }
    user_seq = viewer["userId"]

    refresh_rows = (
        await session.execute(
            select(RefreshToken)
            .where(RefreshToken.user_id == user.user_id)
            .order_by(desc(RefreshToken.last_used_at))
            .limit(10)
        )
    ).scalars().all()
    sessions = [
        {
            "id": r.id,
            "device": r.device,
            "ip": r.ip,
            "browser": r.browser,
            "createdAt": r.created_at.isoformat() if r.created_at else None,
            "lastUsedAt": r.last_used_at.isoformat() if r.last_used_at else None,
        }
        for r in refresh_rows
    ]

    login_rows = (
        await session.execute(
            select(LoginHistory)
            .where(LoginHistory.user_id == user.user_id)
            .order_by(desc(LoginHistory.login_at))
            .limit(20)
        )
    ).scalars().all()
    login_logs = [
        {
            "id": r.id,
            "createdAt": (r.login_at or now_utc()).isoformat(),
            "success": r.success if r.success is not None else True,
            "ip": r.ip,
            "device": r.device,
        }
        for r in login_rows
    ]

    activity_rows = (
        await session.execute(
            select(ActivityLog)
            .where(ActivityLog.user_seq == user_seq)
            .order_by(desc(ActivityLog.created_at))
            .limit(50)
        )
    ).scalars().all()
    activity = [
        {"id": r.id, "action": r.action, "detail": r.detail, "createdAt": r.created_at.isoformat() if r.created_at else None}
        for r in activity_rows
    ]

    bookmark_rows = (
        await session.execute(
            select(Bookmark).where(Bookmark.user_seq == user_seq).order_by(desc(Bookmark.created_at))
        )
    ).scalars().all()
    bookmark_items: list = []
    for b in bookmark_rows:
        title, href = None, None
        if b.entity_type == "news":
            n = (
                await session.execute(select(News).where(News.id == b.entity_id))
            ).scalar_one_or_none()
            title, href = (n.title, f"/news/{n.slug}") if n else (None, None)
        elif b.entity_type == "schedule":
            s = await session.get(Schedule, b.entity_id)
            title, href = (s.title, f"/schedule/{s.id}") if s else (None, None)
        elif b.entity_type == "encyclopedia":
            e = (
                await session.execute(select(Encyclopedia).where(Encyclopedia.id == b.entity_id))
            ).scalar_one_or_none()
            title, href = (e.title, f"/encyclopedia/{e.slug}") if e else (None, None)
        if title:
            bookmark_items.append({"entityType": b.entity_type, "id": b.entity_id, "title": title, "href": href})

    game_rows = (
        await session.execute(
            select(GameScore)
            .where(GameScore.user_seq == user_seq)
            .order_by(desc(GameScore.created_at))
            .limit(50)
        )
    ).scalars().all()
    game_scores = [
        {"id": r.id, "game": r.game, "score": r.score, "detail": r.detail, "createdAt": r.created_at.isoformat() if r.created_at else None}
        for r in game_rows
    ]

    chat_rows = (
        await session.execute(
            select(ChatMessage)
            .where(ChatMessage.user_seq == user_seq, ChatMessage.created_at >= now_utc() - timedelta(days=3))
            .order_by(desc(ChatMessage.created_at))
            .limit(50)
        )
    ).scalars().all()
    chat = [
        {"id": r.id, "body": r.body, "isHidden": r.is_hidden, "createdAt": r.created_at.isoformat() if r.created_at else None}
        for r in chat_rows
    ]

    sorter_rows = (
        await session.execute(
            select(SorterResult)
            .where(SorterResult.user_seq == user_seq)
            .order_by(desc(SorterResult.created_at))
            .limit(10)
        )
    ).scalars().all()
    sorter = []
    for r in sorter_rows:
        ranking = (r.ranking or [])[:100]
        top3 = []
        for mid in ranking[:3]:
            m = await session.get(Member, mid)
            top3.append(m.nickname if m else "?")
        sorter.append({"id": r.id, "createdAt": r.created_at.isoformat() if r.created_at else None, "top3": top3, "count": len(ranking)})

    return {
        "sessions": sessions,
        "loginLogs": login_logs,
        "activity": activity,
        "bookmarks": bookmark_items,
        "gameScores": game_scores,
        "chat": chat,
        "sorter": sorter,
    }
