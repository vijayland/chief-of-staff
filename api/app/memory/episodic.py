"""Episodic memory — stores raw conversation summaries per user."""

import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.memory_node import MemoryNode, MemoryType
from app.integrations.llm.client import get_embedding


async def store_episode(
    db: AsyncSession,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    content: str,
    source: str = "chat",
) -> MemoryNode:
    embedding = await get_embedding(content)
    node = MemoryNode(
        user_id=user_id,
        tenant_id=tenant_id,
        memory_type=MemoryType.episodic,
        content=content,
        source=source,
        embedding=embedding,
        importance=0.4,
    )
    db.add(node)
    await db.flush()
    return node


async def get_recent_episodes(
    db: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 10,
) -> list[MemoryNode]:
    result = await db.execute(
        select(MemoryNode)
        .where(
            MemoryNode.user_id == user_id,
            MemoryNode.memory_type == MemoryType.episodic,
        )
        .order_by(desc(MemoryNode.created_at))
        .limit(limit)
    )
    return list(result.scalars().all())
