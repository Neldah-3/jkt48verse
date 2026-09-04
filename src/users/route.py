"""Users: registrasi akun JKT48Verse (email + password + verifikasi OTP)."""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.service import AuthService
from src.database import get_session
from src.dependencies import get_auth_service
from src.limiter import limiter
from src.config import config
from src.logging_config import create_logger
from src.users.service import UserService, UsernameTakenError, EmailTakenError

router = APIRouter()
logger = create_logger("users_route", __name__)


class SignupRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class SignupResponse(BaseModel):
    userId: str
    username: str
    email: str
    message: str
    devCode: str | None = None


@router.post("/users/signup", status_code=201, response_model=SignupResponse)
@limiter.limit(f"{config.auth_requests_per_minute}/minute", override_defaults=True)
async def signup(
    request: Request,
    data: SignupRequest,
    session: AsyncSession = Depends(get_session),
    auth_service: AuthService = Depends(get_auth_service),
):
    import re as _re

    username = data.username.strip()
    if not _re.fullmatch(r"[a-zA-Z0-9]{3,20}", username):
        return SignupResponse(
            userId="", username=username, email=data.email,
            message="Username 3–20 karakter alfanumerik.",
        )
    if _re.match(r"^(admin|mod|moderator)", username, _re.IGNORECASE):
        return SignupResponse(
            userId="", username=username, email=data.email,
            message="Username tidak tersedia.",
        )
    if len(data.password) < 8:
        return SignupResponse(
            userId="", username=username, email=data.email,
            message="Password minimal 8 karakter.",
        )

    service = UserService(session)
    try:
        user = await service.create_user(
            username=username, email=data.email.lower(), password=data.password
        )
    except UsernameTakenError:
        return SignupResponse(userId="", username=username, email=data.email, message="Username sudah dipakai.")
    except EmailTakenError:
        return SignupResponse(userId="", username=username, email=data.email, message="Email sudah terdaftar.")

    # notifikasi selamat datang
    from src.models import Notification

    session.add(
        Notification(
            user_seq=user.seq,
            type="SYSTEM",
            title="Selamat datang di JKT48Verse!",
            body="Atur oshi-mu di halaman Akun agar Live Alert & Birthday Alert aktif.",
            href="/account",
        )
    )

    otp = await auth_service.create_email_otp(user.user_id, user.email, user.username)
    dev_code = None
    if not otp["sent"] and config.is_env_dev:
        logger.info(f"[DEV] OTP untuk {user.email}: {otp['code']}")
        dev_code = otp["code"]

    return SignupResponse(
        userId=user.user_id,
        username=user.username,
        email=user.email,
        message="Akun dibuat. Kode OTP verifikasi telah dikirim ke email-mu.",
        devCode=dev_code,
    )
