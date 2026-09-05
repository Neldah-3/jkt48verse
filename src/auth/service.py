import asyncio
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Union

from jose import JWTError, jwt

from src.auth import staff_credentials
from src.auth.email_service import EmailService
from src.auth.exceptions import (
    AuthOperationError,
    IncorrectCredentialsError,
    InvalidJWTTokenError,
)
from src.auth.repository import AuthRepository
from src.auth.schemas import TokenData, UserLogin
from src.auth.security_service import SecurityService
from src.config import Settings
from src.logging_config import create_logger
from src.models import User
from src.users.exceptions import AccountLocked, EmailNotVerified
from src.users.repository import UserRepository
from src.utils import hash_token

logger = create_logger("auth_service", __name__)


class AuthService:
    def __init__(
        self,
        auth_repo: AuthRepository,
        user_repo: UserRepository,
        security_service: SecurityService,
        email_service: EmailService,
        config: Settings,
    ):
        self.auth_repo = auth_repo
        self.user_repo = user_repo
        self.security_service = security_service
        self.email_service = email_service
        self.config = config

    async def verify_password(self, plain_password, hashed_password) -> str:
        try:
            return await asyncio.to_thread(
                self.security_service.verify_password, plain_password, hashed_password
            )
        except Exception as e:
            logger.exception(f"Error verifying password: {str(e)}")
            raise AuthOperationError()

    async def get_password_hash(self, password) -> str:
        try:
            return await asyncio.to_thread(
                self.security_service.get_password_hash, password
            )
        except Exception as e:
            logger.exception(f"Error hashing password: {str(e)}")
            raise AuthOperationError()

    def create_access_token(
        self, data: dict, expires_delta: timedelta | None = None
    ) -> str:
        try:
            to_encode = data.copy()
            if expires_delta:
                expire = datetime.now(timezone.utc) + expires_delta
            else:
                expire = datetime.now(timezone.utc) + timedelta(
                    minutes=self.config.access_token_expire_minutes
                )
            to_encode.update({"exp": expire})
            encoded_jwt = jwt.encode(
                to_encode, self.config.secret_key, algorithm=self.config.algorithm
            )
            return encoded_jwt
        except Exception as e:
            logger.exception(f"Error creating access token: {str(e)}")
            raise AuthOperationError()

    def verify_access_token(self, token: str) -> TokenData:
        try:
            payload = jwt.decode(
                token, self.config.secret_key, algorithms=[self.config.algorithm]
            )
            username = payload.get("sub")
            session_id = payload.get("sid")
            if (
                not isinstance(username, str)
                or not isinstance(session_id, str)
                or not session_id
            ):
                raise InvalidJWTTokenError()
            return TokenData(username=username, session_id=session_id)
        except JWTError as e:
            logger.info(f"Access token rejected: {str(e)}")
            raise InvalidJWTTokenError()

    async def get_user(self, username_or_email: str) -> Optional[UserLogin]:
        try:
            query = {
                "$or": [
                    {"username": username_or_email},
                    {"email": username_or_email},
                    {"userId": username_or_email},
                ]
            }
            user = await self.user_repo.find_one(query)
            if user:
                return UserLogin(**user)
            return None
        except Exception as e:
            logger.exception(f"Error getting user: {str(e)}")
            raise AuthOperationError()

    async def authenticate_user(
        self, username_or_email: str, password: str = None, provider: str = None
    ) -> Union[UserLogin, bool]:
        user = await self.get_user(username_or_email)

        # For provider-based auth, skip password verification
        if provider is not None:
            if not user:
                return False
            return user

        # Mitigate timing attacks by always performing verification for password-based auth
        password_hash = (
            await self.user_repo.get_password_hash(user.userId) if user else None
        )
        is_valid_password = False
        if user and password_hash:
            is_valid_password = await self.verify_password(password, password_hash)
        else:
            # Fake verification to prevent timing attacks
            fake_hash = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"
            await self.verify_password(password or "dummy", fake_hash)

        if not user:
            raise IncorrectCredentialsError()

        # Check account lock status
        lock_status = await self.security_service.check_account_lock_status(user.userId)
        if lock_status["is_locked"]:
            raise AccountLocked()

        if not is_valid_password:
            # Handle failed login
            await self.security_service.handle_failed_login(
                user.userId, user.email, user.username
            )
            raise IncorrectCredentialsError()

        if not self.config.is_env_dev and user.provider == "seed":
            raise IncorrectCredentialsError()
        if not user.isEmailVerified:
            raise EmailNotVerified()

        # Do not reset counters yet: the staff access-code gate must also pass.
        return user

    async def complete_login(self, user_id: str) -> None:
        await self.security_service.unlock_account(user_id)
        await self.user_repo.update_last_active(user_id)

    async def get_session_user(self, user_id: str, session_id: str) -> Optional[User]:
        """Every access token is bound to a revocable, server-side session.

        Missing sid (pre-upgrade JWTs), deleted sessions, disabled staff and bans
        must never confer authorization, even when the JWT has not expired yet.
        """
        token = await self.auth_repo.find_refresh_token(session_id)
        if not token or token["userId"] != user_id:
            return None
        now = datetime.now(timezone.utc)
        created_at = token["createdAt"]
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if now >= created_at + timedelta(days=self.config.refresh_token_max_age_days):
            return None
        user = await self.user_repo.find_model_by_id(user_id)
        if user is None or not user.is_email_verified:
            return None
        if user.blocked_until and user.blocked_until > now:
            return None
        if not self.config.is_env_dev and user.provider == "seed":
            return None
        if user.provider == staff_credentials.PROVIDER:
            cred = staff_credentials.find_credential(user.username, user.email)
            if (
                not user.password
                or cred is None
                or cred.username != user.username
                or cred.email != user.email
                or cred.role != user.role
            ):
                return None
        return user

    def extract_user_provider(self, user) -> Dict[str, str]:
        return {
            "profilePicture": user.picture,
            "name": user.display_name,
            "username": user.email,
            "email": user.email,
            "provider": user.provider,
        }

    def create_refresh_token(self) -> str:
        return secrets.token_urlsafe(64)

    def hash_token(self, token: str) -> str:
        return hash_token(token)

    async def save_refresh_token(
        self, user_id: str, refresh_token: str, device: str, ip: str, browser: str
    ):
        try:
            data = {
                "userId": user_id,
                "hashRefreshToken": refresh_token,
                "device": device,
                "ip": ip,
                "browser": browser,
                "createdAt": datetime.now(timezone.utc),
                "lastUsedAt": datetime.now(timezone.utc),
            }
            await self.auth_repo.insert_refresh_token(data)
        except Exception as e:
            logger.exception(f"Error saving refresh token: {str(e)}")
            raise AuthOperationError()

    async def get_refresh_token(self, token: str) -> Optional[dict]:
        try:
            return await self.auth_repo.find_refresh_token(token)
        except Exception as e:
            logger.exception(f"Error getting refresh token: {str(e)}")
            raise AuthOperationError()

    async def update_refresh_token_last_used(self, token: str):
        try:
            await self.auth_repo.update_refresh_token_last_used(token)
        except Exception as e:
            logger.exception(f"Error updating refresh token last used: {str(e)}")
            raise AuthOperationError()

    async def delete_refresh_token(self, token: str):
        try:
            await self.auth_repo.delete_refresh_token(token)
        except Exception as e:
            logger.exception(f"Error deleting refresh token: {str(e)}")
            raise AuthOperationError()

    async def save_login_history(
        self,
        user_id: str,
        device: str,
        ip: str,
        browser: str,
        user_agent_raw: Optional[str] = None,
    ):
        try:
            data = {
                "userId": user_id,
                "device": device,
                "ip": ip,
                "browser": browser,
                "loginAt": datetime.now(timezone.utc),
                "userAgentRaw": user_agent_raw,
            }
            await self.auth_repo.insert_login_history(data)
        except Exception as e:
            logger.exception(f"Error saving login history: {str(e)}")
            raise AuthOperationError()

    async def get_last_login_history(self, user_id: str) -> Optional[dict]:
        try:
            return await self.auth_repo.find_last_login_history(user_id)
        except Exception as e:
            logger.exception(f"Error getting last login history: {str(e)}")
            raise AuthOperationError()

    async def register_refresh_token_activity(
        self, user_id: str, device: str, ip: str, browser: str, user_agent: str
    ) -> str:
        try:
            refresh_token = self.create_refresh_token()
            hash_refresh_token = hash_token(refresh_token)
            await self.save_refresh_token(
                user_id, hash_refresh_token, device, ip, browser
            )
            await self.save_login_history(
                user_id, device, ip, browser, user_agent_raw=user_agent
            )
            await self.user_repo.update_last_active(user_id)
            return refresh_token
        except Exception as e:
            logger.exception(f"Error registering refresh token activity: {str(e)}")
            raise AuthOperationError()

    async def create_email_verification_token(self, user_id: str) -> str:
        """Create and save email verification token"""
        try:
            token = await self.security_service.create_and_save_token(
                user_id,
                "email_verification",
                self.config.email_verification_expire_hours,
            )
            return token
        except Exception as e:
            logger.exception(f"Error creating email verification token: {str(e)}")
            raise AuthOperationError()

    async def verify_email(self, token: str) -> bool:
        """Verify email with token"""
        try:
            token_hash = hash_token(token)
            user_id = await self.security_service.verify_email_token(token_hash)
            return user_id is not None
        except Exception as e:
            logger.exception(f"Error verifying email with token: {str(e)}")
            raise AuthOperationError()

    async def create_password_reset_token(
        self, email: str
    ) -> Optional[tuple[str, str, str]]:
        """
        Create and save password reset token.
        Returns (token, username, email) if user exists, else None.
        """
        try:
            user = await self.get_user(email)
            if not user:
                return None  # Don't reveal if email not exists

            token = await self.security_service.create_and_save_token(
                user.userId,
                "password_reset",
                self.config.password_reset_expire_hours,
            )

            await self.email_service.send_password_reset(
                user.email, token, user.username
            )

            return token, user.username, user.email
        except Exception as e:
            logger.exception(f"Error creating password reset token: {str(e)}")
            raise AuthOperationError()

    async def reset_password(self, token: str, new_password: str) -> bool:
        """Reset password with token"""
        try:
            token_hash = hash_token(token)
            token_data = await self.security_service.verify_token(
                token_hash, "password_reset"
            )
            if not token_data:
                return False

            # Update password using userId
            hashed_password = await self.get_password_hash(new_password)

            await self.user_repo.update_one(
                {"userId": token_data["userId"]},
                {"$set": {"password": hashed_password}},
            )

            await self.auth_repo.delete_user_refresh_tokens(token_data["userId"])
            await self.security_service.delete_token(token_hash, "password_reset")

            user = await self.user_repo.find_one({"userId": token_data["userId"]})
            if user:
                await self.security_service.reset_failed_login_attempts(user["userId"])
                await self.security_service.unlock_account(user["userId"])

            return True
        except Exception as e:
            logger.exception(f"Error resetting password with token: {str(e)}")
            raise AuthOperationError()

    async def resend_verification_email(
        self, email: str
    ) -> Optional[tuple[str, str, str]]:
        """
        Resend verification email.
        Returns (token, username, email) if eligible, else None.
        """
        try:
            user = await self.get_user(email)
            if not user:
                return None

            if user.isEmailVerified:
                return None  # Already verified

            token = await self.create_email_verification_token(user.userId)

            await self.email_service.send_email_verification(
                user.email, token, user.username
            )

            return token, user.username, user.email
        except Exception as e:
            logger.exception(f"Error resending verification email: {str(e)}")
            raise AuthOperationError()

    # ------------------------------------------------------------------
    # JKT48Verse: verifikasi email via OTP 6 digit
    # ------------------------------------------------------------------
    async def create_email_otp(self, user_id: str, email: str, username: str) -> dict:
        """Buat OTP 6 digit (berlaku 10 menit), kirim via email bila Resend aktif."""
        import secrets as _secrets

        code = f"{_secrets.randbelow(1_000_000):06d}"
        code_hash = self.hash_token(code)
        # 10 menit = 1/6 jam
        await self.security_service.save_token(user_id, code_hash, "otp", 10 / 60)
        sent = await self.email_service.send_otp_email(email, code, username)
        return {"code": code, "sent": sent}

    async def verify_email_otp(self, email: str, code: str) -> tuple[bool, str]:
        """Verifikasi kode OTP → tandai email terverifikasi."""
        user = await self.get_user(email)
        if not user:
            return False, "Kode OTP tidak valid atau kedaluwarsa."
        if user.isEmailVerified:
            return True, "Email sudah terverifikasi. Silakan login."
        code_hash = self.hash_token((code or "").strip())
        token_data = await self.security_service.verify_token(code_hash, "otp")
        if not token_data or token_data.get("userId") != user.userId:
            return False, "Kode OTP tidak valid atau kedaluwarsa."
        await self.security_service.delete_token(code_hash, "otp")
        await self.user_repo.set_email_verified(user.userId)
        return True, "Email berhasil diverifikasi. Silakan login."

    async def resend_email_otp(self, email: str) -> Optional[dict]:
        """Kirim ulang OTP. Bila Resend belum diatur & ENV=dev → kembalikan devCode."""
        user = await self.get_user(email)
        if not user or user.isEmailVerified:
            return None
        result = await self.create_email_otp(user.userId, user.email, user.username)
        if not result["sent"] and self.config.is_env_dev:
            logger.info(f"[DEV] OTP untuk {email}: {result['code']}")
            return {"devCode": result["code"]}
        return {}

    # ------------------------------------------------------------------
    # JKT48Verse: lupa & reset password via OTP 6 digit
    # ------------------------------------------------------------------
    RESET_OTP_TYPE = "reset_otp"
    RESET_OTP_TTL_MINUTES = 10
    RESET_OTP_MAX_ATTEMPTS = 5

    def _reset_otp_attempts_key(self, user_id: str) -> str:
        return f"reset_otp_attempts:{user_id}"

    async def create_password_reset_otp(self, email: str) -> Optional[dict]:
        """Buat OTP 6 digit untuk reset password (berlaku 10 menit).

        Return ``None`` bila email tidak terdaftar supaya keberadaan akun
        tidak bocor. Kode baru otomatis mengganti kode lama.
        """
        user = await self.get_user(email)
        if not user:
            return None

        import secrets as _secrets

        code = f"{_secrets.randbelow(1_000_000):06d}"
        code_hash = self.hash_token(code)
        await self.security_service.save_token(
            user.userId, code_hash, self.RESET_OTP_TYPE, self.RESET_OTP_TTL_MINUTES / 60
        )

        from src.redis_client import redis_instance

        await redis_instance.delete(self._reset_otp_attempts_key(user.userId))

        sent = await self.email_service.send_password_reset_otp(
            user.email, code, user.username
        )
        return {"code": code, "sent": sent}

    async def resend_password_reset_otp(self, email: str) -> Optional[dict]:
        """Kirim (ulang) OTP reset password.

        Bila Resend belum diatur & ENV=dev → kembalikan ``devCode`` agar alur
        tetap bisa diuji lokal. Return ``None`` bila email tidak terdaftar.
        """
        result = await self.create_password_reset_otp(email)
        if result is None:
            return None
        if not result["sent"] and self.config.is_env_dev:
            logger.info(f"[DEV] OTP reset password untuk {email}: {result['code']}")
            return {"devCode": result["code"]}
        return {}

    async def reset_password_with_otp(
        self, email: str, code: str, new_password: str
    ) -> tuple[bool, str]:
        """Verifikasi kode OTP reset password lalu ganti password.

        Percobaan kode salah dibatasi (maks. ``RESET_OTP_MAX_ATTEMPTS`` per
        kode); melewati batas membuat kode hangus dan harus minta yang baru.
        """
        from src.redis_client import redis_instance

        user = await self.get_user(email)
        if not user:
            return False, "Kode OTP tidak valid atau kedaluwarsa."

        attempts_key = self._reset_otp_attempts_key(user.userId)
        attempts_raw = await redis_instance.get(attempts_key)
        attempts = int(attempts_raw) if attempts_raw else 0
        if attempts >= self.RESET_OTP_MAX_ATTEMPTS:
            # Kode sudah hangus: buang semua kode reset_otp milik user ini.
            await self.security_service.auth_repo.delete_verification_tokens_by_user(
                user.userId, self.RESET_OTP_TYPE
            )
            return False, "Terlalu banyak percobaan. Silakan minta kode OTP baru."

        code_hash = self.hash_token((code or "").strip())
        token_data = await self.security_service.verify_token(
            code_hash, self.RESET_OTP_TYPE
        )
        if not token_data or token_data.get("userId") != user.userId:
            attempts += 1
            await redis_instance.set(
                attempts_key, str(attempts), ttl=self.RESET_OTP_TTL_MINUTES * 60
            )
            if attempts >= self.RESET_OTP_MAX_ATTEMPTS:
                return False, "Terlalu banyak percobaan. Silakan minta kode OTP baru."
            return False, "Kode OTP tidak valid atau kedaluwarsa."

        try:
            hashed_password = await self.get_password_hash(new_password)
            await self.user_repo.update_one(
                {"userId": user.userId}, {"$set": {"password": hashed_password}}
            )
        except Exception as e:
            logger.exception(f"Error resetting password with OTP: {str(e)}")
            raise AuthOperationError()

        # Pasca-reset: buang kode, cabut semua sesi, & pulihkan lockout login.
        await self.security_service.delete_token(code_hash, self.RESET_OTP_TYPE)
        await redis_instance.delete(attempts_key)
        await self.auth_repo.delete_user_refresh_tokens(user.userId)
        await self.security_service.reset_failed_login_attempts(user.userId)
        await self.security_service.unlock_account(user.userId)
        return True, "Password berhasil direset. Silakan login dengan password baru."
