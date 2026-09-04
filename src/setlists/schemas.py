from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class SetlistBase(BaseModel):
    setlistId: str
    imageUrl: str
    title: str
    titleJapanese: Optional[str] = None
    description: str
    type: str
    active: bool = False
    songs: Optional[List[str]] = []


class SetlistOption(BaseModel):
    setlistId: str
    title: str
    type: str
    active: bool
    imageUrl: str


class SetlistResponse(SetlistBase):
    pass


class SetlistListResponse(BaseModel):
    total: int
    setlists: List[SetlistResponse]


class SetlistCreateRequest(BaseModel):
    imageUrl: str = Field(max_length=500)
    title: str = Field(max_length=100)
    titleJapanese: Optional[str] = Field(default=None, max_length=100)
    description: str = Field(max_length=1000)
    type: Literal["setlist", "event"]
    active: bool = False
    songs: Optional[List[str]] = []


class SetlistUpdateRequest(BaseModel):
    imageUrl: Optional[str] = Field(default=None, max_length=500)
    title: Optional[str] = Field(default=None, max_length=100)
    titleJapanese: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=1000)
    type: Optional[Literal["setlist", "event"]] = None
    active: Optional[bool] = None
    songs: Optional[List[str]] = None


class MessageResponse(BaseModel):
    message: str
