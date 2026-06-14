from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class EmailListRequest(BaseModel):
    query: str = ""
    max_results: int = Field(default=20, ge=1, le=100)


class SendEmailRequest(BaseModel):
    to: EmailStr
    subject: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1, max_length=50_000)


class DraftEmailRequest(SendEmailRequest):
    pass


class EmailResponse(BaseModel):
    id: str
    subject: str
    from_: str = Field(alias="from")
    to: str
    date: str
    snippet: str
    body: str
    body_html: str = ""
    label_ids: list[str]

    model_config = {"populate_by_name": True}
