from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.auth.exceptions import (
    AuthOperationError,
    IncorrectCredentialsError,
    InvalidJWTTokenError,
    InvalidRefreshTokenError,
    PasswordPolicyViolationError,
    PasswordResetTokenInvalidError,
    PasswordsDoNotMatchError,
    RefreshTokenExpiredError,
    SuspiciousActivityError,
    VerificationTokenInvalidError,
)
from src.auth.http_exceptions import (
    AccountLocked,
    AuthOperationFailed,
    EmailNotVerified,
    IncorrectEmailOrPassword,
    InvalidJWTToken,
    InvalidRefreshToken,
    PasswordPolicyViolation,
    PasswordResetTokenInvalid,
    PasswordsNotMatch,
    RefreshTokenExpired,
    SuspiciousActivity,
    VerificationTokenInvalid,
)
from src.concerts.exceptions import ConcertCreationError
from src.concerts.exceptions import ConcertDeleteError as DomainConcertDeleteError
from src.concerts.exceptions import ConcertNotFoundError
from src.concerts.exceptions import ConcertUpdateError as DomainConcertUpdateError
from src.concerts.http_exceptions import ConcertCreateError
from src.concerts.http_exceptions import ConcertDeleteError as HttpConcertDeleteError
from src.concerts.http_exceptions import ConcertNotFound
from src.concerts.http_exceptions import ConcertUpdateError as HttpConcertUpdateError
from src.events.exceptions import EventCreationError, EventFetchError, EventNotFoundError
from src.events.http_exceptions import EventCreateError, EventFetchFailed, EventNotFound
from src.exceptions import DomainException, InvalidDateError
from src.http_exceptions import BadRequest, DetailedHTTPException
from src.live.exceptions import (
    CommentsFetchError,
    FetchIdnError,
    FetchShowroomError,
    GiftsFetchError,
    ProxyError,
    StreamingUrlNotFoundError,
)
from src.live.http_exceptions import (
    CommentsFetchFailed,
    GiftsFetchFailed,
    IdnFetchFailed,
    ProxyRequestFailed,
    ShowroomFetchFailed,
    StreamingUrlNotFound,
)
from src.logging_config import create_logger
from src.members.exceptions import MemberFetchError, MemberNotFoundError
from src.members.http_exceptions import MemberFetchError as MemberFetchHTTPException
from src.members.http_exceptions import MemberNotFound
from src.news.exceptions import NewsFetchError, NewsItemFetchError, NewsNotFoundError
from src.news.http_exceptions import NewsFetchHTTPError, NewsItemFetchHTTPError, NewsNotFound
from src.setlists.exceptions import SetlistFetchError, SetlistNotFoundError
from src.setlists.http_exceptions import SetlistFetchError as SetlistFetchHTTPException
from src.setlists.http_exceptions import SetlistNotFound
from src.sorter.exceptions import SorterDeleteError, SorterNotFoundError, SorterSaveError
from src.sorter.http_exceptions import SorterDeleteFailed, SorterNotFound, SorterSaveFailed
from src.users.constants import ErrorCode
from src.users.exceptions import AccountLocked as DomainAccountLocked
from src.users.exceptions import EmailAlreadyExistsError
from src.users.exceptions import EmailNotVerified as DomainEmailNotVerified
from src.users.exceptions import (
    OshiAlreadyExistsError,
    OshiLimitReachedError,
    OshiNotFoundError,
    OshiUpdateError,
    ProfileStatsFetchError,
    ProviderUserCreationError,
    PublicStatusUpdateError,
    PublicUserNotFoundError,
    UserCreationError,
    UserFetchError,
    UsernameAlreadyExistsError,
    UserUpdateError,
)
from src.users.http_exceptions import (
    EmailTaken,
    OshiAlreadyExists,
    OshiLimitReached,
    OshiNotFound,
    OshiUpdateFailed,
    ProfileStatsFetchFailed,
    PublicStatusUpdateFailed,
    PublicUserNotFound,
    ServerError,
    UserFetchFailed,
    UsernameTaken,
    UserUpdateFailed,
)

logger = create_logger("exceptions", __name__)


async def domain_exception_handler(request: Request, exc: DomainException):
    logger.warning(
        f"Domain exception occurred: type={type(exc).__name__}, message={str(exc)}, path={request.url.path}"
    )

    mapping = [
        (UsernameAlreadyExistsError, UsernameTaken),
        (EmailAlreadyExistsError, EmailTaken),
        (IncorrectCredentialsError, IncorrectEmailOrPassword),
        (InvalidJWTTokenError, InvalidJWTToken),
        (InvalidRefreshTokenError, InvalidRefreshToken),
        (RefreshTokenExpiredError, RefreshTokenExpired),
        (SuspiciousActivityError, SuspiciousActivity),
        (VerificationTokenInvalidError, VerificationTokenInvalid),
        (PasswordResetTokenInvalidError, PasswordResetTokenInvalid),
        (PasswordsDoNotMatchError, PasswordsNotMatch),
        (PasswordPolicyViolationError, PasswordPolicyViolation),
        (AuthOperationError, AuthOperationFailed),
        (DomainAccountLocked, AccountLocked),
        (DomainEmailNotVerified, EmailNotVerified),
        (PublicUserNotFoundError, PublicUserNotFound),
        (UserUpdateError, UserUpdateFailed),
        (UserFetchError, UserFetchFailed),
        (OshiUpdateError, OshiUpdateFailed),
        (OshiLimitReachedError, OshiLimitReached),
        (OshiAlreadyExistsError, OshiAlreadyExists),
        (OshiNotFoundError, OshiNotFound),
        (PublicStatusUpdateError, PublicStatusUpdateFailed),
        (ProfileStatsFetchError, ProfileStatsFetchFailed),
        (SetlistNotFoundError, SetlistNotFound),
        (SetlistFetchError, SetlistFetchHTTPException),
        (MemberNotFoundError, MemberNotFound),
        (MemberFetchError, MemberFetchHTTPException),
        (EventNotFoundError, EventNotFound),
        (EventCreationError, EventCreateError),
        (EventFetchError, EventFetchFailed),
        (NewsNotFoundError, NewsNotFound),
        (NewsFetchError, NewsFetchHTTPError),
        (NewsItemFetchError, NewsItemFetchHTTPError),
        (SorterNotFoundError, SorterNotFound),
        (SorterSaveError, SorterSaveFailed),
        (SorterDeleteError, SorterDeleteFailed),
        (FetchShowroomError, ShowroomFetchFailed),
        (FetchIdnError, IdnFetchFailed),
        (StreamingUrlNotFoundError, StreamingUrlNotFound),
        (ProxyError, ProxyRequestFailed),
        (CommentsFetchError, CommentsFetchFailed),
        (GiftsFetchError, GiftsFetchFailed),
        (ConcertNotFoundError, ConcertNotFound),
        (ConcertCreationError, ConcertCreateError),
        (DomainConcertUpdateError, HttpConcertUpdateError),
        (DomainConcertDeleteError, HttpConcertDeleteError),
        (InvalidDateError, BadRequest),
    ]

    if isinstance(exc, (UserCreationError, ProviderUserCreationError)):
        logger.error(f"Critical domain error: {str(exc)}")
        return await detailed_http_exception_handler(request, ServerError())

    for domain_exc, http_exc in mapping:
        if isinstance(exc, domain_exc):
            return await detailed_http_exception_handler(request, http_exc())

    logger.error(f"Unhandled domain/unexpected exception: {type(exc).__name__}: {str(exc)}")
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


async def detailed_http_exception_handler(request: Request, exc: DetailedHTTPException):
    return JSONResponse(
        status_code=exc.STATUS_CODE,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    errors = exc.errors()
    if errors:
        first_error = errors[0]
        msg = first_error.get("msg", "Invalid request")
        clean_msg = msg
        if msg.startswith("Value error, "):
            clean_msg = msg.replace("Value error, ", "")
        if clean_msg in (ErrorCode.PASSWORD_MISMATCH, ErrorCode.PASSWORD_RULES):
            return JSONResponse(status_code=400, content={"detail": clean_msg})
    return JSONResponse(
        status_code=422,
        content={"detail": jsonable_encoder(exc.errors())},
    )
