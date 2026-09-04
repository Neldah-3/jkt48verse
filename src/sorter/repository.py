from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Sorter
from src.sorter.schemas import SorterInDB


class SortersRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_sorter(self, sorter: SorterInDB):
        row = Sorter(
            user_id=sorter.user_id,
            title=sorter.title,
            description=sorter.description,
            filters=sorter.filters,
            results=[item.model_dump() for item in sorter.results],
            created_at=sorter.created_at,
            updated_at=sorter.updated_at,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def get_sorter(self, sorter_id: str, user_id: str) -> Optional[dict]:
        result = await self.session.execute(
            select(Sorter).where(Sorter.id == sorter_id, Sorter.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        return row.to_dict() if row else None

    async def get_sorters(
        self, user_id: str, page: int = 1, limit: int = 15
    ) -> tuple[List[dict], int]:
        skip = (page - 1) * limit
        result = await self.session.execute(
            select(Sorter)
            .where(Sorter.user_id == user_id)
            .order_by(Sorter.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        data = [s.to_dict() for s in result.scalars().all()]
        total_result = await self.session.execute(
            select(func.count()).select_from(Sorter).where(Sorter.user_id == user_id)
        )
        total = int(total_result.scalar() or 0)
        return data, total

    async def delete_sorter(self, sorter_id: str, user_id: str) -> bool:
        result = await self.session.execute(
            select(Sorter).where(Sorter.id == sorter_id, Sorter.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return False
        await self.session.delete(row)
        await self.session.flush()
        return True

    async def update_sorter(self, sorter_id: str, user_id: str, update_data: dict) -> bool:
        result = await self.session.execute(
            select(Sorter).where(Sorter.id == sorter_id, Sorter.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return False
        for k, v in update_data.items():
            if hasattr(row, k):
                setattr(row, k, v)
        await self.session.flush()
        return True
