"""Celery task: sync Google Calendar for all connected users."""

import asyncio

import structlog
from sqlalchemy import select

from app.core.security import decrypt_value
from app.db.models.oauth_token import OAuthToken
from app.db.models.user import User
from app.db.session import AsyncSessionLocal
from app.integrations.google.calendar import GoogleCalendarClient
from app.integrations.google.oauth import build_credentials
from app.memory.manager import MemoryManager
from app.workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(name="app.workers.calendar_sync.sync_all_users_calendar", bind=True, max_retries=3)
def sync_all_users_calendar(self) -> None:
    asyncio.get_event_loop().run_until_complete(_sync_all())


async def _sync_all() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.is_active, User.google_connected)
        )
        users = result.scalars().all()
        for user in users:
            try:
                await _sync_user_calendar(db, user)
            except Exception as exc:
                logger.error("calendar_sync_failed", user_id=str(user.id), error=str(exc))
        await db.commit()


async def _sync_user_calendar(db, user: User) -> None:
    token_result = await db.execute(
        select(OAuthToken).where(OAuthToken.user_id == user.id, OAuthToken.provider == "google")
    )
    token = token_result.scalar_one_or_none()
    if not token:
        return

    access = decrypt_value(token.encrypted_access_token)
    refresh = decrypt_value(token.encrypted_refresh_token) if token.encrypted_refresh_token else None
    creds = build_credentials(access, refresh)

    gcal = GoogleCalendarClient(creds)
    events = gcal.list_events(days_ahead=14, max_results=30)

    if not events:
        return

    mem = MemoryManager(db, user.id, user.tenant_id)
    summary = "Upcoming calendar events for the next 14 days: " + ", ".join(
        f"{e['title']} on {e['start']}" for e in events[:10]
    )
    await mem.store_episode(summary, source="calendar")
    logger.info("calendar_sync_complete", user_id=str(user.id), events=len(events))
