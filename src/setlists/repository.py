from typing import List, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Setlist


class SetlistsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _filters(
        self,
        setlist_type: Optional[str] = None,
        active: Optional[bool] = None,
        search: Optional[str] = None,
    ):
        conditions = []
        if setlist_type:
            conditions.append(Setlist.type == setlist_type)
        if active is not None:
            conditions.append(Setlist.active.is_(active))
        if search:
            like = f"%{search}%"
            conditions.append(
                or_(Setlist.title.ilike(like), Setlist.title_japanese.ilike(like))
            )
        return conditions

    async def find_all(
        self,
        skip: int = 0,
        limit: int = 100,
        setlist_type: Optional[str] = None,
        active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> List[dict]:
        stmt = select(Setlist)
        conditions = self._filters(setlist_type, active, search)
        if conditions:
            stmt = stmt.where(*conditions)
        stmt = stmt.order_by(Setlist.active.desc(), Setlist.title.asc()).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return [s.to_dict() for s in result.scalars().all()]

    async def count(
        self,
        setlist_type: Optional[str] = None,
        active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> int:
        stmt = select(func.count()).select_from(Setlist)
        conditions = self._filters(setlist_type, active, search)
        if conditions:
            stmt = stmt.where(*conditions)
        result = await self.session.execute(stmt)
        return int(result.scalar() or 0)

    async def find_by_setlist_id(self, setlist_id: str) -> Optional[dict]:
        result = await self.session.execute(
            select(Setlist).where(Setlist.setlist_id == setlist_id)
        )
        row = result.scalar_one_or_none()
        return row.to_dict() if row else None

    async def find_by_title(self, title: str) -> Optional[dict]:
        result = await self.session.execute(
            select(Setlist).where(func.lower(Setlist.title) == title.lower())
        )
        row = result.scalar_one_or_none()
        return row.to_dict() if row else None

    async def get_types(self) -> List[str]:
        result = await self.session.execute(select(Setlist.type).distinct())
        return sorted([t for t in result.scalars().all() if t])

    async def upsert_one(self, data: dict) -> dict:
        setlist_id = data.get("setlistId") or data.get("setlist_id")
        result = await self.session.execute(
            select(Setlist).where(Setlist.setlist_id == setlist_id)
        )
        row = result.scalar_one_or_none()
        payload = {
            "image_url": data.get("imageUrl") or data.get("image_url"),
            "title": data.get("title", ""),
            "title_japanese": data.get("titleJapanese") or data.get("title_japanese"),
            "description": data.get("description", ""),
            "type": data.get("type", "setlist"),
            "active": data.get("active", False),
            "songs": data.get("songs") or [],
        }
        if row:
            for k, v in payload.items():
                setattr(row, k, v)
        else:
            row = Setlist(setlist_id=setlist_id, **payload)
            self.session.add(row)
        await self.session.flush()
        return row.to_dict()

    async def insert_one(self, setlist: dict) -> dict:
        return await self.upsert_one(setlist)

    async def update_one(self, setlist_id: str, update_data: dict) -> Optional[dict]:
        result = await self.session.execute(
            select(Setlist).where(Setlist.setlist_id == setlist_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        mapping = {
            "imageUrl": "image_url",
            "titleJapanese": "title_japanese",
        }
        for k, v in update_data.items():
            attr = mapping.get(k, k)
            if hasattr(row, attr):
                setattr(row, attr, v)
        await self.session.flush()
        return row.to_dict()

    async def delete_one(self, setlist_id: str) -> bool:
        result = await self.session.execute(
            select(Setlist).where(Setlist.setlist_id == setlist_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return False
        await self.session.delete(row)
        await self.session.flush()
        return True
