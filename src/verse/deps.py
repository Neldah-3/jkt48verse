"""Dependency auth untuk rute verse: viewer dari cookie token JWT backend."""

from typing import Any, Optional

from fastapi import Depends, Request

from src.auth.http_exceptions import InvalidJWTToken
from src.dependencies import get_auth_service
from src.auth.service import AuthService
from src.models import User
from src.verse.helpers import wish_user_dict

GUEST_VIEWER: dict[str, Any] = {
    "role": "GUEST",
    "userId": None,
    "username": "Tamu",
    "avatarSeed": 1,
    "staffId": None,
    "isBlocked": False,
    "isMuted": False,
    "user": None,
}


def _site_role(user: User) -> str:
    if user.role in ("ADMIN", "MODERATOR"):
        return user.role
    return "MEMBER"


def build_viewer(user: User) -> dict[str, Any]:
    now = __import__("src.verse.helpers", fromlist=["now_utc"]).now_utc()
    blocked = bool(user.blocked_until and user.blocked_until > now)
    muted = bool(user.muted_until and user.muted_until > now)
    return {
        "role": _site_role(user),
        "userId": user.seq,
        "username": user.username,
        "avatarSeed": user.avatar_seed,
        "staffId": None,
        "isBlocked": blocked,
        "isMuted": muted,
        "user": wish_user_dict(user),
    }


async def get_viewer(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, Any]:
    token = request.cookies.get("token")
    if not token:
        header = request.headers.get("authorization")
        if header and header.lower().startswith("bearer "):
            token = header.split(" ", 1)[1]
    if not token:
        return dict(GUEST_VIEWER)
    try:
        token_data = auth_service.verify_access_token(token)
    except Exception:
        return dict(GUEST_VIEWER)
    user = await auth_service.get_session_user(
        token_data.username, token_data.session_id
    )
    if user is None:
        return dict(GUEST_VIEWER)
    return build_viewer(user)


async def require_user(
    viewer: dict[str, Any] = Depends(get_viewer),
) -> dict[str, Any]:
    if viewer["role"] == "GUEST" or not viewer["userId"]:
        raise InvalidJWTToken()
    return viewer


def _require_role(viewer: dict[str, Any], roles: tuple[str, ...]) -> dict[str, Any]:
    if viewer["role"] not in roles:
        from src.http_exceptions import AdminRequired

        raise AdminRequired()
    return viewer


async def require_moderator(
    viewer: dict[str, Any] = Depends(get_viewer)
) -> dict[str, Any]:
    return _require_role(viewer, ("MODERATOR", "ADMIN"))


async def require_admin(viewer: dict[str, Any] = Depends(get_viewer)) -> dict[str, Any]:
    return _require_role(viewer, ("ADMIN",))


def viewer_summary(viewer: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    v = viewer or GUEST_VIEWER
    return {
        "role": v["role"],
        "userId": v.get("userId"),
        "username": v.get("username"),
        "avatarSeed": v.get("avatarSeed", 1),
        "isBlocked": v.get("isBlocked", False),
        "isMuted": v.get("isMuted", False),
    }
