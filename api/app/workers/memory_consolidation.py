"""Celery task: nightly memory consolidation — prune low-importance, duplicate memories."""

import asyncio
import structlog
from app.workers.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.db.models.memory_node import MemoryNode
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

MIN_IMPORTANCE = 0.2
MAX_MEMORIES_PER_USER = 1000


@celery_app.task(name="app.workers.memory_consolidation.consolidate_all_users", bind=True)
def consolidate_all_users(self) -> None:
    asyncio.get_event_loop().run_until_complete(_consolidate_all())


async def _consolidate_all() -> None:
    async with AsyncSessionLocal() as db:
        # Get distinct user IDs that have memories
        from sqlalchemy import distinct
        from app.db.models.user import User
        result = await db.execute(select(distinct(MemoryNode.user_id)))
        user_ids = [row[0] for row in result.fetchall()]

        for user_id in user_ids:
            try:
                await _consolidate_user(db, user_id)
            except Exception as exc:
                logger.error("consolidation_failed", user_id=str(user_id), error=str(exc))

        await db.commit()


async def _consolidate_user(db: AsyncSession, user_id) -> None:
    # Delete very low importance memories
    await db.execute(
        delete(MemoryNode).where(
            MemoryNode.user_id == user_id,
            MemoryNode.importance < MIN_IMPORTANCE,
            MemoryNode.access_count == 0,
        )
    )

    # If user exceeds MAX_MEMORIES, delete oldest lowest-importance ones
    count_result = await db.execute(
        select(MemoryNode.id)
        .where(MemoryNode.user_id == user_id)
        .order_by(MemoryNode.importance.asc(), MemoryNode.access_count.asc(), MemoryNode.created_at.asc())
    )
    all_ids = [row[0] for row in count_result.fetchall()]

    if len(all_ids) > MAX_MEMORIES_PER_USER:
        to_delete = all_ids[: len(all_ids) - MAX_MEMORIES_PER_USER]
        await db.execute(delete(MemoryNode).where(MemoryNode.id.in_(to_delete)))
        logger.info("memories_pruned", user_id=str(user_id), pruned=len(to_delete))
