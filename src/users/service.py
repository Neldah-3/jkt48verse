import asyncio
import math
import time
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.exc import IntegrityError

from src.auth.email_service import EmailService
from src.auth.schemas import OshiResponse, OshiShowResponse
from src.auth.security_service import SecurityService
from src.config import Settings
from src.events.service import EventsService
from src.logging_config import create_logger
from src.members.service import MemberService
from src.users.constants import Info
from src.users.exceptions import (
    EmailAlreadyExistsError,
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
from src.users.repository import UserRepository
from src.users.schemas import (
    MessageResponse,
    ProfileFullResponse,
    ProviderUserCreateRequest,
    PublicUserResponse,
    UpdateProfileRequest,
    UserCreated,
    UserCreatedWithEmail,
    UserCreateRequest,
    UserInDB,
    UserListItem,
    UserListResponse,
    UserPaginationMeta,
)

logger = create_logger("users_service", __name__)


class UserService:
    def __init__(
        self,
        repository: UserRepository,
        security_service: SecurityService,
        email_service: EmailService,
        config: Settings,
        member_service: MemberService,
        events_service: EventsService,
    ):
        self.repository = repository
        self.security_service = security_service
        self.email_service = email_service
        self.config = config
        self.member_service = member_service
        self.events_service = events_service

    def _handle_duplicate_key_error(self, error: IntegrityError):
        message = str(error).lower()
        if "username" in message:
            raise UsernameAlreadyExistsError()
        if "email" in message:
            raise EmailAlreadyExistsError()
        raise UsernameAlreadyExistsError()

    async def _generate_unique_member_id(self) -> str:
        return f"MYP48-{int(time.time() * 1000)}"

    async def create_user(self, request: UserCreateRequest) -> UserCreated:
        try:
            hashed_password = await asyncio.to_thread(
                self.security_service.get_password_hash, request.password
            )
            member_id = await self._generate_unique_member_id()
            user_in_db = UserInDB(
                name=request.fullName,
                memberId=member_id,
                username=request.username.lower(),
                email=request.email.lower(),
                ofcStatus="Active",
                password=hashed_password,
                isEmailVerified=False,
                failedLoginAttempts=0,
                isAccountLocked=False,
                accountLockedUntil=None,
            )
            await self.repository.insert_user(user_in_db.model_dump())
            try:
                token = await self.security_service.create_and_save_token(
                    user_in_db.userId,
                    "email_verification",
                    self.config.email_verification_expire_hours,
                )
                await self.email_service.send_email_verification(
                    user_in_db.email, token, user_in_db.username
                )
                return UserCreatedWithEmail()
            except Exception as e:
                logger.warning(f"User created but error sending verification email: {e}")
                return UserCreated()
        except IntegrityError as dk:
            self._handle_duplicate_key_error(dk)
        except (UsernameAlreadyExistsError, EmailAlreadyExistsError):
            raise
        except Exception as e:
            logger.exception(f"Unexpected error in create_user: {str(e)}")
            raise UserCreationError()

    async def create_user_provider(self, request: ProviderUserCreateRequest) -> UserCreated:
        try:
            user_in_db = UserInDB(
                profilePicture=request.profilePicture,
                name=request.name,
                username=request.username.lower(),
                email=request.email.lower(),
                password=None,
                provider=request.provider,
                isEmailVerified=True,
                failedLoginAttempts=0,
                isAccountLocked=False,
                accountLockedUntil=None,
            )
            await self.repository.insert_user(user_in_db.model_dump())
            return UserCreated()
        except IntegrityError as dk:
            self._handle_duplicate_key_error(dk)
        except (UsernameAlreadyExistsError, EmailAlreadyExistsError):
            raise
        except Exception as e:
            logger.exception(f"Unexpected error in create_user_provider: {str(e)}")
            raise ProviderUserCreationError()

    async def batch_add_oshi(self, user_id: str, new_oshi_ids: list[str]) -> MessageResponse:
        try:
            user_data = await self.repository.get_user_by_id(user_id)
            if not user_data:
                raise UserFetchError()
            current_ids = user_data.get("oshiIds") or []
            if len(current_ids) + len(new_oshi_ids) > 5:
                raise OshiLimitReachedError()
            already_exists = [oid for oid in new_oshi_ids if oid in current_ids]
            if already_exists:
                raise OshiAlreadyExistsError()
            for oshi_id in new_oshi_ids:
                await self.repository.add_oshi_id(user_id, oshi_id)
            return MessageResponse(detail=Info.OSHI_ADDED)
        except (OshiLimitReachedError, OshiAlreadyExistsError):
            raise
        except Exception as e:
            logger.exception(f"Error batch adding oshis: {str(e)}")
            raise OshiUpdateError()

    async def remove_oshi(self, user_id: str, oshi_id: str) -> MessageResponse:
        try:
            user_data = await self.repository.get_user_by_id(user_id)
            if not user_data:
                raise UserFetchError()
            oshi_ids = user_data.get("oshiIds") or []
            if oshi_id not in oshi_ids:
                raise OshiNotFoundError()
            await self.repository.remove_oshi_id(user_id, oshi_id)
            return MessageResponse(detail=Info.OSHI_REMOVED)
        except OshiNotFoundError:
            raise
        except Exception as e:
            logger.exception(f"Error removing oshi: {str(e)}")
            raise OshiUpdateError()

    async def update_public_status(
        self, user_id: str, is_public: bool, public_year: int | None = None
    ) -> MessageResponse:
        try:
            await self.repository.set_public_status(user_id, is_public, public_year)
            return MessageResponse(detail=Info.PUBLIC_STATUS_UPDATED)
        except Exception as e:
            logger.exception(f"Error updating public status: {str(e)}")
            raise PublicStatusUpdateError()

    async def get_public_user_by_username(self, username: str) -> UserInDB | None:
        try:
            user_data = await self.repository.find_one({"username": username.lower()})
            if not user_data:
                return None
            user = UserInDB(**user_data)
            if not user.isPublic:
                return None
            return user
        except Exception as e:
            logger.exception(f"Error fetching public user: {str(e)}")
            raise UserFetchError()

    async def update_profile(
        self, user_id: str, request: UpdateProfileRequest
    ) -> MessageResponse:
        try:
            user_data = await self.repository.get_user_by_id(user_id)
            if not user_data:
                raise UserFetchError()
            current_user = UserInDB(**user_data)
            update_data = {"updatedAt": datetime.now(timezone.utc)}
            if request.name is not None:
                update_data["name"] = request.name
            if request.username is not None:
                new_username = request.username.lower()
                if new_username != current_user.username:
                    update_data["username"] = new_username
            email_changed = False
            if request.email is not None:
                new_email = request.email.lower()
                if new_email != current_user.email:
                    update_data["email"] = new_email
                    update_data["isEmailVerified"] = False
                    email_changed = True
            if request.bio is not None:
                update_data["bio"] = request.bio
            if len(update_data) > 1:
                try:
                    await self.repository.update_one({"userId": user_id}, {"$set": update_data})
                except IntegrityError as dk:
                    self._handle_duplicate_key_error(dk)
            if email_changed:
                try:
                    token = await self.security_service.create_and_save_token(
                        user_id,
                        "email_verification",
                        self.config.email_verification_expire_hours,
                    )
                    await self.email_service.send_email_verification(
                        update_data["email"],
                        token,
                        update_data.get("username", current_user.username),
                    )
                except Exception as e:
                    logger.warning(f"Profile updated but error sending verification email: {e}")
            return MessageResponse(detail=Info.PROFILE_UPDATED)
        except (UsernameAlreadyExistsError, EmailAlreadyExistsError):
            raise
        except Exception as e:
            logger.exception(f"Error updating profile: {str(e)}")
            raise UserUpdateError()

    async def _build_oshi_response(self, oshi_id: str) -> Optional[OshiResponse]:
        try:
            member_detail = await self.member_service.get_member_by_id(str(oshi_id))
            member = member_detail.member
            oshi = OshiResponse(
                id=str(oshi_id),
                name=member.name,
                nickname=member.nickname,
                generation=member.generation or "-",
                memberType=member.member_type,
                profilePicture=member.img,
                catchphrase=member.jiko or "-",
                socials=member.socials.model_dump() if member.socials else None,
            )
            oshi_events = await self.events_service.get_events_for_member(str(oshi_id))
            oshi.totalShows = len(oshi_events)
            now = datetime.now(timezone.utc)
            upcoming, past = [], []
            for e in oshi_events:
                event_date = e.get("date")
                if not isinstance(event_date, datetime):
                    try:
                        event_date = datetime.fromisoformat(str(event_date))
                    except Exception:
                        continue
                show = OshiShowResponse(
                    title=e.get("title", "Unknown"), date=event_date, url=e.get("url")
                )
                if event_date >= now:
                    upcoming.append(show)
                else:
                    past.append(show)
            oshi.upcomingSchedule = sorted(upcoming, key=lambda x: x.date)
            oshi.pastSchedule = sorted(past, key=lambda x: x.date, reverse=True)[:5]
            return oshi
        except Exception as e:
            logger.warning(f"Failed to fetch oshi data for id {oshi_id}: {e}")
            return None

    async def get_public_profile(self, username: str) -> PublicUserResponse:
        user = await self.get_public_user_by_username(username)
        if not user:
            raise PublicUserNotFoundError()
        oshis = []
        for oshi_id in user.oshiIds or []:
            oshi = await self._build_oshi_response(oshi_id)
            if oshi:
                oshis.append(oshi)
        return PublicUserResponse(
            name=user.name,
            username=user.username,
            bio=user.bio,
            profilePicture=user.profilePicture,
            oshis=oshis,
            createdAt=user.createdAt,
            lastActiveAt=user.lastActiveAt if hasattr(user, "lastActiveAt") else None,
            publicYear=user.publicYear,
        )

    async def get_profile_full(self, current_user) -> ProfileFullResponse:
        try:
            oshi_ids = list(current_user.oshiIds) if current_user.oshiIds else []
            oshi_responses = []
            for oshi_id in oshi_ids:
                oshi = await self._build_oshi_response(oshi_id)
                if oshi:
                    oshi_responses.append(oshi)
            profile_dict = {
                "userId": current_user.userId,
                "profilePicture": current_user.profilePicture,
                "name": current_user.name,
                "email": current_user.email,
                "username": current_user.username,
                "bio": current_user.bio,
                "memberId": current_user.memberId,
                "ofcStatus": current_user.ofcStatus,
                "isPublic": current_user.isPublic,
                "publicYear": current_user.publicYear,
                "isAdmin": current_user.isAdmin,
                "isEmailVerified": current_user.isEmailVerified,
                "createdAt": current_user.createdAt,
                "oshiIds": oshi_ids,
            }
            if current_user.isAdmin is False:
                profile_dict.pop("isAdmin", None)
            return ProfileFullResponse(profile=profile_dict, oshis=oshi_responses)
        except Exception as e:
            logger.exception(f"Error fetching profile: {str(e)}")
            raise ProfileStatsFetchError()

    async def get_all_users(
        self, page: int, limit: int, search: str | None = None
    ) -> UserListResponse:
        try:
            users = await self.repository.get_all_paginated(page, limit, search)
            total = await self.repository.count_all(search)
            user_list = []
            for u in users:
                last_active = u.get("lastActiveAt")
                if last_active and last_active.tzinfo is None:
                    last_active = last_active.replace(tzinfo=timezone.utc)
                created_at = u.get("createdAt")
                if created_at and created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                user_list.append(
                    UserListItem(
                        userId=u.get("userId", ""),
                        name=u.get("name", ""),
                        username=u.get("username", ""),
                        profilePicture=u.get("profilePicture"),
                        isAdmin=u.get("isAdmin", False),
                        isEmailVerified=u.get("isEmailVerified", False),
                        isAccountLocked=u.get("isAccountLocked", False),
                        createdAt=created_at,
                        lastActiveAt=last_active,
                    )
                )
            last_page = math.ceil(total / limit) if total > 0 else 1
            next_page = page + 1 if page < last_page else None
            return UserListResponse(
                data=user_list,
                meta=UserPaginationMeta(
                    current_page=page,
                    last_page=last_page,
                    total_data=total,
                    per_page=limit,
                    next_page=next_page,
                ),
            )
        except Exception as e:
            logger.exception(f"Error fetching users list: {str(e)}")
            raise UserFetchError()
