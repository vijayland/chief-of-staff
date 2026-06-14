import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.db.models.memory_node import MemoryNode, MemoryType
from app.memory.semantic import search_similar
from app.core.exceptions import NotFoundError


async def list_memories(
    db: AsyncSession,
    user_id: uuid.UUID,
    memory_type: MemoryType | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[MemoryNode]:
    q = select(MemoryNode).where(MemoryNode.user_id == user_id)
    if memory_type:
        q = q.where(MemoryNode.memory_type == memory_type)
    q = q.order_by(MemoryNode.importance.desc(), MemoryNode.created_at.desc())
    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


async def search_memories(
    db: AsyncSession, user_id: uuid.UUID, query: str, top_k: int = 10
) -> list[tuple[MemoryNode, float]]:
    return await search_similar(db, user_id, query, top_k=top_k)


async def delete_memory(db: AsyncSession, user_id: uuid.UUID, memory_id: uuid.UUID) -> None:
    result = await db.execute(
        select(MemoryNode).where(MemoryNode.id == memory_id, MemoryNode.user_id == user_id)
    )
    node = result.scalar_one_or_none()
    if not node:
        raise NotFoundError("Memory")
    await db.delete(node)
    await db.flush()


async def update_memory_importance(
    db: AsyncSession, user_id: uuid.UUID, memory_id: uuid.UUID, importance: float
) -> MemoryNode:
    result = await db.execute(
        select(MemoryNode).where(MemoryNode.id == memory_id, MemoryNode.user_id == user_id)
    )
    node = result.scalar_one_or_none()
    if not node:
        raise NotFoundError("Memory")
    node.importance = max(0.0, min(1.0, importance))
    await db.flush()
    return node
