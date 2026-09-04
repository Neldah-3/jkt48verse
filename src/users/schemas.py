from datetime import datetime
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from src.auth.schemas import OshiResponse
from src.users.constants import ErrorCode, Info
from src.utils import cleanse_image_url, validate_password_strength


class UserCreateRequest(BaseModel):
    fullName: str = Field(max_length=100)
    username: str = Field(max_length=50)
    email: EmailStr
    password: str
    confirmPassword: str

    @model_validator(mode="after")
    def verify_password_match(self):
        if self.password != self.confirmPassword:
            raise ValueError(ErrorCode.PASSWORD_MISMATCH)
        if not validate_password_strength(self.password):
            raise ValueError(ErrorCode.PASSWORD_RULES)
        return self


class ProviderUserCreateRequest(BaseModel):
    profilePicture: Optional[str] = Field(default=None)
    name: str = Field(max_length=100)
    username: str = Field(max_length=50)
    email: EmailStr
    provider: str

    @field_validator("profilePicture")
    @classmethod
    def validate_profile_picture(cls, v: Optional[str]) -> Optional[str]:
        return cleanse_image_url(v)


class UserInDB(BaseModel):
    userId: str = Field(default_factory=lambda: str(uuid4()))
    profilePicture: Optional[str] = Field(default=None)
    name: str = Field(max_length=100)
    memberId: Optional[str] = Field(max_length=20, default=None)
    oshiIds: list[str] = Field(default_factory=list)
    username: str = Field(max_length=50)
    email: EmailStr
    ofcStatus: str = Field(default="Active")
    bio: Optional[str] = Field(default=None, max_length=300)
    password: Optional[str] = Field(default=None)
    provider: Optional[str] = Field(default=None)
    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(default_factory=datetime.now)
    isEmailVerified: bool = Field(default=False)
    isPublic: bool = Field(default=False)
    publicYear: Optional[int] = Field(default=None)
    failedLoginAttempts: int = Field(default=0)
    isAccountLocked: bool = Field(default=False)
    accountLockedUntil: Optional[datetime] = Field(default=None)
    lastActiveAt: Optional[datetime] = Field(default=None)
    isAdmin: bool = Field(default=False)


class UserCreateResponse(BaseModel):
    detail: str


class UserCreatedWithEmail(UserCreateResponse):
    detail: str = Info.USER_CREATED_WITH_EMAIL


class UserCreated(UserCreateResponse):
    detail: str = Info.USER_CREATED


class PublicUserResponse(BaseModel):
    name: str
    username: str
    bio: Optional[str] = None
    profilePicture: Optional[str] = None
    oshis: list[OshiResponse] = []
    createdAt: datetime
    lastActiveAt: Optional[datetime] = None
    publicYear: Optional[int] = None


class BatchAddOshiRequest(BaseModel):
    oshiIds: list[str]

    @field_validator("oshiIds", mode="before")
    @classmethod
    def allow_int_oshi_ids(cls, v):
        if v is None:
            return None
        return [str(x) for x in v]


class RemoveOshiRequest(BaseModel):
    oshiId: str

    @field_validator("oshiId", mode="before")
    @classmethod
    def allow_int_oshi_id(cls, v):
        if v is None:
            return None
        return str(v)


class UpdatePublicStatusRequest(BaseModel):
    isPublic: bool
    publicYear: Optional[int] = None


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    username: Optional[str] = Field(None, max_length=50)
    email: Optional[EmailStr] = None
    bio: Optional[str] = Field(None, max_length=300)


class MessageResponse(BaseModel):
    detail: str


class ProfileFullResponse(BaseModel):
    profile: dict
    oshis: list[OshiResponse] = []


class UserListItem(BaseModel):
    userId: str
    name: str
    username: str
    profilePicture: Optional[str] = None
    isAdmin: bool = False
    isEmailVerified: bool = False
    isAccountLocked: bool = False
    createdAt: datetime
    lastActiveAt: Optional[datetime] = None


class UserPaginationMeta(BaseModel):
    current_page: int
    last_page: int
    total_data: int
    per_page: int
    next_page: Optional[int] = None


class UserListResponse(BaseModel):
    data: list[UserListItem]
    meta: UserPaginationMeta
