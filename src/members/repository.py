"""Repository member kanonik JKT48Verse (dipakai antara lain oleh modul live)."""

from typing import List, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Member


class MemberRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_all(
        self,
        skip: int = 0,
        limit: int = 100,
        generation: Optional[str] = None,
        search: Optional[str] = None,
        include_inactive: bool = False,
    ) -> List[dict]:
        stmt = select(Member)
        conds = []
        if not include_inactive:
            conds.append(Member.status.in_(["regular", "trainee"]))
        if generation:
            try:
                conds.append(Member.generation == int(generation))
            except (TypeError, ValueError):
                pass
        if search:
            like = f"%{search}%"
            conds.append(
                or_(Member.name.ilike(like), Member.nickname.ilike(like))
            )
        if conds:
            stmt = stmt.where(*conds)
        stmt = stmt.order_by(Member.name.asc()).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return [m.to_dict() for m in result.scalars().all()]

    async def find_all_active(self) -> List[dict]:
        result = await self.session.execute(
            select(Member)
            .where(Member.status.in_(["regular", "trainee"]))
            .order_by(Member.name.asc())
        )
        return [m.to_dict() for m in result.scalars().all()]

    async def count(
        self,
        generation: Optional[str] = None,
        search: Optional[str] = None,
        include_inactive: bool = False,
    ) -> int:
        rows = await self.find_all(
            generation=generation, search=search, include_inactive=include_inactive, limit=100000
        )
        return len(rows)

    async def find_by_slug(self, slug: str) -> Optional[dict]:
        result = await self.session.execute(select(Member).where(Member.slug == slug))
        member = result.scalar_one_or_none()
        return member.to_dict() if member else None

    async def find_by_id(self, member_id) -> Optional[dict]:
        try:
            result = await self.session.execute(
                select(Member).where(Member.id == int(member_id))
            )
        except (TypeError, ValueError):
            return None
        member = result.scalar_one_or_none()
        return member.to_dict() if member else None

    async def find_by_nickname(self, nickname: str) -> Optional[dict]:
        result = await self.session.execute(
            select(Member).where(func.lower(Member.nickname) == nickname.lower())
        )
        member = result.scalar_one_or_none()
        return member.to_dict() if member else None
