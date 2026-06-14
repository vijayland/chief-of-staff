from fastapi import APIRouter, Query

from app.dependencies import CurrentUser, DBSession
from app.schemas.email import DraftEmailRequest, SendEmailRequest
from app.services import email_service

router = APIRouter(prefix="/email", tags=["Email"])


@router.get("", response_model=dict)
async def list_emails(
    current_user: CurrentUser,
    db: DBSession,
    query: str = Query(default="", description="Gmail search query"),
    max_results: int = Query(default=20, ge=1, le=100),
    page_token: str | None = Query(default=None),
):
    return await email_service.list_emails(db, current_user.id, query, max_results, page_token)


@router.get("/{message_id}", response_model=dict)
async def get_email(message_id: str, current_user: CurrentUser, db: DBSession):
    return await email_service.get_email(db, current_user.id, message_id)


@router.post("/send", response_model=dict, status_code=201)
async def send_email(body: SendEmailRequest, current_user: CurrentUser, db: DBSession):
    return await email_service.send_email(db, current_user.id, body.to, body.subject, body.body)


@router.post("/draft", response_model=dict, status_code=201)
async def draft_email(body: DraftEmailRequest, current_user: CurrentUser, db: DBSession):
    return await email_service.draft_email(db, current_user.id, body.to, body.subject, body.body)


@router.delete("/{message_id}", status_code=204)
async def trash_email(message_id: str, current_user: CurrentUser, db: DBSession):
    await email_service.trash_email(db, current_user.id, message_id)
