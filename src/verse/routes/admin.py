"""Panel Admin & Moderator: daftar user, sanksi, laporan, log login."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.models import LoginHistory, ModerationLog, Notification, Report, User
from src.verse.deps import require_admin, require_moderator
from src.verse.helpers import wish_user_dict

router = APIRouter()


@router.get("/admin/users")
async def list_users(
    limit: int = 100,
    viewer: dict = Depends(require_moderator),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        (
            await session.execute(
                select(User).order_by(desc(User.created_at)).limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return [wish_user_dict(u) for u in rows]


@router.get("/admin/login-logs")
async def login_logs(
    limit: int = 20,
    viewer: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        (
            await session.execute(
                select(LoginHistory).order_by(desc(LoginHistory.login_at)).limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": r.id,
            "userId": r.user_id,
            "username": r.username,
            "success": r.success,
            "kind": r.kind,
            "device": r.device,
            "ip": r.ip,
            "browser": r.browser,
            "createdAt": (r.login_at or datetime.now(timezone.utc)).isoformat(),
        }
        for r in rows
    ]


@router.get("/admin/moderation-logs")
async def moderation_logs(
    limit: int = 50,
    viewer: dict = Depends(require_moderator),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        (
            await session.execute(
                select(ModerationLog)
                .order_by(desc(ModerationLog.created_at))
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": r.id,
            "userId": r.user_seq,
            "kind": r.kind,
            "detail": r.detail,
            "createdAt": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/moderation/reports")
async def list_reports(
    status: Optional[str] = None,
    viewer: dict = Depends(require_moderator),
    session: AsyncSession = Depends(get_session),
):
    from src.models import ChatMessage

    conds = [Report.status == (status or "pending")]
    if status == "all":
        conds = []
    rows = (
        await session.execute(
            select(Report, ChatMessage)
            .join(ChatMessage, ChatMessage.id == Report.message_id)
            .where(*conds)
            .order_by(desc(Report.created_at))
            .limit(100)
        )
    ).all()
    # info user target untuk tombol sanksi
    target_seqs = [r.target_user_seq for r, _ in rows if r.target_user_seq]
    targets = {}
    if target_seqs:
        t_rows = (
            (await session.execute(select(User).where(User.seq.in_(target_seqs))))
            .scalars()
            .all()
        )
        targets = {t.seq: t for t in t_rows}
    out = []
    for r, m in rows:
        t = targets.get(r.target_user_seq)
        out.append(
            {
                "id": r.id,
                "messageId": r.message_id,
                "reporterId": r.reporter_seq,
                "targetUserId": r.target_user_seq,
                "targetUsername": r.target_username,
                "targetRole": t.role if t else None,
                "targetAvatarSeed": t.avatar_seed if t else None,
                "reason": r.reason,
                "description": r.description,
                "status": r.status,
                "createdAt": r.created_at.isoformat() if r.created_at else None,
                "message": {
                    "username": m.username,
                    "body": m.body,
                    "isHidden": m.is_hidden,
                },
            }
        )
    return out


class ResolveIn(BaseModel):
    decision: str  # approved | rejected


@router.post("/moderation/reports/{report_id}/resolve")
async def resolve_report(
    report_id: int,
    data: ResolveIn,
    viewer: dict = Depends(require_moderator),
    session: AsyncSession = Depends(get_session),
):
    from src.models import ChatMessage

    r = await session.get(Report, report_id)
    if not r:
        return {"ok": False, "error": "Laporan tidak ditemukan."}
    r.status = data.decision
    if data.decision == "approved":
        m = await session.get(ChatMessage, r.message_id)
        if m:
            m.is_hidden = True
    session.add(
        ModerationLog(
            user_seq=viewer.get("userId"),
            kind=f"report:{data.decision}",
            detail=f"laporan #{report_id} — oleh {viewer.get('username')} ({viewer.get('role')})",
        )
    )
    return {"ok": True}


class SanctionIn(BaseModel):
    userId: int
    kind: str  # mute | block | unblock
    duration: str  # hours number | "permanent"
    reason: str = ""


@router.post("/admin/sanction")
async def sanction_user(
    data: SanctionIn,
    viewer: dict = Depends(require_moderator),
    session: AsyncSession = Depends(get_session),
):
    user = (
        await session.execute(select(User).where(User.seq == data.userId))
    ).scalar_one_or_none()
    if not user:
        return {"ok": False, "error": "User tidak ditemukan."}
    if user.role == "ADMIN" and viewer.get("role") != "ADMIN":
        return {"ok": False, "error": "Tidak dapat menyanksi ADMIN."}
    if viewer.get("role") == "MODERATOR":
        if user.role != "MEMBER":
            return {
                "ok": False,
                "error": "Moderator hanya dapat memblokir akun MEMBER.",
            }
        if data.duration == "permanent":
            return {"ok": False, "error": "Ban permanen memerlukan approval Admin."}
        if data.kind == "block":
            try:
                if float(data.duration) > 30 * 24:
                    return {"ok": False, "error": "Moderator maksimal ban 30 hari."}
            except ValueError:
                pass

    now = datetime.now(timezone.utc)
    if data.duration == "permanent":
        until = datetime(2099, 1, 1, tzinfo=timezone.utc)
        dur_label = "permanen"
    else:
        try:
            hours = float(data.duration)
        except ValueError:
            hours = 24
        until = now + timedelta(hours=hours)
        dur_label = (
            until.astimezone(
                timezone(offset=__import__("datetime").timedelta(hours=7))
            ).strftime("%d %b %Y %H:%M")
            + " WIB"
        )

    if data.kind == "mute":
        user.muted_until = until
        title = "Kamu di-mute dari chat"
    elif data.kind == "block":
        user.blocked_until = until
        user.block_reason = data.reason
        from sqlalchemy import delete
        from src.models import RefreshToken

        await session.execute(
            delete(RefreshToken).where(RefreshToken.user_id == user.user_id)
        )
        title = "Akun kamu diblokir"
    else:
        user.blocked_until = None
        user.muted_until = None
        user.block_reason = None

    if data.kind != "unblock":
        session.add(
            Notification(
                user_seq=user.seq,
                type="SYSTEM",
                title=title,
                body=f"Alasan: {data.reason}. Berlaku hingga {dur_label}.",
            )
        )
    session.add(
        ModerationLog(
            user_seq=user.seq,
            kind=f"{data.kind}:{data.duration}",
            detail=f"{data.reason} — oleh {viewer.get('username')} ({viewer.get('role')})",
        )
    )
    return {"ok": True}


@router.get("/admin/stats")
async def admin_stats(
    viewer: dict = Depends(require_moderator),
    session: AsyncSession = Depends(get_session),
):
    admins = (
        await session.execute(
            select(func.count()).select_from(User).where(User.role == "ADMIN")
        )
    ).scalar() or 0
    moderators = (
        await session.execute(
            select(func.count()).select_from(User).where(User.role == "MODERATOR")
        )
    ).scalar() or 0
    pending = (
        await session.execute(
            select(func.count()).select_from(Report).where(Report.status == "pending")
        )
    ).scalar() or 0
    return {"admins": admins, "moderators": moderators, "pendingReports": pending}


# =====================================================================
# KREDENSIAL STAFF (3 Admin + 10 Moderator) — status slot env
# =====================================================================
@router.get("/admin/credentials")
async def credential_slots(viewer: dict = Depends(require_admin)):
    """Status tiap slot kredensial: aktif (4/4 lengkap) atau false + alasannya."""
    from src.auth import staff_credentials

    return {
        "ok": True,
        "summary": staff_credentials.summary(),
        "slots": staff_credentials.report(),
    }


@router.post("/admin/credentials/reload")
async def reload_credentials(
    viewer: dict = Depends(require_admin), session: AsyncSession = Depends(get_session)
):
    """Synchronize staff accounts and revoke sessions for disabled credentials."""
    from scripts.seed import seed_staff
    from src.auth import staff_credentials

    await seed_staff(session)
    return {"ok": True, "summary": staff_credentials.summary()}


# =====================================================================
# ROUTER API KEY LLM — monitoring anti-limit
# =====================================================================
@router.get("/admin/ai/keys")
async def llm_key_stats(viewer: dict = Depends(require_admin)):
    """Statistik router API key: key mana yang sehat, mana yang sedang cooldown."""
    from src.verse.llm_router import get_router

    return {"ok": True, "data": get_router().stats()}


@router.post("/admin/ai/keys/reload")
async def reload_llm_keys(viewer: dict = Depends(require_admin)):
    """Baca ulang LLM_API_KEYS dari environment tanpa restart."""
    from src.verse.llm_router import get_router, reset_router

    reset_router()
    return {"ok": True, "data": get_router().stats()}
