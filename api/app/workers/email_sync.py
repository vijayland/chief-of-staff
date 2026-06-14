"""Celery task: sync Gmail for all connected users and extract memories."""

import asyncio
import json

import structlog
from sqlalchemy import select

from app.agent.prompts.system import MEMORY_EXTRACTION_SYSTEM
from app.core.security import decrypt_value
from app.db.models.oauth_token import OAuthToken
from app.db.models.user import User
from app.db.session import AsyncSessionLocal
from app.integrations.google.gmail import GmailClient
from app.integrations.google.oauth import build_credentials
from app.integrations.llm.client import chat_completion
from app.memory.manager import MemoryManager
from app.workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(name="app.workers.email_sync.sync_all_users_email", bind=True, max_retries=3)
def sync_all_users_email(self) -> None:
    asyncio.get_event_loop().run_until_complete(_sync_all())


async def _sync_all() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.is_active, User.google_connected)
        )
        users = result.scalars().all()
        for user in users:
            try:
                await _sync_user_email(db, user)
            except Exception as exc:
                logger.error("email_sync_failed", user_id=str(user.id), error=str(exc))
        await db.commit()


async def _sync_user_email(db, user: User) -> None:
    token_result = await db.execute(
        select(OAuthToken).where(OAuthToken.user_id == user.id, OAuthToken.provider == "google")
    )
    token = token_result.scalar_one_or_none()
    if not token:
        return

    access = decrypt_value(token.encrypted_access_token)
    refresh = decrypt_value(token.encrypted_refresh_token) if token.encrypted_refresh_token else None
    creds = build_credentials(access, refresh)

    gmail = GmailClient(creds)
    messages = gmail.list_messages(max_results=20, query="is:unread")

    if not messages:
        return

    mem = MemoryManager(db, user.id, user.tenant_id)
    email_text = "\n\n---\n\n".join(
        f"From: {m['from']}\nSubject: {m['subject']}\n{m['body'][:500]}"
        for m in messages[:10]
    )

    # Extract facts from emails automatically
    try:
        response = await chat_completion(
            messages=[{"role": "user", "content": f"Emails:\n{email_text}"}],
            system=MEMORY_EXTRACTION_SYSTEM,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        extracted = json.loads(raw)

        for fact in extracted.get("facts", []):
            await mem.store_fact(fact, source="email", importance=0.75)

        for pref in extracted.get("preferences", []):
            await mem.store_fact(pref, source="email", importance=0.85)

        logger.info(
            "email_sync_complete",
            user_id=str(user.id),
            emails=len(messages),
            facts=len(extracted.get("facts", [])),
        )
    except Exception as exc:
        logger.warning("email_memory_extraction_failed", user_id=str(user.id), error=str(exc))
