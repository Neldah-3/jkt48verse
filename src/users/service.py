"""Service user JKT48Verse — pembuatan akun + util pencarian."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.security_service import SecurityService
from src.logging_config import create_logger
from src.models import User

logger = create_logger("users_service", __name__)


class UsernameTakenError(Exception):
    pass


class EmailTakenError(Exception):
    pass


class UserService:
    def __init__(self, session: AsyncSession, security_service: SecurityService | None = None):
        self.session = session
        self.security_service = security_service

    async def _hash_password(self, password: str) -> str:
        if self.security_service is not None:
            return self.security_service.get_password_hash(password)
        from passlib.context import CryptContext

        ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return ctx.hash(password)

    async def create_user(self, username: str, email: str, password: str) -> User:
        existing = (
            await self.session.execute(
                select(User).where(
                    func.lower(User.username) == username.lower(),
                )
            )
        ).scalar_one_or_none()
        if existing:
            raise UsernameTakenError()
        existing = (
            await self.session.execute(select(User).where(func.lower(User.email) == email.lower()))
        ).scalar_one_or_none()
        if existing:
            raise EmailTakenError()

        import random

        hashed = await self._hash_password(password)
        user = User(
            user_id=str(uuid.uuid4()),
            name=username,
            username=username,
            email=email,
            password=hashed,
            role="MEMBER",
            avatar_seed=random.randint(1, 6),
            last_active_at=datetime.now(timezone.utc),
        )
        self.session.add(user)
        try:
            await self.session.flush()
        except IntegrityError as e:
            await self.session.rollback()
            raise e
        return user

    async def get_by_username(self, username: str) -> User | None:
        result = await self.session.execute(
            select(User).where(func.lower(User.username) == username.lower())
        )
        return result.scalar_one_or_none()
