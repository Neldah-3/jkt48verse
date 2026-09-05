from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Response
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
    RefreshTokenExpiredError,
    SuspiciousActivityError,
    VerificationTokenInvalidError,
)
from src.auth.http_exceptions import EmailNotFoundOrVerified
from src.auth.schemas import (
    EmailVerificationRequest,
    EmailVerificationResponse,
    LogoutResponse,
    PasswordResetConfirmRequest,
    PasswordResetConfirmResponse,
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
    response: Response = None,
    auth_service: AuthService = Depends(get_auth_service),
    config: Settings = Depends(get_settings),
):
    """
    Sign in using email and password. Returns an access token and sets a refresh token cookie.

    Parameters:
        request (Request): FastAPI request object.
        form_data (OAuth2PasswordRequestForm): Form data containing username and password.
        response (Response): FastAPI response object (used to set cookies).

    Returns:
        Token: Access token and token type.
    """

    user = await auth_service.authenticate_user(form_data.username, form_data.password)

    # Blokir khusus JKT48Verse (sanksi moderator/admin)
    from sqlalchemy import func as sa_func, or_ as sa_or_, select as sa_select

    from src.database import database_instance
    from src.models import User as _UserModel

    _ident = form_data.username.lower()
    async with database_instance.session_factory() as _s:
        _row = (
            await _s.execute(
                sa_select(_UserModel).where(
                    sa_or_(
                        sa_func.lower(_UserModel.username) == _ident,
                        sa_func.lower(_UserModel.email) == _ident,
                        _UserModel.user_id == _ident,
                    )
                )
            )
        ).scalar_one_or_none()
    if _row is not None and _row.blocked_until and _row.blocked_until > datetime.now(timezone.utc):
        _until = _row.blocked_until.astimezone(
            timezone(offset=__import__("datetime").timedelta(hours=7))
        ).strftime("%d %b %Y %H:%M")
        return JSONResponse(
            status_code=403,
            content={"detail": f"Akun diblokir hingga {_until} WIB. Alasan: {_row.block_reason or '-'}"},
        )

    access_token = auth_service.create_access_token(data={"sub": user.userId})

    device, ip, browser, user_agent = _extract_request_info(request)
    refresh_token = await auth_service.register_refresh_token_activity(
        user.userId, device, ip, browser, user_agent
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
        raise SuspiciousActivityError()

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
        raise RefreshTokenExpiredError()

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

    access_token = auth_service.create_access_token(data={"sub": token_data["userId"]})
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
    from src.verse.deps import build_viewer, GUEST_VIEWER
    from src.database import database_instance

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
    from sqlalchemy import select
    from src.models import User

    async with database_instance.session_factory() as session:
        result = await session.execute(select(User).where(User.user_id == token_data.username))
        user = result.scalar_one_or_none()
        if user is None:
            return dict(GUEST_VIEWER)
        return build_viewer(user)


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
    success, message = await auth_service.verify_email_otp(request_data.email, request_data.code)
    if success:
        return {"message": message, "verified": True}
    return JSONResponse(status_code=400, content={"message": message, "verified": False})


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
    payload: dict = {"message": "Jika email terdaftar dan belum terverifikasi, kode OTP telah dikirim."}
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
