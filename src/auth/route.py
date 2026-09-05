from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordRequestForm

from src.auth.constants import (
    REFRESH_TOKEN_COOKIE_KEY,
    REFRESH_TOKEN_MAX_AGE,
    ErrorCode,
    Info,
)
from src.auth.csrf_service import CSRFService
from src.auth.exceptions import (
    InvalidRefreshTokenError,
    PasswordResetTokenInvalidError,
    VerificationTokenInvalidError,
)
from src.auth.http_exceptions import EmailNotFoundOrVerified
from src.auth.schemas import (
    EmailVerificationRequest,
    EmailVerificationResponse,
    LogoutResponse,
    PasswordResetConfirmRequest,
    PasswordResetConfirmResponse,
    PasswordResetOtpConfirmRequest,
    PasswordResetOtpRequest,
    PasswordResetOtpResponse,
    PasswordResetRequest,
    PasswordResetResponse,
    Token,
    VerifyEmailRequest,
    VerifyEmailResponse,
)
from src.auth.service import AuthService
from src.config import Settings, config
from src.dependencies import (
    get_auth_service,
    get_settings,
    require_csrf_protection,
)
from src.limiter import limiter
from src.logging_config import create_logger


def _extract_request_info(request: Request):
    user_agent = request.headers.get("user-agent", "")

    ip = request.client.host if request.client else "unknown"
    if config.trust_proxy_headers:
        cf_ip = request.headers.get("cf-connecting-ip")
        if cf_ip:
            ip = cf_ip.strip()
        else:
            x_forwarded_for = request.headers.get("x-forwarded-for")
            if x_forwarded_for:
                ip = x_forwarded_for.split(",")[0].strip()

    from user_agents import parse as parse_ua

    ua = parse_ua(user_agent)
    device = f"{ua.device.family or 'Unknown'} {ua.os.family or 'Unknown'} {ua.os.version_string or ''}".strip()
    browser = (
        f"{ua.browser.family or 'Unknown'} {ua.browser.version_string or ''}".strip()
    )
    return device, ip, browser, user_agent


def _set_auth_cookies(response: Response, refresh_token: str, config: Settings):
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_KEY,
        value=refresh_token,
        httponly=True,
        max_age=REFRESH_TOKEN_MAX_AGE,
        path="/",
        samesite="lax",
        secure=not config.is_env_dev,
        domain=config.cookie_domain,
    )

    _set_csrf_cookie(response, config)


def _set_csrf_cookie(response: Response, config: Settings):
    csrf_token = CSRFService.generate_csrf_token()
    response.set_cookie(
        key=CSRFService.CSRF_TOKEN_COOKIE,
        value=csrf_token,
        httponly=False,
        max_age=REFRESH_TOKEN_MAX_AGE,
        path="/",
        samesite="lax",
        secure=not config.is_env_dev,
        domain=config.cookie_domain,
    )


def _set_access_token_cookie(response: Response, access_token: str, config: Settings):
    response.set_cookie(
        key="token",
        value=access_token,
        httponly=True,
        max_age=config.access_token_expire_minutes * 60,
        path="/",
        samesite="lax",
        secure=not config.is_env_dev,
        domain=config.cookie_domain,
    )


router = APIRouter()

logger = create_logger("auth", __name__)


@router.post("/auth/signin", response_model=Token)
@limiter.limit(f"{config.auth_requests_per_minute}/minute", override_defaults=True)
async def signin_with_email_and_password(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    access_code: str = Form(default=""),
    response: Response = None,
    auth_service: AuthService = Depends(get_auth_service),
    config: Settings = Depends(get_settings),
):
    """
    Sign in using email and password. Returns an access token and sets a refresh token cookie.

    Akun staff (slot ADMIN_n / MOD_n di environment) WAJIB mengirim field
    ``access_code``. Slot yang tidak lengkap (username/email/password/code akses
    tidak 4/4) otomatis nonaktif (false) dan tidak bisa login sampai dilengkapi.

    Parameters:
        request (Request): FastAPI request object.
        form_data (OAuth2PasswordRequestForm): Form data containing username and password.
        access_code (str): Code akses staff (opsional untuk user biasa).
        response (Response): FastAPI response object (used to set cookies).

    Returns:
        Token: Access token and token type.
    """

    user = await auth_service.authenticate_user(form_data.username, form_data.password)

    # --- Gerbang kredensial staff: code akses wajib & harus sama persis ---
    from src.auth import staff_credentials

    gate = staff_credentials.gate_login(user.username, user.email, access_code)
    if gate is not None:
        status_code = 403 if gate.code == "SLOT_INCOMPLETE" else 401
        logger.warning(
            f"[staff] login ditolak untuk '{user.username}' ({gate.code}): {gate.message}"
        )
        if gate.code != "SLOT_INCOMPLETE":
            # hitung sebagai percobaan gagal (maks MAX_LOGIN_ATTEMPTS)
            await auth_service.security_service.handle_failed_login(
                user.userId, user.email, user.username
            )
        raise HTTPException(status_code=status_code, detail=gate.message)

    if (
        user.provider == staff_credentials.PROVIDER
        and not staff_credentials.find_credential(user.username, user.email)
    ):
        raise HTTPException(status_code=403, detail="Akun staff sudah dinonaktifkan.")

    # Blokir khusus JKT48Verse (sanksi moderator/admin)
    from sqlalchemy import select as sa_select

    from src.database import database_instance
    from src.models import User as _UserModel

    async with database_instance.session_factory() as _s:
        _row = (
            await _s.execute(
                sa_select(_UserModel).where(_UserModel.user_id == user.userId)
            )
        ).scalar_one_or_none()
    if (
        _row is not None
        and _row.blocked_until
        and _row.blocked_until > datetime.now(timezone.utc)
    ):
        _until = _row.blocked_until.astimezone(
            timezone(offset=__import__("datetime").timedelta(hours=7))
        ).strftime("%d %b %Y %H:%M")
        return JSONResponse(
            status_code=403,
            content={
                "detail": f"Akun diblokir hingga {_until} WIB. Alasan: {_row.block_reason or '-'}"
            },
        )

    await auth_service.complete_login(user.userId)
    device, ip, browser, user_agent = _extract_request_info(request)
    refresh_token = await auth_service.register_refresh_token_activity(
        user.userId, device, ip, browser, user_agent
    )
    access_token = auth_service.create_access_token(
        data={"sub": user.userId, "sid": auth_service.hash_token(refresh_token)}
    )

    _set_auth_cookies(response, refresh_token, config)
    _set_access_token_cookie(response, access_token, config)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/auth/refresh", response_model=Token)
async def refresh_access_token(
    request: Request,
    response: Response,
    _=Depends(require_csrf_protection),
    auth_service: AuthService = Depends(get_auth_service),
    config: Settings = Depends(get_settings),
):
    """
    Refresh the access token using a valid refresh token from cookies.

    Parameters:
        request (Request): FastAPI request object (must contain refresh_token cookie).
        response (Response): FastAPI response object.

    Returns:
        Token: New access token and token type.
    """

    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        logger.warning("No refresh_token in cookie.")
        raise InvalidRefreshTokenError()

    hash_refresh_token = auth_service.hash_token(refresh_token)
    token_data = await auth_service.get_refresh_token(hash_refresh_token)
    if not token_data:
        logger.warning("Token data not found")
        raise InvalidRefreshTokenError()

    if (
        await auth_service.get_session_user(token_data["userId"], hash_refresh_token)
        is None
    ):
        await auth_service.delete_refresh_token(hash_refresh_token)
        # Return, rather than raise, so revocation is committed by get_session.
        return JSONResponse(
            status_code=401,
            content={"detail": "Sesi sudah tidak berlaku. Silakan login kembali."},
        )

    device, ip, browser, user_agent = _extract_request_info(request)

    # Check for mismatches but be lenient with IP changes
    mismatches = []
    if token_data["device"] != device:
        mismatches.append(f"device ({token_data['device']} -> {device})")
    if token_data["browser"] != browser:
        mismatches.append(f"browser ({token_data['browser']} -> {browser})")

    if mismatches:
        logger.warning(
            f"Security mismatch detected for user_id={token_data.get('userId')}: {', '.join(mismatches)}"
        )
        await auth_service.delete_refresh_token(hash_refresh_token)
        return JSONResponse(
            status_code=403,
            content={"detail": "Perangkat sesi tidak cocok. Silakan login kembali."},
        )

    # Log IP change but don't invalidate session
    if token_data["ip"] != ip:
        logger.info(
            f"IP change detected for user_id={token_data.get('userId')}: {token_data['ip']} -> {ip}. Allowing refresh because device/browser matched."
        )

    created_at = token_data["createdAt"]
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    age_days = (datetime.now(timezone.utc) - created_at).days
    if age_days >= config.refresh_token_max_age_days:
        await auth_service.delete_refresh_token(hash_refresh_token)
        return JSONResponse(
            status_code=401,
            content={"detail": "Sesi kedaluwarsa. Silakan login kembali."},
        )

    threshold_days = 7
    should_rotate = age_days >= (config.refresh_token_max_age_days - threshold_days)

    if should_rotate:
        await auth_service.delete_refresh_token(hash_refresh_token)
        refresh_token = await auth_service.register_refresh_token_activity(
            token_data["userId"], device, ip, browser, user_agent
        )
        _set_auth_cookies(response, refresh_token, config)
    else:
        await auth_service.update_refresh_token_last_used(hash_refresh_token)
        await auth_service.save_login_history(
            token_data["userId"],
            device,
            ip,
            browser,
            user_agent_raw=user_agent,
        )

    access_token = auth_service.create_access_token(
        data={
            "sub": token_data["userId"],
            "sid": auth_service.hash_token(refresh_token),
        }
    )
    _set_access_token_cookie(response, access_token, config)

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/auth/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    response: Response,
    _=Depends(require_csrf_protection),
    auth_service: AuthService = Depends(get_auth_service),
    config: Settings = Depends(get_settings),
):
    """
    Log out the current user by deleting the refresh token cookie and invalidating the token in the database.

    Returns:
        LogoutResponse: Message indicating logout success.
    """

    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        hash_refresh_token = auth_service.hash_token(refresh_token)
        await auth_service.delete_refresh_token(hash_refresh_token)
        response.delete_cookie(
            key="refresh_token",
            path="/",
            samesite="lax",
            secure=not config.is_env_dev,
            httponly=True,
            domain=config.cookie_domain,
        )
    response.delete_cookie(
        key="token",
        path="/",
        samesite="lax",
        secure=not config.is_env_dev,
        httponly=True,
        domain=config.cookie_domain,
    )
    return LogoutResponse(message=Info.LOGOUT_SUCCESS)


# ---- JKT48Verse: viewer saat ini (dipakai frontend Next.js) ----
@router.get("/auth/me")
async def current_viewer(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    from src.auth.exceptions import InvalidJWTTokenError
    from src.verse.deps import build_viewer, GUEST_VIEWER

    token = request.cookies.get("token")
    if not token:
        header = request.headers.get("authorization", "")
        if header.lower().startswith("bearer "):
            token = header.split(" ", 1)[1]
    if not token and not request.cookies.get("refresh_token"):
        return dict(GUEST_VIEWER)
    if token:
        try:
            token_data = auth_service.verify_access_token(token)
        except InvalidJWTTokenError:
            pass
        else:
            user = await auth_service.get_session_user(
                token_data.username, token_data.session_id
            )
            if user is not None:
                return build_viewer(user)
    return JSONResponse(
        status_code=401,
        content={
            "detail": "Sesi sudah tidak berlaku. Silakan perbarui sesi atau login kembali."
        },
    )


class OtpVerifyRequest(BaseModel):
    email: str
    code: str


@router.post("/auth/verify-otp")
async def verify_otp_endpoint(
    request_data: OtpVerifyRequest,
    auth_service: AuthService = Depends(get_auth_service),
    config: Settings = Depends(get_settings),
):
    """Verifikasi email memakai kode OTP 6 digit."""
    success, message = await auth_service.verify_email_otp(
        request_data.email, request_data.code
    )
    if success:
        return {"message": message, "verified": True}
    return JSONResponse(
        status_code=400, content={"message": message, "verified": False}
    )


class OtpResendRequest(BaseModel):
    email: str


@router.post("/auth/resend-otp")
@limiter.limit(f"{config.auth_requests_per_minute}/minute", override_defaults=True)
async def resend_otp_endpoint(
    request: Request,
    request_data: OtpResendRequest,
    auth_service: AuthService = Depends(get_auth_service),
    config: Settings = Depends(get_settings),
):
    """Kirim ulang kode OTP verifikasi email."""
    result = await auth_service.resend_email_otp(request_data.email)
    payload: dict = {
        "message": "Jika email terdaftar dan belum terverifikasi, kode OTP telah dikirim."
    }
    if isinstance(result, dict) and result.get("devCode"):
        payload["devCode"] = result["devCode"]
    return payload


# Email Verification Endpoints
@router.post("/auth/send-verification", response_model=EmailVerificationResponse)
@limiter.limit(f"{config.auth_requests_per_minute}/minute", override_defaults=True)
async def send_email_verification(
    request: Request,
    request_data: EmailVerificationRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Send a verification email to the user for email verification.

    Parameters:
        request (Request): FastAPI request object.
        request_data (EmailVerificationRequest): Email to send verification to.

    Returns:
        EmailVerificationResponse: Message indicating email sent or error.
    """
    result = await auth_service.resend_verification_email(request_data.email)
    if result:
        return EmailVerificationResponse(message=Info.EMAIL_VERIFICATION_SENT)
    else:
        # Don't reveal if user doesn't exist or is already verified
        raise EmailNotFoundOrVerified()


@router.post("/auth/verify-email", response_model=VerifyEmailResponse)
async def verify_email_endpoint(
    request_data: VerifyEmailRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Verify user's email using the provided token.

    Parameters:
        request_data (VerifyEmailRequest): Contains the verification token.

    Returns:
        VerifyEmailResponse: Message indicating verification result.
    """

    success = await auth_service.verify_email(request_data.token)
    if success:
        return VerifyEmailResponse(message=ErrorCode.EMAIL_VERIFIED_SUCCESS)
    else:
        raise VerificationTokenInvalidError()


# Password Reset Endpoints
@router.post("/auth/forgot-password", response_model=PasswordResetResponse)
@limiter.limit(f"{config.auth_requests_per_minute}/minute", override_defaults=True)
async def forgot_password(
    request: Request,
    request_data: PasswordResetRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Send a password reset email to the user.

    Parameters:
        request (Request): FastAPI request object.
        request_data (PasswordResetRequest): Email to send password reset link to.

    Returns:
        PasswordResetResponse: Message indicating reset email sent.
    """
    await auth_service.create_password_reset_token(request_data.email)

    return PasswordResetResponse(message=ErrorCode.PASSWORD_RESET_SENT)


@router.post("/auth/reset-password", response_model=PasswordResetConfirmResponse)
async def reset_password_endpoint(
    request_data: PasswordResetConfirmRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Reset the user's password using the provided token and new password.

    Parameters:
        request_data (PasswordResetConfirmRequest): Contains token, new password, and confirmation.

    Returns:
        PasswordResetConfirmResponse: Message indicating password reset result.
    """

    success = await auth_service.reset_password(
        request_data.token, request_data.new_password
    )
    if success:
        return PasswordResetConfirmResponse(message=ErrorCode.PASSWORD_RESET_SUCCESS)
    else:
        raise PasswordResetTokenInvalidError()


# Password Reset via OTP (JKT48Verse)
@router.post(
    "/auth/forgot-password/otp",
    response_model=PasswordResetOtpResponse,
    response_model_exclude_none=True,
)
@limiter.limit(f"{config.auth_requests_per_minute}/minute", override_defaults=True)
async def forgot_password_otp(
    request: Request,
    request_data: PasswordResetOtpRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Minta kode OTP 6 digit untuk reset password (dikirim ke email).

    Respons selalu sama untuk email terdaftar maupun tidak (anti-enumerasi).
    Kode berlaku 10 menit; meminta kode baru otomatis mengganti kode lama.
    Pada ENV=dev tanpa Resend, kode dikembalikan sebagai ``devCode``.
    """
    result = await auth_service.resend_password_reset_otp(request_data.email)
    payload: dict = {
        "message": "Jika email terdaftar, kode OTP reset password telah dikirim."
    }
    if isinstance(result, dict) and result.get("devCode"):
        payload["devCode"] = result["devCode"]
    return payload


@router.post("/auth/reset-password/otp")
@limiter.limit(f"{config.auth_requests_per_minute}/minute", override_defaults=True)
async def reset_password_otp_endpoint(
    request: Request,
    request_data: PasswordResetOtpConfirmRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Reset password memakai kode OTP 6 digit yang dikirim via email.

    Selain mengganti password, semua sesi login dicabut dan lockout akun
    (akibat salah password berulang) dipulihkan.
    """
    if request_data.new_password != request_data.confirm_password:
        return JSONResponse(
            status_code=400,
            content={"message": "Konfirmasi password tidak cocok.", "reset": False},
        )
    if not 8 <= len(request_data.new_password) <= 64:
        return JSONResponse(
            status_code=400,
            content={
                "message": "Password minimal 8 karakter (maksimal 64 karakter).",
                "reset": False,
            },
        )

    success, message = await auth_service.reset_password_with_otp(
        request_data.email, request_data.code, request_data.new_password
    )
    if success:
        return {"message": message, "reset": True}
    return JSONResponse(
        status_code=400, content={"message": message, "reset": False}
    )
