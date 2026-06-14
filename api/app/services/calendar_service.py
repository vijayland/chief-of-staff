import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.auth_service import get_google_credentials
from app.integrations.google.calendar import GoogleCalendarClient
from app.core.exceptions import BadRequestError


async def _get_client(db: AsyncSession, user_id: uuid.UUID) -> GoogleCalendarClient:
    creds = await get_google_credentials(db, user_id)
    if not creds:
        raise BadRequestError("Google account not connected. Please connect via /auth/google.")
    return GoogleCalendarClient(creds)


async def list_events(
    db: AsyncSession, user_id: uuid.UUID, days_ahead: int = 7, max_results: int = 20
) -> list[dict]:
    client = await _get_client(db, user_id)
    return client.list_events(days_ahead=days_ahead, max_results=max_results)


async def create_event(
    db: AsyncSession,
    user_id: uuid.UUID,
    title: str,
    start: datetime,
    end: datetime,
    description: str = "",
    attendees: list[str] | None = None,
) -> dict:
    client = await _get_client(db, user_id)
    return client.create_event(title, start, end, description, attendees)


async def update_event(
    db: AsyncSession, user_id: uuid.UUID, event_id: str, updates: dict
) -> dict:
    client = await _get_client(db, user_id)
    return client.update_event(event_id, updates)


async def delete_event(db: AsyncSession, user_id: uuid.UUID, event_id: str) -> None:
    client = await _get_client(db, user_id)
    client.delete_event(event_id)
