from datetime import datetime

from pydantic import BaseModel, Field


class CreateEventRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    start: datetime
    end: datetime
    description: str = ""
    attendees: list[str] = []


class UpdateEventRequest(BaseModel):
    title: str | None = None
    start: datetime | None = None
    end: datetime | None = None
    description: str | None = None


class EventResponse(BaseModel):
    id: str
    title: str
    description: str
    start: str
    end: str
    attendees: list[str]
    location: str
    html_link: str
    status: str | None
