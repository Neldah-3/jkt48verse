from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import LoginHistory, RefreshToken, VerificationToken


class AuthRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def insert_refresh_token(self, data: dict):
        token = RefreshToken(
            user_id=data["userId"],
            hash_refresh_token=data["hashRefreshToken"],
            device=data.get("device", ""),
            ip=data.get("ip", ""),
            browser=data.get("browser", ""),
            created_at=data.get("createdAt") or datetime.now(timezone.utc),
            last_used_at=data.get("lastUsedAt") or datetime.now(timezone.utc),
        )
        self.session.add(token)
        await self.session.flush()
        return token

    async def find_refresh_token(self, token: str) -> Optional[dict]:
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.hash_refresh_token == token)
        )
        row = result.scalar_one_or_none()
        return row.to_dict() if row else None

    async def update_refresh_token_last_used(self, token: str):
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.hash_refresh_token == token)
        )
        row = result.scalar_one_or_none()
        if row:
            row.last_used_at = datetime.now(timezone.utc)
            await self.session.flush()

    async def delete_refresh_token(self, token: str):
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.hash_refresh_token == token)
        )
        row = result.scalar_one_or_none()
        if row:
            await self.session.delete(row)
            await self.session.flush()

    async def delete_user_refresh_tokens(self, user_id: str):
        await self.session.execute(
            delete(RefreshToken).where(RefreshToken.user_id == user_id)
        )

    async def insert_login_history(self, data: dict):
        history = LoginHistory(
            user_id=data["userId"],
            device=data.get("device", ""),
            ip=data.get("ip", ""),
            browser=data.get("browser", ""),
            login_at=data.get("loginAt") or datetime.now(timezone.utc),
            user_agent_raw=data.get("userAgentRaw"),
        )
        self.session.add(history)
        await self.session.flush()
        return history

    async def find_last_login_history(self, user_id: str) -> Optional[dict]:
        result = await self.session.execute(
            select(LoginHistory)
            .where(LoginHistory.user_id == user_id)
            .order_by(LoginHistory.login_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return row.to_dict() if row else None

    async def delete_verification_tokens_by_user(self, user_id: str, token_type: str):
        result = await self.session.execute(
            select(VerificationToken).where(
                VerificationToken.user_id == user_id,
                VerificationToken.token_type == token_type,
            )
        )
        for row in result.scalars().all():
            await self.session.delete(row)
        await self.session.flush()

    async def insert_verification_token(self, data: dict):
        token = VerificationToken(
            user_id=data["userId"],
            hash_token=data["hashToken"],
            token_type=data["tokenType"],
            expires_at=data["expiresAt"],
            created_at=data.get("createdAt") or datetime.now(timezone.utc),
        )
        self.session.add(token)
        await self.session.flush()
        return token

    async def find_verification_token(
        self, token: str, token_type: str
    ) -> Optional[dict]:
        result = await self.session.execute(
            select(VerificationToken).where(
                VerificationToken.hash_token == token,
                VerificationToken.token_type == token_type,
            )
        )
        row = result.scalar_one_or_none()
        return row.to_dict() if row else None

    async def delete_verification_token(self, token: str, token_type: str):
        result = await self.session.execute(
            select(VerificationToken).where(
                VerificationToken.hash_token == token,
                VerificationToken.token_type == token_type,
            )
        )
        row = result.scalar_one_or_none()
        if row:
            await self.session.delete(row)
            await self.session.flush()
