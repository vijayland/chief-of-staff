import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import (
    get_calendar,
    invalidate_calendar,
    set_calendar,
)
from app.core.exceptions import BadRequestError
from app.integrations.google.calendar import GoogleCalendarClient
from app.services.auth_service import get_google_credentials


async def _get_client(db: AsyncSession, user_id: uuid.UUID) -> GoogleCalendarClient:
    creds = await get_google_credentials(db, user_id)
    if not creds:
        raise BadRequestError("Google account not connected. Please connect via /auth/google.")
    return GoogleCalendarClient(creds)


async def list_events(
    db: AsyncSession, user_id: uuid.UUID, days_ahead: int = 7, max_results: int = 20
) -> list[dict]:
    """
    Cache flow:
      1. Check Redis — TTL 5 min (fresh enough for scheduling decisions)
      2. Miss → Google Calendar API → cache result
    Invalidated: on create / update / delete event.
    """
    uid = str(user_id)

    cached = await get_calendar(uid, days_ahead)
    if cached is not None:
        return cached

    client = await _get_client(db, user_id)
    events = client.list_events(days_ahead=days_ahead, max_results=max_results)
    await set_calendar(uid, days_ahead, events)
    return events


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
    result = client.create_event(title, start, end, description, attendees)
    # Calendar changed → invalidate all cached views for this user
    await invalidate_calendar(str(user_id))
    return result


async def update_event(
    db: AsyncSession, user_id: uuid.UUID, event_id: str, updates: dict
) -> dict:
    client = await _get_client(db, user_id)
    result = client.update_event(event_id, updates)
    await invalidate_calendar(str(user_id))
    return result


async def delete_event(db: AsyncSession, user_id: uuid.UUID, event_id: str) -> None:
    client = await _get_client(db, user_id)
    client.delete_event(event_id)
    await invalidate_calendar(str(user_id))
