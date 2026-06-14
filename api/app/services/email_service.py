import uuid

from sqlalchemy.ext.asyncio import AsyncSession

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
    client = await _get_client(db, user_id)
    return client.list_messages(max_results=max_results, query=query, page_token=page_token)


async def get_email(db: AsyncSession, user_id: uuid.UUID, message_id: str) -> dict:
    client = await _get_client(db, user_id)
    return client.get_message(message_id)


async def send_email(
    db: AsyncSession, user_id: uuid.UUID, to: str, subject: str, body: str
) -> dict:
    client = await _get_client(db, user_id)
    return client.send_message(to, subject, body)


async def draft_email(
    db: AsyncSession, user_id: uuid.UUID, to: str, subject: str, body: str
) -> dict:
    client = await _get_client(db, user_id)
    return client.draft_message(to, subject, body)


async def trash_email(db: AsyncSession, user_id: uuid.UUID, message_id: str) -> None:
    client = await _get_client(db, user_id)
    client.trash_message(message_id)
