from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class CreateEventRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    start: datetime
    end: datetime
    description: str = ""
    attendees: list[str] = []


class UpdateEventRequest(BaseModel):
    title: Optional[str] = None
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    description: Optional[str] = None


class EventResponse(BaseModel):
    id: str
    title: str
    description: str
    start: str
    end: str
    attendees: list[str]
    location: str
    html_link: str
    status: Optional[str]
