from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from src.config import Settings
from src.logging_config import create_logger
from src.setlists.constants import Info
from src.setlists.exceptions import SetlistFetchError, SetlistNotFoundError
from src.setlists.repository import SetlistsRepository
from src.setlists.schemas import (
    MessageResponse,
    SetlistCreateRequest,
    SetlistListResponse,
    SetlistOption,
    SetlistResponse,
    SetlistUpdateRequest,
)

logger = create_logger("setlists_service", __name__)


class SetlistsService:
    def __init__(self, repository: SetlistsRepository, config: Settings):
        self.repository = repository
        self.config = config

    async def get_all_setlists(
        self,
        skip: int = 0,
        limit: int = 100,
        setlist_type: Optional[str] = None,
        active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> SetlistListResponse:
        try:
            setlists = await self.repository.find_all(
                skip, limit, setlist_type, active, search
            )
            total = await self.repository.count(setlist_type, active, search)
            return SetlistListResponse(
                total=total, setlists=[SetlistResponse(**s) for s in setlists]
            )
        except Exception as e:
            logger.exception(f"Error fetching setlists: {str(e)}")
            raise SetlistFetchError()

    async def get_setlist_by_id(self, setlist_id: str) -> SetlistResponse:
        try:
            setlist = await self.repository.find_by_setlist_id(setlist_id)
            if not setlist:
                raise SetlistNotFoundError()
            return SetlistResponse(**setlist)
        except SetlistNotFoundError:
            raise
        except Exception as e:
            logger.exception(f"Error fetching setlist {setlist_id}: {str(e)}")
            raise SetlistFetchError()

    async def get_setlist_by_title(self, title: str) -> SetlistResponse:
        try:
            setlist = await self.repository.find_by_title(title)
            if not setlist:
                raise SetlistNotFoundError()
            return SetlistResponse(**setlist)
        except SetlistNotFoundError:
            raise
        except Exception as e:
            logger.exception(f"Error fetching setlist {title}: {str(e)}")
            raise SetlistFetchError()

    async def get_types(self) -> List[str]:
        try:
            return await self.repository.get_types()
        except Exception as e:
            logger.exception(f"Error fetching setlist types: {str(e)}")
            raise SetlistFetchError()

    async def get_setlist_options(self) -> List[SetlistOption]:
        try:
            setlists = await self.repository.find_all(limit=200, active=True)
            return [SetlistOption(**s) for s in setlists]
        except Exception as e:
            logger.exception(f"Error fetching setlist options: {str(e)}")
            raise SetlistFetchError()

    async def create_setlist(self, data: SetlistCreateRequest) -> SetlistResponse:
        try:
            payload = data.model_dump()
            payload["setlistId"] = str(uuid4())
            payload["createdAt"] = datetime.now()
            created = await self.repository.insert_one(payload)
            return SetlistResponse(**created)
        except Exception as e:
            logger.exception(f"Error creating setlist: {str(e)}")
            raise SetlistFetchError()

    async def update_setlist(
        self, setlist_id: str, data: SetlistUpdateRequest
    ) -> SetlistResponse:
        try:
            existing = await self.repository.find_by_setlist_id(setlist_id)
            if not existing:
                raise SetlistNotFoundError()
            update_data = data.model_dump(exclude_none=True)
            updated = await self.repository.update_one(setlist_id, update_data)
            return SetlistResponse(**updated)
        except SetlistNotFoundError:
            raise
        except Exception as e:
            logger.exception(f"Error updating setlist {setlist_id}: {str(e)}")
            raise SetlistFetchError()

    async def delete_setlist(self, setlist_id: str) -> MessageResponse:
        try:
            existing = await self.repository.find_by_setlist_id(setlist_id)
            if not existing:
                raise SetlistNotFoundError()
            await self.repository.delete_one(setlist_id)
            return MessageResponse(message=Info.SETLIST_DELETED)
        except SetlistNotFoundError:
            raise
        except Exception as e:
            logger.exception(f"Error deleting setlist {setlist_id}: {str(e)}")
            raise SetlistFetchError()
