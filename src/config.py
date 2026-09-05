from typing import List, Optional

from pydantic import SecretStr, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENV: str = "dev"
    SECRET_KEY: SecretStr
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_MAX_AGE_DAYS: int = 30

    DATABASE_URL: SecretStr
    DB_NAME: str = "postgres"
    DB_MAX_POOL_SIZE: int = 10
    DB_POOL_TIMEOUT: int = 30

    # "memory://" = fallback in-process untuk development tanpa server Redis.
    # Produksi wajib redis:// atau rediss:// (mis. Upstash).
    REDIS_URL: SecretStr = SecretStr("memory://")

    IDN_LIVE_PLUS_API_KEY: Optional[SecretStr] = None
    IDN_AUTH_TOKEN: Optional[SecretStr] = None
    IDN_AES_KEY: str = ""
    IDN_ACCESS_TOKEN: Optional[SecretStr] = None
    IDN_SESSION_ID: Optional[str] = None
    IDN_REFRESH_TOKEN: Optional[SecretStr] = None
    COGNITO_CLIENT_ID: Optional[str] = None

    FRONTEND_URL: str = "http://localhost:3000"
    ORIGINS: str = ""
    API_BASE_URL: str = "http://localhost:8000/api"
    COOKIE_DOMAIN: Optional[str] = None

    RESEND_API_KEY: SecretStr = SecretStr("")
    EMAIL_FROM: str = "onboarding@resend.dev"
    EMAIL_VERIFICATION_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_EXPIRE_HOURS: int = 1

    MAX_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_MINUTES: int = 15
    AUTH_REQUESTS_PER_MINUTE: int = 60
    DEFAULT_REQUESTS_PER_MINUTE: int = 120
    LIVE_PROXY_REQUESTS_PER_MINUTE: int = 1500
    LIVE_CACHE_TTL_SECONDS: int = 10
    # Hanya aktifkan bila aplikasi benar-benar berada di belakang reverse proxy
    # terpercaya (mis. Cloudflare) yang selalu menimpa header X-Forwarded-For /
    # CF-Connecting-IP. Jika tidak, klien dapat memalsukan header ini untuk
    # melewati rate-limiting.
    TRUST_PROXY_HEADERS: bool = False

    # --- JKT48Verse additions ---
    # AI Search via provider yang kompatibel OpenAI API (default: OpenRouter)
    LLM_API_KEY: SecretStr = SecretStr("")
    LLM_BASE_URL: str = "https://openrouter.ai/api/v1"
    LLM_MODEL: str = "meta-llama/llama-3.1-8b-instruct"
    LLM_TEMPERATURE: float = 0.3
    LLM_SYSTEM_PROMPT: str = (
        "Kamu asisten komunitas fans JKT48 (JKT48Verse). Jawab hanya seputar JKT48, "
        "48 Group, dan budaya idol. Jika pertanyaan di luar topik, tolak dengan sopan. "
        "Jawab ringkas dalam Bahasa Indonesia. Gunakan konteks database bila relevan."
    )
    # Kuota AI Search per hari (WIB): login / guest
    AI_SEARCH_DAILY_LIMIT_USER: int = 20
    AI_SEARCH_DAILY_LIMIT_GUEST: int = 3

    # Seed akun admin/moderator/demo (dipakai scripts/seed.py)
    ADMIN_USERNAME: str = "admin"
    ADMIN_EMAIL: str = "admin@jkt48verse.local"
    # Default kosong = seed.py memakai password bawaan terdokumentasi + peringatan.
    # Di produksi, selalu set via environment dan ganti setelah deploy.
    ADMIN_PASSWORD: SecretStr = SecretStr("")

    LOG_LEVEL: str = "INFO"
    LOG_DESTINATION: str = "console"
    LOG_PATH: str = "/tmp/mypage48/"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=True
    )

    @model_validator(mode="after")
    def validate_production_hardening(self) -> "Settings":
        if self.ENV == "prod":
            for field in ["FRONTEND_URL", "API_BASE_URL"]:
                val = getattr(self, field)
                if "localhost" in val or "127.0.0.1" in val:
                    raise ValueError(
                        f"{field} cannot contain 'localhost' or '127.0.0.1' in production. Value was: {val}"
                    )
            if len(self.SECRET_KEY.get_secret_value()) < 32:
                raise ValueError("SECRET_KEY must be at least 32 characters long in production")
            if self.redis_url.startswith("memory://"):
                raise ValueError("REDIS_URL cannot be 'memory://' in production — use a real Redis (e.g. Upstash rediss://)")
        return self

    @property
    def is_env_dev(self) -> bool:
        return self.ENV == "dev"

    @computed_field
    @property
    def cors_origins(self) -> List[str]:
        if not self.ORIGINS:
            if self.is_env_dev:
                return [
                    "http://localhost:3000",
                    "http://localhost:5173",
                    "http://127.0.0.1:3000",
                    "http://127.0.0.1:5173",
                ]
            raise ValueError("ORIGINS environment variable is required in production")

        origins = [origin.strip() for origin in self.ORIGINS.split(",") if origin.strip()]
        if not self.is_env_dev:
            for origin in origins:
                if origin == "*":
                    raise ValueError("Wildcard (*) origins are not allowed in production")
                if not origin.startswith("https://"):
                    raise ValueError(f"Only HTTPS origins allowed in production: {origin}")
        return origins

    @property
    def database_url(self) -> str:
        url = self.DATABASE_URL.get_secret_value()
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def redis_url(self) -> str:
        return self.REDIS_URL.get_secret_value()

    @property
    def db_name(self) -> str:
        return self.DB_NAME

    @property
    def oauthlib_insecure_transport(self) -> bool:
        return False

    @computed_field
    @property
    def secret_key(self) -> str:
        return self.SECRET_KEY.get_secret_value()

    @property
    def algorithm(self) -> str:
        allowed_algos = ["HS256", "RS256"]
        algo = self.ALGORITHM or "HS256"
        if algo.lower() == "none" or algo not in allowed_algos:
            raise ValueError(f"Algorithm {algo} is not allowed. Choose from {allowed_algos}")
        return algo

    @property
    def access_token_expire_minutes(self) -> int:
        return self.ACCESS_TOKEN_EXPIRE_MINUTES

    @property
    def refresh_token_max_age_days(self) -> int:
        return self.REFRESH_TOKEN_MAX_AGE_DAYS

    @property
    def admin_username(self) -> str:
        return self.ADMIN_USERNAME

    @property
    def admin_email(self) -> str:
        return self.ADMIN_EMAIL

    @property
    def admin_password(self) -> SecretStr:
        return self.ADMIN_PASSWORD

    @property
    def llm_api_key(self) -> str:
        return self.LLM_API_KEY.get_secret_value()

    @property
    def llm_base_url(self) -> str:
        return self.LLM_BASE_URL

    @property
    def llm_model(self) -> str:
        return self.LLM_MODEL

    @property
    def llm_temperature(self) -> float:
        return self.LLM_TEMPERATURE

    @property
    def llm_system_prompt(self) -> str:
        return self.LLM_SYSTEM_PROMPT

    @property
    def ai_search_daily_limit_user(self) -> int:
        return self.AI_SEARCH_DAILY_LIMIT_USER

    @property
    def ai_search_daily_limit_guest(self) -> int:
        return self.AI_SEARCH_DAILY_LIMIT_GUEST

    @property
    def idn_live_plus_api_key(self) -> Optional[str]:
        return self.IDN_LIVE_PLUS_API_KEY.get_secret_value() if self.IDN_LIVE_PLUS_API_KEY else None

    @property
    def idn_auth_token(self) -> Optional[str]:
        return self.IDN_AUTH_TOKEN.get_secret_value() if self.IDN_AUTH_TOKEN else None

    @property
    def idn_access_token(self) -> Optional[str]:
        return self.IDN_ACCESS_TOKEN.get_secret_value() if self.IDN_ACCESS_TOKEN else None

    @property
    def idn_session_id(self) -> Optional[str]:
        return self.IDN_SESSION_ID

    @property
    def idn_refresh_token(self) -> Optional[str]:
        return self.IDN_REFRESH_TOKEN.get_secret_value() if self.IDN_REFRESH_TOKEN else None

    @property
    def cognito_client_id(self) -> Optional[str]:
        return self.COGNITO_CLIENT_ID

    @property
    def frontend_url(self) -> str:
        return self.FRONTEND_URL

    @property
    def resend_api_key(self) -> str:
        return self.RESEND_API_KEY.get_secret_value()

    @property
    def email_from(self) -> str:
        return self.EMAIL_FROM

    @property
    def email_verification_expire_hours(self) -> int:
        return self.EMAIL_VERIFICATION_EXPIRE_HOURS

    @property
    def password_reset_expire_hours(self) -> int:
        return self.PASSWORD_RESET_EXPIRE_HOURS

    @property
    def max_login_attempts(self) -> int:
        return self.MAX_LOGIN_ATTEMPTS

    @property
    def account_lockout_minutes(self) -> int:
        return self.ACCOUNT_LOCKOUT_MINUTES

    @property
    def auth_requests_per_minute(self) -> int:
        return self.AUTH_REQUESTS_PER_MINUTE

    @property
    def trust_proxy_headers(self) -> bool:
        return self.TRUST_PROXY_HEADERS

    @property
    def default_requests_per_minute(self) -> int:
        return self.DEFAULT_REQUESTS_PER_MINUTE

    @property
    def live_proxy_requests_per_minute(self) -> int:
        return self.LIVE_PROXY_REQUESTS_PER_MINUTE

    @property
    def live_cache_ttl_seconds(self) -> int:
        return self.LIVE_CACHE_TTL_SECONDS

    @property
    def log_level(self) -> str:
        return self.LOG_LEVEL

    @property
    def log_destination(self) -> str:
        return self.LOG_DESTINATION

    @property
    def log_path(self) -> str:
        return self.LOG_PATH

    @property
    def db_max_pool_size(self) -> int:
        return self.DB_MAX_POOL_SIZE

    @property
    def api_base_url(self) -> str:
        return self.API_BASE_URL.rstrip("/")

    @property
    def cookie_domain(self) -> Optional[str]:
        return self.COOKIE_DOMAIN


config = Settings()
