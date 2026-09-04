"""Live sessions: sync ShowRoom → DB, live now, riwayat."""

import time
from typing import Optional

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.logging_config import create_logger
from src.models import LiveSession, Member
from src.verse.helpers import live_dict, now_utc

router = APIRouter()
logger = create_logger("verse_live", __name__)

_last_sync = 0.0
SYNC_INTERVAL = 60.0


def _norm(s: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]", "", s.lower())


async def sync_showroom(session: AsyncSession, force: bool = False):
    """Tarik live rooms dari API publik ShowRoom, cocokkan ke tabel member, upsert."""
    global _last_sync
    now = time.monotonic()
    if not force and now - _last_sync < SYNC_INTERVAL:
        return
    _last_sync = now
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            res = await client.get(
                "https://www.showroom-live.com/api/live/onlives",
                headers={"user-agent": "Mozilla/5.0 (JKT48Verse fan project)"},
            )
            res.raise_for_status()
            data = res.json()
    except Exception as e:
        logger.warning(f"ShowRoom sync gagal (jaringan?): {e}")
        return

    rooms: list[dict] = []
    for group in data.get("onlives") or []:
        for r in group.get("lives") or []:
            rooms.append(r)
    jkt = [
        r
        for r in rooms
        if (r.get("room_url_key") or "").upper().startswith("JKT48")
        or "JKT48" in (r.get("main_name") or "").upper()
    ]

    members = (
        await session.execute(select(Member.id, Member.name, Member.nickname, Member.socials))
    ).all()
    open_sessions = (
        await session.execute(
            select(LiveSession).where(
                LiveSession.platform == "showroom", LiveSession.ended_at.is_(None)
            )
        )
    ).scalars().all()
    live_keys: set[str] = set()

    for r in jkt:
        key = r.get("room_url_key") or str(r.get("room_id"))
        live_keys.add(key)
        nk = _norm(key.replace("JKT48_", "").lstrip("_").lower()) if key else ""
        import re as _re

        nk = _re.sub(r"officer$|official$", "", nk)
        found = None
        for m in members:
            showroom_url = (m.socials or {}).get("showroom", "").lower()
            if showroom_url.endswith("/" + key.lower()):
                found = m
                break
        if not found and nk:
            for m in members:
                if _norm(m.nickname or "") == nk:
                    found = m
                    break
        if not found and nk and len(nk) > 3:
            for m in members:
                if nk in _norm(m.name or ""):
                    found = m
                    break
        display = (found.nickname if found else None) or _re.sub(
            r"^JKT48\s*[-–:]?\s*", "", (r.get("main_name") or key)
        ).strip()
        streams = r.get("streaming_url_list") or []
        stream = next((s.get("url") for s in streams if s.get("is_default")), None) or (
            streams[0].get("url") if streams else None
        )
        existing = next((o for o in open_sessions if o.room_key == key), None)
        if existing:
            existing.viewers = r.get("view_num") or existing.viewers
            existing.title = r.get("telop") or existing.title
            existing.stream_url = stream or existing.stream_url
            existing.image_url = r.get("image") or existing.image_url
        else:
            from datetime import datetime, timezone

            started = r.get("started_at")
            session.add(
                LiveSession(
                    member_id=found.id if found else None,
                    member_name=display or key,
                    platform="showroom",
                    title=r.get("telop") or f"Live {display}",
                    room_key=key,
                    stream_url=stream,
                    image_url=r.get("image"),
                    viewers=r.get("view_num"),
                    started_at=(
                        datetime.fromtimestamp(started, tz=timezone.utc)
                        if started
                        else now_utc()
                    ),
                )
            )
    for o in open_sessions:
        if o.room_key and o.room_key not in live_keys:
            o.ended_at = now_utc()


@router.get("/live/now")
async def live_now(session: AsyncSession = Depends(get_session)):
    await sync_showroom(session)
    rows = (
        await session.execute(
            select(LiveSession, Member.slug)
            .outerjoin(Member, Member.id == LiveSession.member_id)
            .where(LiveSession.ended_at.is_(None))
            .order_by(desc(LiveSession.started_at))
        )
    ).all()
    return [live_dict(l, slug) for l, slug in rows]


@router.get("/live/history")
async def live_history(days: int = 3, session: AsyncSession = Depends(get_session)):
    from datetime import timedelta

    since = now_utc() - timedelta(days=days)
    rows = (
        await session.execute(
            select(LiveSession, Member.slug)
            .outerjoin(Member, Member.id == LiveSession.member_id)
            .where(LiveSession.started_at >= since)
            .order_by(desc(LiveSession.started_at))
            .limit(100)
        )
    ).all()
    return [live_dict(l, slug) for l, slug in rows]
