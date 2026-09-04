from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.concerts.schemas import CreateConcert, UpdateConcert
from src.models import Concert


class ConcertsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def insert_concert(self, concert_data: CreateConcert):
        concert = Concert(
            title=concert_data.title,
            theme=concert_data.theme,
            type=concert_data.type,
            date=concert_data.date,
            location=concert_data.location,
            details=concert_data.details,
            benefits=concert_data.benefits,
            ticket_price=concert_data.ticket_price,
            image=concert_data.image,
        )
        self.session.add(concert)
        await self.session.flush()
        return concert

    async def find_concert_by_id(self, concert_id: str) -> Optional[dict]:
        result = await self.session.execute(select(Concert).where(Concert.id == concert_id))
        row = result.scalar_one_or_none()
        return row.to_dict() if row else None

    async def get_all_concerts(self) -> List[dict]:
        result = await self.session.execute(select(Concert).order_by(Concert.date.asc()))
        return [c.to_dict() for c in result.scalars().all()]

    async def update_concert(self, concert_id: str, update_data: UpdateConcert) -> bool:
        result = await self.session.execute(select(Concert).where(Concert.id == concert_id))
        row = result.scalar_one_or_none()
        if not row:
            return False
        update_dict = update_data.model_dump(exclude_unset=True)
        for k, v in update_dict.items():
            if hasattr(row, k):
                setattr(row, k, v)
        await self.session.flush()
        return True

    async def delete_concert(self, concert_id: str) -> bool:
        result = await self.session.execute(select(Concert).where(Concert.id == concert_id))
        row = result.scalar_one_or_none()
        if not row:
            return False
        await self.session.delete(row)
        await self.session.flush()
        return True
