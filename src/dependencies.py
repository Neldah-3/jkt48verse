import typing

from fastapi import BackgroundTasks, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi_sso.sso.github import GithubSSO
from fastapi_sso.sso.google import GoogleSSO
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.csrf_service import CSRFService
from src.auth.email_service import EmailService
from src.auth.http_exceptions import InvalidCSRFToken, InvalidJWTToken
from src.auth.repository import AuthRepository
from src.auth.schemas import UserCurrent
from src.auth.security_service import SecurityService
from src.auth.service import AuthService
from src.concerts.repository import ConcertsRepository
from src.concerts.service import ConcertsService
from src.config import Settings, config
from src.database import database_instance, get_session
from src.events.repository import EventsRepository
from src.events.service import EventsService
from src.health.service import HealthService
from src.http_exceptions import AdminRequired
from src.infrastructure import AsyncBackgroundRunner
from src.live.service import LiveService
from src.logging_config import create_logger
from src.members.repository import MemberRepository
from src.members.service import MemberService
from src.news.repository import NewsRepository
from src.news.service import NewsService
from src.redis_client import redis_instance
from src.setlists.repository import SetlistsRepository
from src.setlists.service import SetlistsService
from src.sorter.repository import SortersRepository
from src.sorter.service import SortersService
from src.users.repository import UserRepository
from src.users.service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/signin")
logger = create_logger("dependencies", __name__)


def get_settings() -> Settings:
    return config


def get_email_service(settings: Settings = Depends(get_settings)) -> EmailService:
    background_runner = AsyncBackgroundRunner()
    return EmailService(settings, background_runner)


def get_user_repository(session: AsyncSession = Depends(get_session)) -> UserRepository:
    return UserRepository(session)


def get_auth_repository(session: AsyncSession = Depends(get_session)) -> AuthRepository:
    return AuthRepository(session)


def get_security_service(
    auth_repo: AuthRepository = Depends(get_auth_repository),
    user_repo: UserRepository = Depends(get_user_repository),
    email_service: EmailService = Depends(get_email_service),
    settings: Settings = Depends(get_settings),
) -> SecurityService:
    background_runner = AsyncBackgroundRunner()
    return SecurityService(auth_repo, user_repo, email_service, background_runner, settings)


def get_auth_service(
    auth_repo: AuthRepository = Depends(get_auth_repository),
    user_repo: UserRepository = Depends(get_user_repository),
    security_service: SecurityService = Depends(get_security_service),
    email_service: EmailService = Depends(get_email_service),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    return AuthService(auth_repo, user_repo, security_service, email_service, settings)


async def get_current_user(
    background_tasks: BackgroundTasks,
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service),
    user_repo: UserRepository = Depends(get_user_repository),
):
    token_data = auth_service.verify_access_token(token)
    user = await auth_service.get_user(username_or_email=token_data.username)
    if user is None:
        logger.warning("User not found for provided token")
        raise InvalidJWTToken()
    if background_tasks:
        background_tasks.add_task(user_repo.update_last_active, user.userId)
    return UserCurrent(**user.model_dump())


async def get_current_user_optional(
    background_tasks: BackgroundTasks,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    user_repo: UserRepository = Depends(get_user_repository),
) -> typing.Optional[UserCurrent]:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]
    try:
        token_data = auth_service.verify_access_token(token)
        user = await auth_service.get_user(username_or_email=token_data.username)
        if user is None:
            raise InvalidJWTToken()
        if background_tasks:
            background_tasks.add_task(user_repo.update_last_active, user.userId)
        return UserCurrent(**user.model_dump())
    except Exception as e:
        logger.warning(f"Optional auth failed: {e}")
        raise InvalidJWTToken()


def require_csrf_protection(request: Request, settings: Settings = Depends(get_settings)):
    if request.method == "OPTIONS":
        return True

    if settings.is_env_dev:
        referer = request.headers.get("referer", "")
        sec_fetch_site = request.headers.get("sec-fetch-site", "")
        if (
            referer.startswith("http://localhost:8000/docs")
            or referer.startswith("http://localhost:8000/redoc")
        ) and sec_fetch_site == "same-origin":
            return True
        user_agent = request.headers.get("user-agent", "").lower()
        if "postman" in user_agent:
            return True

    header_token = request.headers.get(CSRFService.CSRF_TOKEN_HEADER)
    cookie_token = request.cookies.get(CSRFService.CSRF_TOKEN_COOKIE)
    if not CSRFService.validate_csrf_token_string(header_token, cookie_token):
        raise InvalidCSRFToken()
    return True


def get_google_sso(settings: Settings = Depends(get_settings)) -> GoogleSSO:
    return GoogleSSO(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=settings.google_redirect_uri,
        allow_insecure_http=settings.is_env_dev,
    )


def get_github_sso(settings: Settings = Depends(get_settings)) -> GithubSSO:
    return GithubSSO(
        client_id=settings.github_client_id,
        client_secret=settings.github_client_secret,
        redirect_uri=settings.github_redirect_uri,
        allow_insecure_http=settings.is_env_dev,
    )


async def require_admin(
    background_tasks: BackgroundTasks,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    user_repo: UserRepository = Depends(get_user_repository),
) -> UserCurrent:
    current_user = None
    try:
        current_user = await get_current_user_optional(
            background_tasks=background_tasks,
            request=request,
            auth_service=auth_service,
            user_repo=user_repo,
        )
    except Exception:
        pass
    if not current_user or not current_user.isAdmin:
        raise AdminRequired()
    return current_user


def get_member_repository(session: AsyncSession = Depends(get_session)) -> MemberRepository:
    return MemberRepository(session)


def get_member_service(
    repo: MemberRepository = Depends(get_member_repository),
    settings: Settings = Depends(get_settings),
) -> MemberService:
    return MemberService(repo, settings)


def get_events_repository(session: AsyncSession = Depends(get_session)) -> EventsRepository:
    return EventsRepository(session)


def get_events_service(
    repo: EventsRepository = Depends(get_events_repository),
    settings: Settings = Depends(get_settings),
    member_service: MemberService = Depends(get_member_service),
) -> EventsService:
    return EventsService(repo, settings, member_service)


def get_user_service(
    repo: UserRepository = Depends(get_user_repository),
    security_service: SecurityService = Depends(get_security_service),
    email_service: EmailService = Depends(get_email_service),
    settings: Settings = Depends(get_settings),
    member_service: MemberService = Depends(get_member_service),
    events_service: EventsService = Depends(get_events_service),
) -> UserService:
    return UserService(
        repo, security_service, email_service, settings, member_service, events_service
    )


def get_setlists_repository(
    session: AsyncSession = Depends(get_session),
) -> SetlistsRepository:
    return SetlistsRepository(session)


def get_setlists_service(
    repo: SetlistsRepository = Depends(get_setlists_repository),
    settings: Settings = Depends(get_settings),
) -> SetlistsService:
    return SetlistsService(repo, settings)


def get_health_service() -> HealthService:
    return HealthService(database_instance, redis_instance)


def get_news_repository(session: AsyncSession = Depends(get_session)) -> NewsRepository:
    return NewsRepository(session)


def get_news_service(
    repo: NewsRepository = Depends(get_news_repository),
    settings: Settings = Depends(get_settings),
) -> NewsService:
    return NewsService(repo, settings)


def get_live_service(
    member_repo: MemberRepository = Depends(get_member_repository),
    settings: Settings = Depends(get_settings),
) -> LiveService:
    return LiveService(member_repo, settings)


def get_sorters_repository(
    session: AsyncSession = Depends(get_session),
) -> SortersRepository:
    return SortersRepository(session)


def get_sorters_service(
    repo: SortersRepository = Depends(get_sorters_repository),
    settings: Settings = Depends(get_settings),
) -> SortersService:
    return SortersService(repo, settings)


def get_concerts_repository(
    session: AsyncSession = Depends(get_session),
) -> ConcertsRepository:
    return ConcertsRepository(session)


def get_concerts_service(
    repo: ConcertsRepository = Depends(get_concerts_repository),
    settings: Settings = Depends(get_settings),
) -> ConcertsService:
    return ConcertsService(repo, settings)
