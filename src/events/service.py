from datetime import datetime, timedelta
from math import ceil
from typing import List, Optional

from curl_cffi.requests import AsyncSession

from src.config import Settings
from src.events.exceptions import EventFetchError, EventNotFoundError
from src.events.repository import EventsRepository
from src.events.schemas import (
    CalendarEvent,
    Event,
    EventPaginationResponse,
    MemberEventStats,
    PaginationMeta,
)
from src.logging_config import create_logger
from src.members.service import MemberService

logger = create_logger("events_service", __name__)


class EventsService:
    def __init__(
        self,
        repository: EventsRepository,
        config: Settings,
        member_service: MemberService,
    ):
        self.repository = repository
        self.config = config
        self.member_service = member_service

    async def get_events_paginated(
        self,
        page: int = 1,
        limit: int = 20,
        current_only: bool = False,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> EventPaginationResponse:
        query = {}
        if current_only:
            now = datetime.now()
            today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
            query["$or"] = [
                {"date": {"$gte": now}, "setlistId": {"$ne": None}},
                {"date": {"$gte": today_midnight}, "setlistId": None},
            ]
        elif start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["$gte"] = start_date
            if end_date:
                date_filter["$lte"] = end_date
            query["date"] = date_filter

        try:
            total_data = await self.repository.count_events(query)
            last_page = max(1, ceil(total_data / limit)) if limit > 0 else 1
            if page < 1:
                page = 1
            skip = (page - 1) * limit
            sort_direction = 1 if current_only else -1
            raw_events = await self.repository.find_events_paginated(
                skip, limit, query, sort_direction
            )
            events_data = [Event(**resolved) for resolved in raw_events]
            next_page = page + 1 if page < last_page else None
            return EventPaginationResponse(
                data=events_data,
                meta=PaginationMeta(
                    current_page=page,
                    last_page=last_page,
                    total_data=total_data,
                    per_page=limit,
                    next_page=next_page,
                ),
            )
        except Exception as e:
            logger.exception(f"Failed to fetch paginated events: {str(e)}")
            raise EventFetchError() from e

    async def get_event_by_id(self, event_id: str) -> dict:
        try:
            raw_event = await self.repository.find_event_by_id(event_id)
            if not raw_event:
                raise EventNotFoundError()
            await self._fetch_and_inject_realtime_data(event_id, raw_event)
            return raw_event
        except EventNotFoundError:
            raise
        except Exception as e:
            logger.exception(f"Failed to fetch event by id {event_id}: {str(e)}")
            raise EventFetchError() from e

    async def get_calendar_events(self, year: int, month: int) -> List[CalendarEvent]:
        first_of_month = datetime(year, month, 1)
        days_to_subtract = (first_of_month.weekday() + 1) % 7
        start_date = first_of_month - timedelta(days=days_to_subtract)
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=42) - timedelta(microseconds=1)
        try:
            raw_events = await self.repository.find_events_by_date_range(start_date, end_date)
            results = [CalendarEvent(**e) for e in raw_events]
            birthdays = await self.member_service.get_birthdays_by_date_range(
                start_date, end_date
            )
            for b in birthdays:
                results.append(
                    CalendarEvent(
                        id=b["id"],
                        title=b["name"],
                        date=b["date"],
                        url=f"/member/detail/id/{b['id']}",
                        isBirthday=True,
                        setlistId=None,
                        seitansaiMembers=None,
                    )
                )
            return results
        except Exception as e:
            logger.exception(f"Failed to fetch calendar events: {str(e)}")
            raise EventFetchError() from e

    async def get_events_for_member(self, member_id: str) -> List[dict]:
        try:
            return await self.repository.find_events_by_member_id(member_id)
        except Exception as e:
            logger.exception(f"Failed to fetch events for member {member_id}: {str(e)}")
            return []

    async def get_member_event_stats(self, member_id: str) -> MemberEventStats:
        try:
            stats_data = await self.repository.get_member_event_stats(member_id)
            return MemberEventStats(**stats_data)
        except Exception as e:
            logger.exception(f"Failed to fetch event stats for member {member_id}: {str(e)}")
            return MemberEventStats()

    async def get_member_events_paginated(
        self, member_id: str, page: int = 1, limit: int = 20
    ) -> EventPaginationResponse:
        try:
            total_data = await self.repository.count_member_events(member_id)
            last_page = max(1, ceil(total_data / limit)) if limit > 0 else 1
            if page < 1:
                page = 1
            skip = (page - 1) * limit
            raw_events = await self.repository.find_events_by_member_id_detailed(
                member_id, skip=skip, limit=limit
            )
            events_data = [Event(**resolved) for resolved in raw_events]
            next_page = page + 1 if page < last_page else None
            return EventPaginationResponse(
                data=events_data,
                meta=PaginationMeta(
                    current_page=page,
                    last_page=last_page,
                    total_data=total_data,
                    per_page=limit,
                    next_page=next_page,
                ),
            )
        except Exception as e:
            logger.exception(
                f"Failed to fetch paginated events for member {member_id}: {str(e)}"
            )
            return EventPaginationResponse(
                data=[],
                meta=PaginationMeta(
                    current_page=page, last_page=1, total_data=0, per_page=limit, next_page=None
                ),
            )

    async def _fetch_and_inject_realtime_data(self, event_id: str, raw_event: dict):
        raw_data = raw_event.get("raw_data", {}) or {}
        short_data = raw_data.get("short", {}) or {}
        ref_code = short_data.get("reference_code")
        event_type = raw_event.get("type")
        if not ref_code:
            return
        url = None
        if event_type == "EXCLUSIVE":
            url = f"https://jkt48.com/api/v1/exclusives/{ref_code}"
        elif event_type == "SHOW":
            url = f"https://jkt48.com/api/v1/theater-shows/{ref_code}?lang=id"
        if not url:
            return
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
            "Referer": f"https://jkt48.com/purchase/schedule/show?code={ref_code}"
            if event_type == "SHOW"
            else f"https://jkt48.com/purchase/exclusive?code={ref_code}",
        }
        async with AsyncSession(timeout=10.0, impersonate="chrome124") as client:
            try:
                res = await client.get(url, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("status") and "data" in data:
                        if "raw_data" not in raw_event or raw_event["raw_data"] is None:
                            raw_event["raw_data"] = {}
                        raw_event["raw_data"]["detail"] = data["data"]
                        await self.repository.update_event_raw_data_detail(
                            event_id, data["data"]
                        )
                        if event_type == "SHOW":
                            await self._sync_show_members_dynamically(
                                event_id, raw_event, data["data"]
                            )
            except Exception as exc:
                logger.warning(f"Failed to fetch realtime data for {ref_code}: {exc}")

    async def _sync_show_members_dynamically(
        self, event_id: str, raw_event: dict, show_detail: dict
    ):
        jkt_members = show_detail.get("jkt48_member", [])
        bday_names = show_detail.get("birthday_member_name", [])
        if jkt_members and len(raw_event.get("members", [])) != len(jkt_members):
            active_members = await self.member_service.repository.find_all_active()
            name_to_member = {m["name"].lower(): m for m in active_members}
            member_ids = []
            resolved_members = []
            for jm in jkt_members:
                jm_name = jm.get("name", "").strip().lower()
                current_id = str(jm.get("member_id", ""))
                db_member = name_to_member.get(jm_name)
                if not db_member:
                    for key, m in name_to_member.items():
                        if jm_name in key or key in jm_name:
                            db_member = m
                            break
                legacy_id = db_member["id"] if db_member else current_id
                member_ids.append(legacy_id)
                if db_member:
                    resolved_members.append(db_member)
            seitansai_ids = []
            if bday_names:
                for name in bday_names:
                    name_lower = name.lower()
                    db_member = name_to_member.get(name_lower)
                    if not db_member:
                        for key, m in name_to_member.items():
                            if name_lower in key or key in name_lower:
                                db_member = m
                                break
                    if db_member:
                        seitansai_ids.append(db_member["id"])
            if member_ids:
                await self.repository.update_event_live_members(
                    event_id, member_ids, seitansai_ids
                )
                raw_event["members"] = resolved_members
                raw_event["memberIds"] = member_ids
                raw_event["seitansaiIds"] = seitansai_ids
                seitansai_names = [
                    m["name"] for m in resolved_members if m["id"] in seitansai_ids
                ]
                raw_event["seitansaiMembers"] = seitansai_names
                raw_event["totalMembers"] = len(member_ids)
