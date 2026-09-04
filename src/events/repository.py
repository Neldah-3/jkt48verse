from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import Event, EventMember, Member, Setlist


class EventsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def insert_event(self, event_data: dict):
        event = Event(
            id=str(event_data["id"]),
            title=event_data.get("title", ""),
            date=event_data["date"],
            url=event_data.get("url", ""),
            label=event_data.get("label", ""),
            type=event_data.get("type"),
            setlist_id=event_data.get("setlistId"),
            image_url=event_data.get("imageUrl"),
            raw_data=event_data.get("raw_data"),
        )
        self.session.add(event)
        for member_id in event_data.get("memberIds") or []:
            self.session.add(
                EventMember(event_id=event.id, member_id=str(member_id), role="member")
            )
        for member_id in event_data.get("seitansaiIds") or []:
            self.session.add(
                EventMember(event_id=event.id, member_id=str(member_id), role="seitansai")
            )
        for member_id in event_data.get("graduationIds") or []:
            self.session.add(
                EventMember(
                    event_id=event.id, member_id=str(member_id), role="graduation"
                )
            )
        await self.session.flush()
        return event

    async def upsert_event(self, event_data: dict):
        event_id = str(event_data["id"])
        result = await self.session.execute(
            select(Event).options(selectinload(Event.members)).where(Event.id == event_id)
        )
        event = result.scalar_one_or_none()
        if event:
            event.title = event_data.get("title", event.title)
            event.date = event_data.get("date", event.date)
            event.url = event_data.get("url", event.url)
            event.label = event_data.get("label", event.label)
            event.type = event_data.get("type", event.type)
            event.setlist_id = event_data.get("setlistId", event.setlist_id)
            event.image_url = event_data.get("imageUrl", event.image_url)
            if "raw_data" in event_data:
                event.raw_data = event_data["raw_data"]
            for row in list(event.members):
                await self.session.delete(row)
        else:
            event = Event(
                id=event_id,
                title=event_data.get("title", ""),
                date=event_data["date"],
                url=event_data.get("url", ""),
                label=event_data.get("label", ""),
                type=event_data.get("type"),
                setlist_id=event_data.get("setlistId"),
                image_url=event_data.get("imageUrl"),
                raw_data=event_data.get("raw_data"),
            )
            self.session.add(event)
            await self.session.flush()

        for member_id in event_data.get("memberIds") or []:
            self.session.add(
                EventMember(event_id=event_id, member_id=str(member_id), role="member")
            )
        for member_id in event_data.get("seitansaiIds") or []:
            self.session.add(
                EventMember(event_id=event_id, member_id=str(member_id), role="seitansai")
            )
        for member_id in event_data.get("graduationIds") or []:
            self.session.add(
                EventMember(
                    event_id=event_id, member_id=str(member_id), role="graduation"
                )
            )
        await self.session.flush()
        return event

    def _date_conditions(self, query: dict | None):
        if not query:
            return []
        conditions = []
        if "$or" in query:
            or_parts = []
            for part in query["$or"]:
                date_filter = part.get("date", {})
                setlist_ne = part.get("setlistId")
                sub = []
                if "$gte" in date_filter:
                    sub.append(Event.date >= date_filter["$gte"])
                if setlist_ne is None:
                    sub.append(Event.setlist_id.is_(None))
                elif setlist_ne == {"$ne": None}:
                    sub.append(Event.setlist_id.is_not(None))
                if sub:
                    or_parts.append(and_(*sub))
            if or_parts:
                conditions.append(or_(*or_parts))
        elif "date" in query:
            date_filter = query["date"]
            if "$gte" in date_filter:
                conditions.append(Event.date >= date_filter["$gte"])
            if "$lte" in date_filter:
                conditions.append(Event.date <= date_filter["$lte"])
        return conditions

    async def count_events(self, query: dict = None) -> int:
        stmt = select(func.count()).select_from(Event)
        conditions = self._date_conditions(query)
        if conditions:
            stmt = stmt.where(*conditions)
        result = await self.session.execute(stmt)
        return int(result.scalar() or 0)

    async def _hydrate(self, events: List[Event]) -> List[dict]:
        if not events:
            return []
        setlist_ids = {e.setlist_id for e in events if e.setlist_id}
        setlists = {}
        if setlist_ids:
            result = await self.session.execute(
                select(Setlist).where(Setlist.setlist_id.in_(setlist_ids))
            )
            setlists = {s.setlist_id: s for s in result.scalars().all()}

        all_member_ids = set()
        for event in events:
            for m in event.members:
                all_member_ids.add(m.member_id)

        members_map = {}
        if all_member_ids:
            result = await self.session.execute(
                select(Member).where(Member.id.in_(all_member_ids))
            )
            members_map = {m.id: m.to_dict() for m in result.scalars().all()}

        hydrated = []
        for event in events:
            setlist = setlists.get(event.setlist_id) if event.setlist_id else None
            member_docs = [
                members_map[m.member_id]
                for m in event.members
                if m.role == "member" and m.member_id in members_map
            ]
            seitansai = [
                members_map[m.member_id]["name"]
                for m in event.members
                if m.role == "seitansai" and m.member_id in members_map
            ]
            graduation = [
                members_map[m.member_id]["name"]
                for m in event.members
                if m.role == "graduation" and m.member_id in members_map
            ]
            hydrated.append(
                {
                    "id": event.id,
                    "title": event.title,
                    "date": event.date,
                    "url": event.url,
                    "label": event.label,
                    "type": event.type,
                    "setlistId": event.setlist_id,
                    "imageUrl": event.image_url or (setlist.image_url if setlist else None),
                    "totalMembers": len([m for m in event.members if m.role == "member"]),
                    "seitansaiMembers": seitansai,
                    "graduationMembers": graduation,
                    "members": member_docs,
                    "raw_data": event.raw_data,
                    "memberIds": event.member_ids("member"),
                    "seitansaiIds": event.member_ids("seitansai"),
                    "graduationIds": event.member_ids("graduation"),
                }
            )
        return hydrated

    async def find_events_paginated(
        self, skip: int, limit: int, query: dict = None, sort_direction: int = 1
    ) -> List[dict]:
        stmt = select(Event).options(selectinload(Event.members))
        conditions = self._date_conditions(query)
        if conditions:
            stmt = stmt.where(*conditions)
        order = Event.date.asc() if sort_direction >= 0 else Event.date.desc()
        stmt = stmt.order_by(order).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return await self._hydrate(list(result.scalars().unique().all()))

    async def find_event_by_id(self, event_id: str) -> Optional[dict]:
        result = await self.session.execute(
            select(Event).options(selectinload(Event.members)).where(Event.id == event_id)
        )
        event = result.scalar_one_or_none()
        if not event:
            return None
        rows = await self._hydrate([event])
        return rows[0] if rows else None

    async def find_events_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[dict]:
        result = await self.session.execute(
            select(Event)
            .options(selectinload(Event.members))
            .where(Event.date >= start_date, Event.date <= end_date)
            .order_by(Event.date.asc())
        )
        events = list(result.scalars().unique().all())
        hydrated = await self._hydrate(events)
        return [
            {
                "id": e["id"],
                "title": e["title"],
                "date": e["date"],
                "url": e["url"],
                "label": e["label"],
                "type": e["type"],
                "setlistId": e["setlistId"],
                "seitansaiMembers": e["seitansaiMembers"],
                "graduationMembers": e["graduationMembers"],
            }
            for e in hydrated
        ]

    async def find_events_by_member_id(self, member_id: str) -> List[dict]:
        result = await self.session.execute(
            select(Event)
            .join(EventMember, EventMember.event_id == Event.id)
            .where(EventMember.member_id == member_id, EventMember.role == "member")
            .order_by(Event.date.desc())
        )
        return [{"title": e.title, "date": e.date, "url": e.url} for e in result.scalars().all()]

    async def count_member_events(self, member_id: str) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(EventMember)
            .where(EventMember.member_id == member_id, EventMember.role == "member")
        )
        return int(result.scalar() or 0)

    async def find_events_by_member_id_detailed(
        self, member_id: str, skip: int = 0, limit: int = 500
    ) -> List[dict]:
        result = await self.session.execute(
            select(Event)
            .options(selectinload(Event.members))
            .join(EventMember, EventMember.event_id == Event.id)
            .where(EventMember.member_id == member_id, EventMember.role == "member")
            .order_by(Event.date.desc())
            .offset(skip)
            .limit(limit)
        )
        return await self._hydrate(list(result.scalars().unique().all()))

    async def get_member_event_stats(self, member_id: str) -> dict:
        events_result = await self.session.execute(
            select(Event)
            .join(EventMember, EventMember.event_id == Event.id)
            .where(EventMember.member_id == member_id, EventMember.role == "member")
        )
        events = list(events_result.scalars().all())
        total = len(events)
        counts: dict[str, int] = {}
        for event in events:
            if event.setlist_id:
                counts[event.setlist_id] = counts.get(event.setlist_id, 0) + 1
        top_setlist_id = max(counts, key=counts.get) if counts else None
        top_setlist_title = None
        if top_setlist_id:
            setlist_result = await self.session.execute(
                select(Setlist).where(Setlist.setlist_id == top_setlist_id)
            )
            setlist = setlist_result.scalar_one_or_none()
            top_setlist_title = setlist.title if setlist else None
        return {
            "total_shows": total,
            "top_setlist_id": top_setlist_id,
            "top_setlist_title": top_setlist_title,
            "top_setlist_count": counts.get(top_setlist_id, 0) if top_setlist_id else 0,
            "unique_setlists": len(counts),
        }

    async def update_event_raw_data_detail(self, event_id: str, detail_data: dict):
        result = await self.session.execute(select(Event).where(Event.id == event_id))
        event = result.scalar_one_or_none()
        if not event:
            return
        raw = dict(event.raw_data or {})
        raw["detail"] = detail_data
        event.raw_data = raw
        await self.session.flush()

    async def update_event_live_members(
        self, event_id: str, member_ids: List[str], seitansai_ids: List[str]
    ):
        result = await self.session.execute(
            select(Event).options(selectinload(Event.members)).where(Event.id == event_id)
        )
        event = result.scalar_one_or_none()
        if not event:
            return
        for row in list(event.members):
            if row.role in ("member", "seitansai"):
                await self.session.delete(row)
        for member_id in member_ids:
            self.session.add(
                EventMember(event_id=event_id, member_id=str(member_id), role="member")
            )
        for member_id in seitansai_ids:
            self.session.add(
                EventMember(event_id=event_id, member_id=str(member_id), role="seitansai")
            )
        await self.session.flush()
