from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status

from src.dependencies import get_setlists_service, require_admin, require_csrf_protection
from src.logging_config import create_logger
from src.setlists.schemas import (
    MessageResponse,
    SetlistCreateRequest,
    SetlistListResponse,
    SetlistOption,
    SetlistResponse,
    SetlistUpdateRequest,
)
from src.setlists.service import SetlistsService

router = APIRouter()
logger = create_logger("setlists", __name__)


@router.get("", response_model=SetlistListResponse)
async def get_setlists(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    type: Optional[str] = Query(None),
    active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    service: SetlistsService = Depends(get_setlists_service),
):
    return await service.get_all_setlists(skip, limit, type, active, search)


@router.get("/types", response_model=List[str])
async def get_types(service: SetlistsService = Depends(get_setlists_service)):
    return await service.get_types()


@router.get("/options", response_model=List[SetlistOption])
async def get_options(service: SetlistsService = Depends(get_setlists_service)):
    return await service.get_setlist_options()


@router.get("/id/{setlist_id}", response_model=SetlistResponse)
async def get_setlist_by_id(
    setlist_id: str,
    service: SetlistsService = Depends(get_setlists_service),
):
    return await service.get_setlist_by_id(setlist_id)


@router.get("/title/{title}", response_model=SetlistResponse)
async def get_setlist_by_title(
    title: str,
    service: SetlistsService = Depends(get_setlists_service),
):
    return await service.get_setlist_by_title(title)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=SetlistResponse,
    dependencies=[Depends(require_admin), Depends(require_csrf_protection)],
)
async def create_setlist(
    data: SetlistCreateRequest,
    service: SetlistsService = Depends(get_setlists_service),
):
    return await service.create_setlist(data)


@router.put(
    "/{setlist_id}",
    response_model=SetlistResponse,
    dependencies=[Depends(require_admin), Depends(require_csrf_protection)],
)
async def update_setlist(
    setlist_id: str,
    data: SetlistUpdateRequest,
    service: SetlistsService = Depends(get_setlists_service),
):
    return await service.update_setlist(setlist_id, data)


@router.delete(
    "/{setlist_id}",
    response_model=MessageResponse,
    dependencies=[Depends(require_admin), Depends(require_csrf_protection)],
)
async def delete_setlist(
    setlist_id: str,
    service: SetlistsService = Depends(get_setlists_service),
):
    return await service.delete_setlist(setlist_id)
