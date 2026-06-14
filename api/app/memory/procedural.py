"""Procedural memory — communication style, tone, and behavioural patterns."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.memory_node import MemoryNode, MemoryType
from app.memory.semantic import search_similar


async def record_style_pattern(
    db: AsyncSession,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    pattern: str,
    source: str = "action",
) -> MemoryNode:
    """Record a communication or behavioural pattern.

    Patterns are stored as semantic memories tagged procedural so they surface
    when the agent needs to decide HOW to act (tone, format, timing).
    """
    node = MemoryNode(
        user_id=user_id,
        tenant_id=tenant_id,
        memory_type=MemoryType.procedural,
        content=pattern,
        source=source,
        importance=0.8,
    )
    from app.integrations.llm.client import get_embedding
    node.embedding = await get_embedding(pattern)
    db.add(node)
    await db.flush()
    return node


async def get_style_context(
    db: AsyncSession,
    user_id: uuid.UUID,
    query: str,
    top_k: int = 3,
    query_embedding: list[float] | None = None,
) -> list[str]:
    """Retrieve relevant style patterns for a given action."""
    results = await search_similar(
        db, user_id, query, top_k=top_k, memory_type=MemoryType.procedural,
        query_embedding=query_embedding,
    )
    return [node.content for node, _ in results]
