from typing import List, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Member


class MemberRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _filters(
        self,
        generation: Optional[str] = None,
        search: Optional[str] = None,
        include_inactive: bool = False,
    ):
        conditions = []
        if not include_inactive:
            conditions.append(Member.active.is_(True))
        if generation:
            conditions.append(Member.generation == generation)
        if search:
            like = f"%{search}%"
            conditions.append(or_(Member.name.ilike(like), Member.nickname.ilike(like)))
        return conditions

    async def insert_many(self, members: List[dict]) -> int:
        count = 0
        for data in members:
            member = await self._upsert(data)
            if member:
                count += 1
        await self.session.flush()
        return count

    async def _upsert(self, data: dict) -> Member:
        member_id = str(data.get("id"))
        result = await self.session.execute(select(Member).where(Member.id == member_id))
        member = result.scalar_one_or_none()
        payload = {
            "name": data.get("name", ""),
            "nickname": data.get("nickname"),
            "generation": data.get("generation"),
            "jiko": data.get("jiko"),
            "active": data.get("active", True),
            "href": data.get("href"),
            "img": data.get("img"),
            "birthdate": data.get("birthdate"),
            "blood_type": data.get("bloodType") or data.get("blood_type"),
            "horoscope": data.get("horoscope"),
            "height": data.get("height"),
            "socials": data.get("socials") or {},
            "member_type": data.get("member_type", "JKT48"),
            "member_code": data.get("member_code"),
        }
        if member:
            for k, v in payload.items():
                setattr(member, k, v)
        else:
            member = Member(id=member_id, **payload)
            self.session.add(member)
        return member

    async def find_all(
        self,
        skip: int = 0,
        limit: int = 100,
        generation: Optional[str] = None,
        search: Optional[str] = None,
        include_inactive: bool = False,
    ) -> List[dict]:
        stmt = select(Member)
        conditions = self._filters(generation, search, include_inactive)
        if conditions:
            stmt = stmt.where(*conditions)
        stmt = (
            stmt.order_by(Member.active.desc(), Member.name.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [m.to_dict() for m in result.scalars().all()]

    async def find_all_active(self) -> List[dict]:
        result = await self.session.execute(
            select(Member).where(Member.active.is_(True)).order_by(Member.name.asc())
        )
        return [m.to_dict() for m in result.scalars().all()]

    async def count(
        self,
        generation: Optional[str] = None,
        search: Optional[str] = None,
        include_inactive: bool = False,
    ) -> int:
        stmt = select(func.count()).select_from(Member)
        conditions = self._filters(generation, search, include_inactive)
        if conditions:
            stmt = stmt.where(*conditions)
        result = await self.session.execute(stmt)
        return int(result.scalar() or 0)

    async def find_by_id(self, member_id: str) -> Optional[dict]:
        result = await self.session.execute(select(Member).where(Member.id == member_id))
        member = result.scalar_one_or_none()
        return member.to_dict() if member else None

    async def find_by_nickname(self, nickname: str) -> Optional[dict]:
        result = await self.session.execute(
            select(Member).where(func.lower(Member.nickname) == nickname.lower())
        )
        member = result.scalar_one_or_none()
        return member.to_dict() if member else None

    async def find_by_name(self, name: str) -> Optional[dict]:
        result = await self.session.execute(
            select(Member).where(
                or_(
                    func.lower(Member.name) == name.lower(),
                    func.lower(Member.nickname) == name.lower(),
                )
            )
        )
        member = result.scalar_one_or_none()
        return member.to_dict() if member else None

    async def get_generations(self) -> List[str]:
        result = await self.session.execute(
            select(Member.generation)
            .where(Member.active.is_(True), Member.generation.is_not(None))
            .distinct()
        )
        generations = [g for g in result.scalars().all() if g]
        return sorted(generations)

    async def get_next_id(self) -> int:
        result = await self.session.execute(select(Member.id))
        ids = []
        for value in result.scalars().all():
            try:
                ids.append(int(value))
            except (ValueError, TypeError):
                continue
        return (max(ids) + 1) if ids else 1

    async def insert_one(self, member: dict) -> dict:
        obj = await self._upsert(member)
        await self.session.flush()
        return obj.to_dict()

    async def update_one(self, member_id: str, update_data: dict) -> Optional[dict]:
        result = await self.session.execute(select(Member).where(Member.id == member_id))
        member = result.scalar_one_or_none()
        if not member:
            return None
        mapping = {
            "bloodType": "blood_type",
            "member_type": "member_type",
            "member_code": "member_code",
        }
        for k, v in update_data.items():
            attr = mapping.get(k, k)
            if hasattr(member, attr):
                setattr(member, attr, v)
        await self.session.flush()
        return member.to_dict()

    async def delete_one(self, member_id: str) -> bool:
        result = await self.session.execute(select(Member).where(Member.id == member_id))
        member = result.scalar_one_or_none()
        if not member:
            return False
        await self.session.delete(member)
        await self.session.flush()
        return True
