from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, case, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _apply_camel(self, values: dict) -> dict:
        mapping = {
            "userId": "user_id",
            "profilePicture": "profile_picture",
            "memberId": "member_id",
            "ofcStatus": "ofc_status",
            "isEmailVerified": "is_email_verified",
            "isPublic": "is_public",
            "publicYear": "public_year",
            "failedLoginAttempts": "failed_login_attempts",
            "isAccountLocked": "is_account_locked",
            "accountLockedUntil": "account_locked_until",
            "lastActiveAt": "last_active_at",
            "isAdmin": "is_admin",
            "createdAt": "created_at",
            "updatedAt": "updated_at",
        }
        out = {}
        for k, v in values.items():
            if k in ("oshiIds", "password"):
                out[k if k == "password" else k] = v
                if k == "password":
                    out["password"] = v
                continue
            out[mapping.get(k, k)] = v
        out.pop("oshiIds", None)
        return out

    @staticmethod
    def _identity_match(column, value: str):
        # Staff credentials are exact; ordinary usernames/emails are case-insensitive.
        # Do not lowercase the supplied identity before deciding which policy applies.
        return or_(
            and_(User.provider == "credential", column == value),
            and_(
                or_(User.provider.is_(None), User.provider != "credential"),
                func.lower(column) == value.lower(),
            ),
        )

    async def find_model_by_id(self, user_id: str) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.user_id == user_id))
        return result.scalar_one_or_none()

    async def find_one(self, query: dict) -> Optional[dict]:
        stmt = select(User)
        if "$or" in query:
            conditions = []
            for cond in query["$or"]:
                if "username" in cond:
                    conditions.append(
                        self._identity_match(User.username, cond["username"])
                    )
                if "email" in cond:
                    conditions.append(self._identity_match(User.email, cond["email"]))
                if "userId" in cond:
                    conditions.append(User.user_id == cond["userId"])
            if conditions:
                stmt = stmt.where(or_(*conditions))
        elif "userId" in query:
            stmt = stmt.where(User.user_id == query["userId"])
        elif "username" in query:
            stmt = stmt.where(
                self._identity_match(User.username, str(query["username"]))
            )
        elif "email" in query:
            stmt = stmt.where(self._identity_match(User.email, str(query["email"])))
        else:
            return None

        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        return user.to_dict() if user else None

    async def get_user_by_id(self, user_id: str) -> Optional[dict]:
        result = await self.session.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()
        return user.to_dict() if user else None

    async def get_password_hash(self, user_id: str) -> Optional[str]:
        result = await self.session.execute(
            select(User.password).where(User.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def update_one(self, filter_query: dict, update_data: dict):
        values = update_data.get("$set", update_data)
        mapped = self._apply_camel(values)
        user_id = filter_query.get("userId")
        result = await self.session.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return None
        for key, value in mapped.items():
            if hasattr(user, key):
                setattr(user, key, value)
        try:
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            raise
        return user

    async def record_failed_login(
        self, user_id: str, max_attempts: int, lock_minutes: int
    ) -> int:
        """Commit only the security counter, independently of a rejected request.

        A single UPDATE serializes concurrent failures. Never commit the request's
        entire unit of work merely to preserve this counter: it may contain other
        writes that must still roll back on a 401.
        """
        now = datetime.now(timezone.utc)
        expired = and_(
            User.is_account_locked.is_(True), User.account_locked_until <= now
        )
        attempts = case(
            (expired, 1), else_=func.coalesce(User.failed_login_attempts, 0) + 1
        )
        locked = attempts >= max_attempts
        stmt = (
            update(User)
            .where(
                User.user_id == user_id, or_(User.is_account_locked.is_(False), expired)
            )
            .values(
                failed_login_attempts=attempts,
                is_account_locked=locked,
                account_locked_until=case(
                    (locked, now + timedelta(minutes=lock_minutes)), else_=None
                ),
            )
            .returning(User.failed_login_attempts)
        )
        # Authentication is being rejected. Release its read transaction first,
        # otherwise many concurrent failures can exhaust the pool while each
        # waits for a second connection. Unrelated request writes stay rolled back.
        await self.session.rollback()
        async with AsyncSession(bind=self.session.bind) as security_session:
            async with security_session.begin():
                result = await security_session.execute(stmt)
                return result.scalar_one_or_none() or 0

    async def reset_failed_login_attempts(self, user_id: str):
        result = await self.session.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.failed_login_attempts = 0
            await self.session.flush()

    async def lock_account(self, user_id: str, locked_until):
        result = await self.session.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.is_account_locked = True
            user.account_locked_until = locked_until
            await self.session.flush()

    async def unlock_account(self, user_id: str):
        result = await self.session.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.is_account_locked = False
            user.account_locked_until = None
            user.failed_login_attempts = 0
            await self.session.flush()

    async def set_email_verified(self, user_id: str):
        result = await self.session.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.is_email_verified = True
            await self.session.flush()

    async def set_public_status(
        self, user_id: str, is_public: bool, public_year: Optional[int] = None
    ):
        result = await self.session.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.is_public = is_public
            user.public_year = public_year if is_public else None
            await self.session.flush()

    async def update_last_active(self, user_id: str):
        result = await self.session.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.last_active_at = datetime.now(timezone.utc)
            await self.session.flush()

    async def get_all_paginated(
        self, page: int, limit: int, search: str | None = None
    ) -> list[dict]:
        stmt = select(User)
        if search:
            like = f"%{search}%"
            stmt = stmt.where(
                or_(
                    User.name.ilike(like),
                    User.email.ilike(like),
                    User.username.ilike(like),
                )
            )
        stmt = (
            stmt.order_by(User.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [u.to_dict() for u in result.scalars().all()]

    async def count_all(self, search: str | None = None) -> int:
        stmt = select(func.count()).select_from(User)
        if search:
            like = f"%{search}%"
            stmt = stmt.where(
                or_(
                    User.name.ilike(like),
                    User.email.ilike(like),
                    User.username.ilike(like),
                )
            )
        result = await self.session.execute(stmt)
        return int(result.scalar() or 0)
