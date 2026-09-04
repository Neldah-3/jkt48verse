import re
from datetime import datetime
from typing import List, Optional

from src.config import Settings
from src.logging_config import create_logger
from src.members.constants import Info
from src.members.exceptions import MemberFetchError, MemberNotFoundError
from src.members.repository import MemberRepository
from src.members.schemas import (
    BirthdayResponse,
    MemberCreateRequest,
    MemberDetailResponse,
    MemberListResponse,
    MemberResponse,
    MemberUpdateRequest,
    MessageResponse,
)
from src.schemas import PaginationMeta

logger = create_logger("members_service", __name__)


class MemberService:
    def __init__(self, repository: MemberRepository, config: Settings):
        self.repository = repository
        self.config = config

    async def get_all_members(
        self,
        page: int = 1,
        limit: int = 20,
        generation: Optional[str] = None,
        search: Optional[str] = None,
        include_inactive: bool = False,
    ) -> MemberListResponse:
        try:
            skip = (page - 1) * limit
            members = await self.repository.find_all(
                skip, limit, generation, search, include_inactive
            )
            total = await self.repository.count(generation, search, include_inactive)
            member_responses = [MemberResponse(**member) for member in members]
            last_page = (total + limit - 1) // limit if limit > 0 else 1
            if last_page < 1:
                last_page = 1
            next_page = page + 1 if page < last_page else None
            return MemberListResponse(
                data=member_responses,
                meta=PaginationMeta(
                    current_page=page,
                    last_page=last_page,
                    total_data=total,
                    per_page=limit,
                    next_page=next_page,
                ),
            )
        except Exception as e:
            logger.exception(f"Error fetching members: {str(e)}")
            raise MemberFetchError()

    async def get_member_by_id(self, member_id: str) -> MemberDetailResponse:
        try:
            member = await self.repository.find_by_id(member_id)
            if not member:
                raise MemberNotFoundError()
            return MemberDetailResponse(
                member=MemberResponse(**member), detail=Info.MEMBER_FOUND
            )
        except MemberNotFoundError:
            raise
        except Exception as e:
            logger.exception(f"Error fetching member {member_id}: {str(e)}")
            raise MemberFetchError()

    async def get_member_by_nickname(self, nickname: str) -> MemberDetailResponse:
        try:
            member = await self.repository.find_by_nickname(nickname)
            if not member:
                raise MemberNotFoundError()
            return MemberDetailResponse(
                member=MemberResponse(**member), detail=Info.MEMBER_FOUND
            )
        except MemberNotFoundError:
            raise
        except Exception as e:
            logger.exception(f"Error fetching member {nickname}: {str(e)}")
            raise MemberFetchError()

    async def get_member_by_name(self, name: str) -> MemberDetailResponse:
        try:
            clean_name = re.sub(r"\(.*?\)|JKT48|Trainee|-.*", "", name).strip()
            member = await self.repository.find_by_name(clean_name)
            if not member:
                search_results = await self.repository.find_all(limit=1, search=clean_name)
                if search_results:
                    member = search_results[0]
                else:
                    raise MemberNotFoundError()
            return MemberDetailResponse(
                member=MemberResponse(**member), detail=Info.MEMBER_FOUND
            )
        except MemberNotFoundError:
            raise
        except Exception as e:
            logger.exception(f"Error fetching member {name}: {str(e)}")
            raise MemberFetchError()

    async def get_generations(self) -> List[str]:
        try:
            return await self.repository.get_generations()
        except Exception as e:
            logger.exception(f"Error fetching generations: {str(e)}")
            raise MemberFetchError()

    async def create_member(self, data: MemberCreateRequest) -> MemberResponse:
        try:
            next_id = await self.repository.get_next_id()
            now = datetime.now()
            member_dict = data.model_dump(exclude_none=True)
            if "name" in member_dict:
                member_dict["member_code"] = (
                    member_dict["name"].upper().strip().replace(" ", "_")
                )
            member_data = {"id": str(next_id), **member_dict, "createdAt": now, "updatedAt": now}
            member = await self.repository.insert_one(member_data)
            return MemberResponse(**member)
        except Exception as e:
            logger.exception(f"Error creating member: {str(e)}")
            raise MemberFetchError()

    async def update_member(self, member_id: str, data: MemberUpdateRequest) -> MemberResponse:
        try:
            existing = await self.repository.find_by_id(member_id)
            if not existing:
                raise MemberNotFoundError()
            update_data = data.model_dump(exclude_none=True)
            if update_data:
                if "name" in update_data:
                    update_data["member_code"] = (
                        update_data["name"].upper().strip().replace(" ", "_")
                    )
                update_data["updatedAt"] = datetime.now()
                member = await self.repository.update_one(member_id, update_data)
            else:
                member = existing
            return MemberResponse(**member)
        except MemberNotFoundError:
            raise
        except Exception as e:
            logger.exception(f"Error updating member {member_id}: {str(e)}")
            raise MemberFetchError()

    async def delete_member(self, member_id: str) -> MessageResponse:
        try:
            existing = await self.repository.find_by_id(member_id)
            if not existing:
                raise MemberNotFoundError()
            deleted = await self.repository.delete_one(member_id)
            if not deleted:
                raise MemberFetchError()
            return MessageResponse(message=Info.MEMBER_DELETED)
        except MemberNotFoundError:
            raise
        except Exception as e:
            logger.exception(f"Error deleting member {member_id}: {str(e)}")
            raise MemberFetchError()

    async def get_upcoming_birthdays(self) -> List[BirthdayResponse]:
        try:
            members = await self.repository.find_all_active()
            upcoming = []
            today = datetime.now().date()
            months_map = {
                "Januari": 1,
                "Februari": 2,
                "Maret": 3,
                "April": 4,
                "Mei": 5,
                "Juni": 6,
                "Juli": 7,
                "Agustus": 8,
                "September": 9,
                "Oktober": 10,
                "November": 11,
                "Desember": 12,
            }
            for member in members:
                if not member.get("birthdate"):
                    continue
                try:
                    parts = member["birthdate"].split()
                    if len(parts) != 3:
                        continue
                    day = int(parts[0])
                    month_str = parts[1]
                    year = int(parts[2])
                    if month_str not in months_map:
                        continue
                    month = months_map[month_str]
                    current_year_birthday = datetime(today.year, month, day).date()
                    next_birthday = current_year_birthday
                    if current_year_birthday < today:
                        next_birthday = datetime(today.year + 1, month, day).date()
                    days_until = (next_birthday - today).days
                    if 0 <= days_until <= 30:
                        upcoming.append(
                            BirthdayResponse(
                                id=member.get("id", ""),
                                name=member.get("name", ""),
                                active=member.get("active", True),
                                img=member.get("img"),
                                birthdate=member.get("birthdate", ""),
                                days_until=days_until,
                                age=next_birthday.year - year,
                                member_type=member.get("member_type", "JKT48"),
                            )
                        )
                except (ValueError, TypeError) as e:
                    logger.warning(
                        f"Error parsing birthdate for member {member.get('name')}: {e}"
                    )
                    continue
            upcoming.sort(key=lambda x: x.days_until)
            return upcoming
        except Exception as e:
            logger.exception(f"Error fetching upcoming birthdays: {str(e)}")
            raise MemberFetchError()

    async def get_birthdays_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[dict]:
        try:
            members = await self.repository.find_all_active()
            results = []
            months_map = {
                "Januari": 1,
                "Februari": 2,
                "Maret": 3,
                "April": 4,
                "Mei": 5,
                "Juni": 6,
                "Juli": 7,
                "Agustus": 8,
                "September": 9,
                "Oktober": 10,
                "November": 11,
                "Desember": 12,
            }
            for member in members:
                if not member.get("birthdate"):
                    continue
                try:
                    parts = member["birthdate"].split()
                    if len(parts) != 3:
                        continue
                    day = int(parts[0])
                    month_str = parts[1]
                    if month_str not in months_map:
                        continue
                    month = months_map[month_str]
                    for year_to_check in range(start_date.year, end_date.year + 1):
                        try:
                            birthday_date = datetime(year_to_check, month, day)
                            if start_date <= birthday_date <= end_date:
                                results.append(
                                    {
                                        "id": member.get("id", ""),
                                        "name": member.get("name", ""),
                                        "date": birthday_date,
                                        "img": member.get("img"),
                                        "active": member.get("active", True),
                                        "member_type": member.get("member_type", "JKT48"),
                                    }
                                )
                        except ValueError:
                            continue
                except (ValueError, TypeError) as e:
                    logger.warning(
                        f"Error parsing birthdate for member {member.get('name')}: {e}"
                    )
                    continue
            return results
        except Exception as e:
            logger.exception(f"Error fetching birthdays by range: {str(e)}")
            return []
