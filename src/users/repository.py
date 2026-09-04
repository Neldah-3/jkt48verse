from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User, UserOshi


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

    async def insert_user(self, user_data: dict):
        oshi_ids = user_data.get("oshiIds") or []
        mapped = self._apply_camel(user_data)
        user = User(**{k: v for k, v in mapped.items() if hasattr(User, k)})
        self.session.add(user)
        for oid in oshi_ids:
            self.session.add(UserOshi(user_id=user.user_id, member_id=str(oid)))
        try:
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            raise
        return user

    async def find_one(self, query: dict) -> Optional[dict]:
        stmt = select(User)
        if "$or" in query:
            conditions = []
            for cond in query["$or"]:
                if "username" in cond:
                    conditions.append(User.username == cond["username"])
                if "email" in cond:
                    conditions.append(User.email == cond["email"])
                if "userId" in cond:
                    conditions.append(User.user_id == cond["userId"])
            if conditions:
                stmt = stmt.where(or_(*conditions))
        elif "userId" in query:
            stmt = stmt.where(User.user_id == query["userId"])
        elif "username" in query:
            stmt = stmt.where(User.username == str(query["username"]).lower())
        elif "email" in query:
            stmt = stmt.where(User.email == str(query["email"]).lower())
        else:
            return None

        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        return user.to_dict() if user else None

    async def get_user_by_id(self, user_id: str) -> Optional[dict]:
        result = await self.session.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()
        return user.to_dict() if user else None

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

    async def increment_failed_login_attempts(self, user_id: str):
        result = await self.session.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            await self.session.flush()

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

    async def add_oshi_id(self, user_id: str, oshi_id: str):
        self.session.add(UserOshi(user_id=user_id, member_id=str(oshi_id)))
        await self.session.flush()

    async def remove_oshi_id(self, user_id: str, oshi_id: str):
        result = await self.session.execute(
            select(UserOshi).where(
                UserOshi.user_id == user_id, UserOshi.member_id == str(oshi_id)
            )
        )
        row = result.scalar_one_or_none()
        if row:
            await self.session.delete(row)
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
                or_(User.name.ilike(like), User.email.ilike(like), User.username.ilike(like))
            )
        stmt = stmt.order_by(User.created_at.desc()).offset((page - 1) * limit).limit(limit)
        result = await self.session.execute(stmt)
        return [u.to_dict() for u in result.scalars().all()]

    async def count_all(self, search: str | None = None) -> int:
        stmt = select(func.count()).select_from(User)
        if search:
            like = f"%{search}%"
            stmt = stmt.where(
                or_(User.name.ilike(like), User.email.ilike(like), User.username.ilike(like))
            )
        result = await self.session.execute(stmt)
        return int(result.scalar() or 0)
