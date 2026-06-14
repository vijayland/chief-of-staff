import uuid
import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Optional


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10_000)
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    reply: str


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: str

    model_config = {"from_attributes": True}

    @field_validator("id", mode="before")
    @classmethod
    def coerce_id(cls, v):
        return str(v)

    @field_validator("created_at", mode="before")
    @classmethod
    def coerce_created_at(cls, v):
        if isinstance(v, datetime.datetime):
            return v.isoformat()
        return str(v)


class ConversationResponse(BaseModel):
    id: str
    title: Optional[str] = None
    created_at: str

    model_config = {"from_attributes": True}

    @field_validator("id", mode="before")
    @classmethod
    def coerce_id(cls, v):
        return str(v)

    @field_validator("created_at", mode="before")
    @classmethod
    def coerce_created_at(cls, v):
        if isinstance(v, datetime.datetime):
            return v.isoformat()
        return str(v)


class ConversationDetailResponse(ConversationResponse):
    messages: list[MessageResponse] = []
