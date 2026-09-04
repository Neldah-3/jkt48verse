from typing import Optional

from fastapi import APIRouter, Depends, Query, Request

from src.auth.schemas import UserCurrent
from src.dependencies import (
    get_current_user,
    get_user_service,
    require_admin,
    require_csrf_protection,
)
from src.limiter import limiter
from src.logging_config import create_logger
from src.users.schemas import (
    BatchAddOshiRequest,
    MessageResponse,
    ProfileFullResponse,
    PublicUserResponse,
    RemoveOshiRequest,
    UpdateProfileRequest,
    UpdatePublicStatusRequest,
    UserCreatedWithEmail,
    UserCreateRequest,
    UserCreateResponse,
    UserListResponse,
)
from src.users.service import UserService

logger = create_logger("users", __name__)

router = APIRouter()


@router.get("/users", response_model=UserListResponse)
async def get_all_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    _: UserCurrent = Depends(require_admin),
    service: UserService = Depends(get_user_service),
):
    return await service.get_all_users(page, limit, search)


@router.post("/users/signup", status_code=201, response_model=UserCreateResponse)
@limiter.limit("5/day", override_defaults=True)
async def signup(
    request: Request,
    user: UserCreateRequest,
    user_service: UserService = Depends(get_user_service),
):
    result = await user_service.create_user(user)
    if isinstance(result, UserCreatedWithEmail):
        logger.info("User created successfully and verification email sent")
    else:
        logger.info("User created successfully")
    return result


@router.get("/users/profile", response_model=ProfileFullResponse)
async def user_profile(
    current_user: UserCurrent = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    return await user_service.get_profile_full(current_user)


@router.post("/users/oshi/batch-add", status_code=200, response_model=MessageResponse)
async def batch_add_oshi(
    request: BatchAddOshiRequest,
    current_user: UserCurrent = Depends(get_current_user),
    _=Depends(require_csrf_protection),
    user_service: UserService = Depends(get_user_service),
):
    return await user_service.batch_add_oshi(current_user.userId, request.oshiIds)


@router.post("/users/oshi/remove", status_code=200, response_model=MessageResponse)
async def remove_oshi(
    request: RemoveOshiRequest,
    current_user: UserCurrent = Depends(get_current_user),
    _=Depends(require_csrf_protection),
    user_service: UserService = Depends(get_user_service),
):
    return await user_service.remove_oshi(current_user.userId, request.oshiId)


@router.post("/users/public-status", status_code=200, response_model=MessageResponse)
async def update_public_status(
    request: UpdatePublicStatusRequest,
    current_user: UserCurrent = Depends(get_current_user),
    _=Depends(require_csrf_protection),
    user_service: UserService = Depends(get_user_service),
):
    return await user_service.update_public_status(
        current_user.userId, request.isPublic, request.publicYear
    )


@router.patch("/users/profile", status_code=200, response_model=MessageResponse)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: UserCurrent = Depends(get_current_user),
    _=Depends(require_csrf_protection),
    user_service: UserService = Depends(get_user_service),
):
    return await user_service.update_profile(current_user.userId, request)


@router.get("/u/{username}", response_model=PublicUserResponse)
async def get_public_profile(
    username: str,
    user_service: UserService = Depends(get_user_service),
):
    return await user_service.get_public_profile(username)
