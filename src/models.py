import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class UserOshi(Base):
    __tablename__ = "user_oshis"

    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True
    )
    member_id: Mapped[str] = mapped_column(String(64), primary_key=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    profile_picture: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    name: Mapped[str] = mapped_column(String(100))
    member_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    ofc_status: Mapped[str] = mapped_column(String(32), default="Active")
    bio: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    provider: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    public_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    is_account_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    account_locked_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_active_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    oshis: Mapped[list["UserOshi"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "userId": self.user_id,
            "profilePicture": self.profile_picture,
            "name": self.name,
            "memberId": self.member_id,
            "username": self.username,
            "email": self.email,
            "ofcStatus": self.ofc_status,
            "bio": self.bio,
            "password": self.password,
            "provider": self.provider,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "isEmailVerified": self.is_email_verified,
            "isPublic": self.is_public,
            "publicYear": self.public_year,
            "failedLoginAttempts": self.failed_login_attempts,
            "isAccountLocked": self.is_account_locked,
            "accountLockedUntil": self.account_locked_until,
            "lastActiveAt": self.last_active_at,
            "isAdmin": self.is_admin,
            "oshiIds": [o.member_id for o in self.oshis],
        }


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    hash_refresh_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    device: Mapped[str] = mapped_column(String(255), default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
    browser: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "userId": self.user_id,
            "hashRefreshToken": self.hash_refresh_token,
            "device": self.device,
            "ip": self.ip,
            "browser": self.browser,
            "createdAt": self.created_at,
            "lastUsedAt": self.last_used_at,
        }


class LoginHistory(Base):
    __tablename__ = "login_history"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    device: Mapped[str] = mapped_column(String(255), default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
    browser: Mapped[str] = mapped_column(String(255), default="")
    login_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    user_agent_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "userId": self.user_id,
            "device": self.device,
            "ip": self.ip,
            "browser": self.browser,
            "loginAt": self.login_at,
            "userAgentRaw": self.user_agent_raw,
        }


class VerificationToken(Base):
    __tablename__ = "verification_tokens"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    hash_token: Mapped[str] = mapped_column(String(64), index=True)
    token_type: Mapped[str] = mapped_column(String(32))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (Index("ix_verification_hash_type", "hash_token", "token_type"),)

    def to_dict(self) -> dict[str, Any]:
        return {
            "userId": self.user_id,
            "hashToken": self.hash_token,
            "tokenType": self.token_type,
            "expiresAt": self.expires_at,
            "createdAt": self.created_at,
        }


class Member(Base):
    __tablename__ = "members"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    nickname: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    generation: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    jiko: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    href: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    img: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    birthdate: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    blood_type: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    horoscope: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    height: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    socials: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    member_type: Mapped[Optional[str]] = mapped_column(String(50), default="JKT48")
    member_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "nickname": self.nickname,
            "generation": self.generation,
            "jiko": self.jiko,
            "active": self.active,
            "href": self.href,
            "img": self.img,
            "birthdate": self.birthdate,
            "bloodType": self.blood_type,
            "horoscope": self.horoscope,
            "height": self.height,
            "socials": self.socials or {},
            "member_type": self.member_type,
            "member_code": self.member_code,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }


class Setlist(Base):
    __tablename__ = "setlists"

    setlist_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    title_japanese: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    description: Mapped[str] = mapped_column(Text, default="")
    type: Mapped[str] = mapped_column(String(32), default="setlist")
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    songs: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "setlistId": self.setlist_id,
            "imageUrl": self.image_url or "",
            "title": self.title,
            "titleJapanese": self.title_japanese,
            "description": self.description,
            "type": self.type,
            "active": self.active,
            "songs": self.songs or [],
        }


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    url: Mapped[str] = mapped_column(Text, default="")
    label: Mapped[str] = mapped_column(String(100), default="")
    type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    setlist_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    members: Mapped[list["EventMember"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )

    def member_ids(self, role: str = "member") -> list[str]:
        return [m.member_id for m in self.members if m.role == role]


class EventMember(Base):
    __tablename__ = "event_members"

    event_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("events.id", ondelete="CASCADE"), primary_key=True
    )
    member_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    role: Mapped[str] = mapped_column(String(32), primary_key=True, default="member")

    __table_args__ = (Index("ix_event_members_member_id", "member_id"),)


class News(Base):
    __tablename__ = "news"

    news_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    title: Mapped[str] = mapped_column(String(500))
    category: Mapped[str] = mapped_column(String(100), default="")
    link: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    background_image: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    valid_date_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    content_body: Mapped[str] = mapped_column(Text, default="")
    short_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "news_id": self.news_id,
            "title": self.title,
            "category": self.category,
            "link": self.link,
            "background_image": self.background_image,
            "is_published": self.is_published,
            "valid_date_from": self.valid_date_from,
            "content_body": self.content_body,
            "short_description": self.short_description,
        }


class Concert(Base):
    __tablename__ = "concerts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(255))
    theme: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    type: Mapped[str] = mapped_column(String(64), default="Anniversary")
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    location: Mapped[str] = mapped_column(String(255), default="")
    details: Mapped[str] = mapped_column(Text, default="")
    benefits: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    ticket_price: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    image: Mapped[str] = mapped_column(Text, default="")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "theme": self.theme,
            "type": self.type,
            "date": self.date,
            "location": self.location,
            "details": self.details,
            "benefits": self.benefits or [],
            "ticket_price": self.ticket_price or [],
            "image": self.image,
        }


class Sorter(Base):
    __tablename__ = "sorter_results"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    filters: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    results: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "_id": self.id,
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "filters": self.filters or [],
            "results": self.results or [],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


