import uuid
from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# =====================================================================
# AUTH & USERS
# =====================================================================
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # id numerik publik (dipakai fitur komunitas JKT48Verse: chat, game, dsb.)
    seq: Mapped[int] = mapped_column(
        BigInteger, Identity(), unique=True, nullable=False
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=utcnow
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

    # --- JKT48Verse community fields ---
    role: Mapped[str] = mapped_column(String(16), default="MEMBER")  # MEMBER | MODERATOR | ADMIN
    avatar_seed: Mapped[int] = mapped_column(Integer, default=1)
    theme: Mapped[str] = mapped_column(String(8), default="system")
    lang: Mapped[str] = mapped_column(String(2), default="id")
    multi_live_layout: Mapped[str] = mapped_column(String(8), default="row-2")
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    hide_oshi: Mapped[bool] = mapped_column(Boolean, default=False)
    notif_prefs: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    blocked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    block_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    muted_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    points: Mapped[int] = mapped_column(Integer, default=0)
    streak: Mapped[int] = mapped_column(Integer, default=0)
    last_daily_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    oshis: Mapped[list["UserOshi"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "userId": self.user_id,
            "seq": self.seq,
            "profilePicture": self.profile_picture,
            "name": self.name,
            "memberId": self.member_id,
            "username": self.username,
            "email": self.email,
            "ofcStatus": self.ofc_status,
            "bio": self.bio,
            "provider": self.provider,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "isEmailVerified": self.is_email_verified,
            "isPublic": self.is_public,
            "publicYear": self.public_year,
            "isAdmin": self.is_admin,
            "failedLoginAttempts": self.failed_login_attempts,
            "isAccountLocked": self.is_account_locked,
            "accountLockedUntil": self.account_locked_until,
            "role": self.role,
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
            "id": self.id,
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
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    kind: Mapped[str] = mapped_column(String(16), default="member")
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "userId": self.user_id,
            "device": self.device,
            "ip": self.ip,
            "browser": self.browser,
            "loginAt": self.login_at,
            "userAgentRaw": self.user_agent_raw,
            "success": self.success,
            "kind": self.kind,
            "username": self.username,
        }


class VerificationToken(Base):
    __tablename__ = "verification_tokens"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    hash_token: Mapped[str] = mapped_column(String(64), index=True)
    token_type: Mapped[str] = mapped_column(String(32))  # verification | otp | reset_otp
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (Index("ix_verification_hash_type", "hash_token", "token_type"),)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "userId": self.user_id,
            "hashToken": self.hash_token,
            "tokenType": self.token_type,
            "expiresAt": self.expires_at,
            "createdAt": self.created_at,
        }


# =====================================================================
# MEMBERS (kanonik JKT48Verse)
# =====================================================================
class Member(Base):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    nickname: Mapped[str] = mapped_column(String(60))
    generation: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(12), default="regular", index=True)  # regular|trainee|graduated|former
    team: Mapped[Optional[str]] = mapped_column(String(24), nullable=True)
    birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    height: Mapped[Optional[str]] = mapped_column(String(12), nullable=True)
    blood_type: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)
    horoscope: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    jikoshoukai: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hobbies: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    trivia: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    socials: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    show_birthday: Mapped[bool] = mapped_column(Boolean, default=True)
    # id eksternal dari jkt48.com (diisi scraper untuk upsert idempoten)
    external_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "slug": self.slug,
            "name": self.name,
            "nickname": self.nickname,
            "generation": self.generation,
            "status": self.status,
            "team": self.team,
            "birthDate": self.birth_date.isoformat() if self.birth_date else None,
            "height": self.height,
            "bloodType": self.blood_type,
            "horoscope": self.horoscope,
            "jikoshoukai": self.jikoshoukai,
            "hobbies": self.hobbies,
            "trivia": self.trivia,
            "socials": self.socials or {},
            "showBirthday": self.show_birthday,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }


class UserOshi(Base):
    __tablename__ = "user_oshi"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_seq: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.seq", ondelete="CASCADE"), index=True
    )
    member_id: Mapped[int] = mapped_column(Integer, ForeignKey("members.id", ondelete="CASCADE"))
    rank: Mapped[int] = mapped_column(Integer, default=1)  # 0 = kami-oshi

    __table_args__ = (UniqueConstraint("user_seq", "member_id", name="user_oshi_uq"),)


# =====================================================================
# SCHEDULE
# =====================================================================
class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    type: Mapped[str] = mapped_column(String(12), default="theater")  # theater|event|concert|media|other
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    map_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    setlist: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    ticket_status: Mapped[str] = mapped_column(String(12), default="unknown")  # available|sold_out|closed|unknown
    ticket_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    flag: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # shonichi|senshuuraku
    # id event/teater dari jkt48.com (diisi scraper untuk upsert idempoten)
    source_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ScheduleMember(Base):
    __tablename__ = "schedule_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    schedule_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("schedules.id", ondelete="CASCADE"), index=True
    )
    member_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("members.id", ondelete="CASCADE")
    )

    __table_args__ = (
        UniqueConstraint("schedule_id", "member_id", name="schedule_members_uq"),
    )


class ScheduleReminder(Base):
    __tablename__ = "schedule_reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_seq: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.seq", ondelete="CASCADE"), index=True
    )
    schedule_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("schedules.id", ondelete="CASCADE")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        UniqueConstraint("user_seq", "schedule_id", name="schedule_reminders_uq"),
    )


# =====================================================================
# NEWS
# =====================================================================
class News(Base):
    __tablename__ = "news"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text, default="")
    body: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(12), default="other", index=True)  # theater|event|release|birthday|other
    is_highlighted: Mapped[bool] = mapped_column(Boolean, default=False)
    views: Mapped[int] = mapped_column(Integer, default=0)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    # sumber eksternal (diisi scraper untuk upsert idempoten)
    source_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, unique=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# =====================================================================
# LIVE
# =====================================================================
class LiveSession(Base):
    __tablename__ = "live_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    member_name: Mapped[str] = mapped_column(String(100))
    platform: Mapped[str] = mapped_column(String(12))  # showroom | idn
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    room_key: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)
    stream_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    viewers: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    replay_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# =====================================================================
# ENCYCLOPEDIA / GLOSSARY / MOTIVATION
# =====================================================================
class Encyclopedia(Base):
    __tablename__ = "encyclopedia"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(60), unique=True)
    title: Mapped[str] = mapped_column(String(160))
    content: Mapped[str] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Glossary(Base):
    __tablename__ = "glossary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    term: Mapped[str] = mapped_column(String(80), index=True)
    meaning: Mapped[str] = mapped_column(Text)


class Motivation(Base):
    __tablename__ = "motivations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quote: Mapped[str] = mapped_column(Text)
    author: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    template: Mapped[str] = mapped_column(String(24), default="jkt48-red-white")
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    featured_on: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# =====================================================================
# GAMES
# =====================================================================
class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question: Mapped[str] = mapped_column(Text)
    options: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    correct_index: Mapped[int] = mapped_column(Integer)
    level: Mapped[str] = mapped_column(String(8), default="easy")  # easy|medium|hard
    category: Mapped[str] = mapped_column(String(16), default="umum")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class GuessQuestion(Base):
    __tablename__ = "guess_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_id: Mapped[int] = mapped_column(Integer, ForeignKey("members.id", ondelete="CASCADE"))
    hints: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class GameSession(Base):
    __tablename__ = "game_sessions"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_seq: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    game: Mapped[str] = mapped_column(String(16))  # quiz | guess | daily
    level: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    question_ids: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    current_index: Mapped[int] = mapped_column(Integer, default=0)
    score: Mapped[int] = mapped_column(Integer, default=0)
    correct: Mapped[int] = mapped_column(Integer, default=0)
    hints_used: Mapped[int] = mapped_column(Integer, default=0)
    question_shown_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class GameScore(Base):
    __tablename__ = "game_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_seq: Mapped[int] = mapped_column(BigInteger, index=True)
    game: Mapped[str] = mapped_column(String(16), index=True)
    score: Mapped[int] = mapped_column(Integer)
    detail: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (Index("game_scores_idx", "game", "created_at"),)


class SorterResult(Base):
    __tablename__ = "sorter_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_seq: Mapped[int] = mapped_column(BigInteger, index=True)
    ranking: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# =====================================================================
# CHAT & MODERASI
# =====================================================================
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_seq: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
    username: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(16), default="MEMBER")
    avatar_seed: Mapped[int] = mapped_column(Integer, default=1)
    body: Mapped[str] = mapped_column(String(500))
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (Index("chat_created_idx", "created_at"),)


class ChatReaction(Base):
    __tablename__ = "chat_reactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chat_messages.id", ondelete="CASCADE"), index=True
    )
    user_seq: Mapped[int] = mapped_column(BigInteger)
    emoji: Mapped[str] = mapped_column(String(8))

    __table_args__ = (UniqueConstraint("message_id", "user_seq", name="chat_reactions_uq"),)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[int] = mapped_column(Integer, index=True)
    reporter_seq: Mapped[int] = mapped_column(BigInteger)
    target_user_seq: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    target_username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    reason: Mapped[str] = mapped_column(String(24))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(12), default="pending")  # pending|approved|rejected
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BannedWord(Base):
    __tablename__ = "banned_words"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    word: Mapped[str] = mapped_column(String(60), unique=True)


class ModerationLog(Base):
    __tablename__ = "moderation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_seq: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    kind: Mapped[str] = mapped_column(String(24))
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# =====================================================================
# BIRTHDAY / BOOKMARK / NOTIFICATION
# =====================================================================
class BirthdayWish(Base):
    __tablename__ = "birthday_wishes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_id: Mapped[int] = mapped_column(Integer, ForeignKey("members.id", ondelete="CASCADE"), index=True)
    user_seq: Mapped[int] = mapped_column(BigInteger)
    username: Mapped[str] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(String(200))
    year: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        UniqueConstraint("member_id", "user_seq", "year", name="birthday_wishes_uq"),
    )


class Bookmark(Base):
    __tablename__ = "bookmarks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_seq: Mapped[int] = mapped_column(BigInteger, index=True)
    entity_type: Mapped[str] = mapped_column(String(16))
    entity_id: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        UniqueConstraint("user_seq", "entity_type", "entity_id", name="bookmarks_uq"),
    )


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_seq: Mapped[int] = mapped_column(BigInteger, index=True)
    type: Mapped[str] = mapped_column(String(24))
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    href: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (Index("notif_user_idx", "user_seq", "is_read"),)


class AISearchHistory(Base):
    __tablename__ = "ai_search_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_seq: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    client_key: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    mode: Mapped[str] = mapped_column(String(8))
    query: Mapped[str] = mapped_column(String(200))
    answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    feedback: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Contributor(Base):
    __tablename__ = "contributors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    role: Mapped[str] = mapped_column(String(60))
    contribution: Mapped[str] = mapped_column(Text)


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_seq: Mapped[int] = mapped_column(BigInteger, index=True)
    action: Mapped[str] = mapped_column(String(40))
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AppMeta(Base):
    __tablename__ = "app_meta"

    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# =====================================================================
# LEGACY (modul lama JKT48Verse yang masih dilayani: setlists & concerts)
# =====================================================================
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
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
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
            "image": self.image or "",
        }
