import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import (
    get_emails,
    invalidate_emails,
    set_emails,
)
from app.core.exceptions import BadRequestError
from app.integrations.google.gmail import GmailClient
from app.services.auth_service import get_google_credentials


async def _get_client(db: AsyncSession, user_id: uuid.UUID) -> GmailClient:
    creds = await get_google_credentials(db, user_id)
    if not creds:
        raise BadRequestError("Google account not connected. Please connect via /auth/google.")
    return GmailClient(creds)


async def list_emails(
    db: AsyncSession,
    user_id: uuid.UUID,
    query: str = "",
    max_results: int = 20,
    page_token: str | None = None,
) -> dict:
    """
    Cache flow:
      1. Check Redis — TTL 2 min (emails change frequently)
      2. Miss → Gmail API → cache result
    Not cached when page_token is present (paginated results vary).
    Invalidated: on send / draft / trash.
    """
    uid = str(user_id)

    # Only cache first-page results (page_token = subsequent pages, skip cache)
    if not page_token:
        cached = await get_emails(uid, query, max_results)
        if cached is not None:
            return cached

    client = await _get_client(db, user_id)
    result = client.list_messages(max_results=max_results, query=query, page_token=page_token)

    if not page_token:
        await set_emails(uid, query, max_results, result)

    return result


async def get_email(db: AsyncSession, user_id: uuid.UUID, message_id: str) -> dict:
    client = await _get_client(db, user_id)
    return client.get_message(message_id)


async def send_email(
    db: AsyncSession, user_id: uuid.UUID, to: str, subject: str, body: str
) -> dict:
    client = await _get_client(db, user_id)
    result = client.send_message(to, subject, body)
    await invalidate_emails(str(user_id))
    return result


async def draft_email(
    db: AsyncSession, user_id: uuid.UUID, to: str, subject: str, body: str
) -> dict:
    client = await _get_client(db, user_id)
    result = client.draft_message(to, subject, body)
    await invalidate_emails(str(user_id))
    return result


async def trash_email(db: AsyncSession, user_id: uuid.UUID, message_id: str) -> None:
    client = await _get_client(db, user_id)
    client.trash_message(message_id)
    await invalidate_emails(str(user_id))
