"""Semantic memory — facts, preferences, and beliefs about the user's world."""

import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models.memory_node import MemoryNode, MemoryType
from app.integrations.llm.client import get_embedding


async def upsert_fact(
    db: AsyncSession,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    content: str,
    source: str = "chat",
    importance: float = 0.7,
) -> MemoryNode:
    """Store or update a semantic fact. Avoids exact duplicates."""
    embedding = await get_embedding(content)
    similar = await search_similar(db, user_id, content, top_k=1)

    if similar and similar[0][1] > 0.97:
        # Near-identical — update existing instead of duplicating
        existing = similar[0][0]
        existing.content = content
        existing.importance = max(existing.importance, importance)
        existing.access_count += 1
        await db.flush()
        return existing

    node = MemoryNode(
        user_id=user_id,
        tenant_id=tenant_id,
        memory_type=MemoryType.semantic,
        content=content,
        source=source,
        embedding=embedding,
        importance=importance,
    )
    db.add(node)
    await db.flush()
    return node


async def search_similar(
    db: AsyncSession,
    user_id: uuid.UUID,
    query: str,
    top_k: int = 5,
    memory_type: MemoryType | None = None,
    query_embedding: list[float] | None = None,
) -> list[tuple[MemoryNode, float]]:
    """Cosine similarity search via pgvector."""
    if query_embedding is None:
        query_embedding = await get_embedding(query)
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    type_filter = ""
    if memory_type:
        type_filter = f"AND memory_type = '{memory_type.value}'"

    rows = await db.execute(
        text(f"""
            SELECT id, 1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
            FROM memory_nodes
            WHERE user_id = :user_id
              AND embedding IS NOT NULL
              {type_filter}
              AND 1 - (embedding <=> CAST(:embedding AS vector)) > :threshold
            ORDER BY similarity DESC
            LIMIT :top_k
        """),
        {
            "embedding": embedding_str,
            "user_id": str(user_id),
            "threshold": settings.MEMORY_SIMILARITY_THRESHOLD,
            "top_k": top_k,
        },
    )
    pairs = rows.fetchall()

    if not pairs:
        return []

    ids = [str(row[0]) for row in pairs]
    scores = {str(row[0]): row[1] for row in pairs}

    nodes_result = await db.execute(
        select(MemoryNode).where(MemoryNode.id.in_(ids))
    )
    nodes = {str(n.id): n for n in nodes_result.scalars().all()}
    return [(nodes[nid], scores[nid]) for nid in ids if nid in nodes]
