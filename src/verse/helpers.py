"""Utilitas umum: waktu WIB, serialisasi, dan tipe Viewer."""

from datetime import date, datetime, timezone
from typing import Any, Optional

TZ_WIB = timezone(offset=__import__("datetime").timedelta(hours=7), name="WIB")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def wib_parts(d: datetime | date | str | None = None) -> dict:
    """Bagian tanggal-waktu dalam zona Asia/Jakarta (mirip lib/time.ts frontend)."""
    if d is None:
        d = now_utc()
    if isinstance(d, str):
        d = datetime.fromisoformat(d.replace("Z", "+00:00"))
    if isinstance(d, date) and not isinstance(d, datetime):
        d = datetime(d.year, d.month, d.day)
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    wib = d.astimezone(TZ_WIB)
    return {
        "year": wib.year,
        "month": wib.month,
        "day": wib.day,
        "hour": wib.hour,
        "minute": wib.minute,
        "second": wib.second,
        "weekday": wib.weekday(),  # Senin=0 .. Minggu=6
    }


def wib_date_key(d: datetime | date | str | None = None) -> str:
    p = wib_parts(d)
    return f"{p['year']:04d}-{p['month']:02d}-{p['day']:02d}"


def wib_midnight(year: int, month: int, day: int) -> datetime:
    """00:00 WIB pada tanggal kalender tersebut (sebagai datetime tz-aware).

    00:00 WIB == 17:00 UTC hari sebelumnya. Implementasi lama keliru
    mengembalikan 07:00 UTC (= 14:00 WIB) sehingga reset kuota/leaderboard
    harian mundur 14 jam.
    """
    return datetime(year, month, day, tzinfo=TZ_WIB)


def iso(value: datetime | date | None) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return value.isoformat()


def dt(value: str | datetime | None) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


# ---------- serialisasi entitas (bentuk = tipe TS di frontend) ----------

def member_dict(m) -> dict[str, Any]:
    return {
        "id": m.id,
        "slug": m.slug,
        "name": m.name,
        "nickname": m.nickname,
        "generation": m.generation,
        "status": m.status,
        "team": m.team,
        "birthDate": m.birth_date.isoformat() if m.birth_date else None,
        "height": m.height,
        "bloodType": m.blood_type,
        "horoscope": m.horoscope,
        "jikoshoukai": m.jikoshoukai,
        "hobbies": m.hobbies,
        "trivia": m.trivia,
        "socials": m.socials or {},
        "showBirthday": m.show_birthday,
        "createdAt": iso(m.created_at),
    }


def schedule_dict(s, member_ids: Optional[list[int]] = None) -> dict[str, Any]:
    d = {
        "id": s.id,
        "title": s.title,
        "type": s.type,
        "startAt": iso(s.start_at),
        "endAt": iso(s.end_at),
        "location": s.location,
        "mapUrl": s.map_url,
        "setlist": s.setlist,
        "ticketStatus": s.ticket_status,
        "ticketUrl": s.ticket_url,
        "description": s.description,
        "flag": s.flag,
        "createdAt": iso(s.created_at),
    }
    if member_ids is not None:
        d["memberIds"] = member_ids
    return d


def news_dict(n) -> dict[str, Any]:
    return {
        "id": n.id,
        "slug": n.slug,
        "title": n.title,
        "summary": n.summary,
        "body": n.body,
        "category": n.category,
        "isHighlighted": n.is_highlighted,
        "views": n.views,
        "publishedAt": iso(n.published_at),
    }


def live_dict(l, slug: Optional[str] = None) -> dict[str, Any]:
    return {
        "id": l.id,
        "memberId": l.member_id,
        "memberName": l.member_name,
        "slug": slug,
        "platform": l.platform,
        "title": l.title or f"Live {l.member_name}",
        "startedAt": iso(l.started_at),
        "endedAt": iso(l.ended_at),
        "viewers": l.viewers,
        "imageUrl": l.image_url,
        "streamUrl": l.stream_url,
        "replayUrl": l.replay_url,
        "roomKey": l.room_key,
    }


def notification_dict(n) -> dict[str, Any]:
    return {
        "id": n.id,
        "userId": n.user_seq,
        "type": n.type,
        "title": n.title,
        "body": n.body,
        "href": n.href,
        "isRead": n.is_read,
        "createdAt": iso(n.created_at),
    }


def wish_dict(w) -> dict[str, Any]:
    return {
        "id": w.id,
        "memberId": w.member_id,
        "userId": w.user_seq,
        "username": w.username,
        "message": w.message,
        "year": w.year,
        "createdAt": iso(w.created_at),
    }


def wish_user_dict(u) -> dict[str, Any]:
    """User bentuk ringkas untuk panel admin (frontend schema.ts users)."""
    return {
        "id": u.seq,
        "username": u.username,
        "email": u.email,
        "name": u.name,
        "role": u.role,
        "bio": u.bio,
        "avatarSeed": u.avatar_seed,
        "theme": u.theme,
        "lang": u.lang,
        "multiLiveLayout": u.multi_live_layout,
        "isPrivate": u.is_private,
        "hideOshi": u.hide_oshi,
        "notifPrefs": u.notif_prefs or {
            "LIVE_ALERT": True,
            "SCHEDULE_REMINDER": True,
            "BIRTHDAY_ALERT": True,
            "NEWS_ALERT": True,
            "CHAT_MENTION": True,
        },
        "blockedUntil": iso(u.blocked_until),
        "blockReason": u.block_reason,
        "mutedUntil": iso(u.muted_until),
        "points": u.points,
        "streak": u.streak,
        "lastDailyDate": u.last_daily_date.isoformat() if u.last_daily_date else None,
        "createdAt": iso(u.created_at),
        "isEmailVerified": u.is_email_verified,
    }
