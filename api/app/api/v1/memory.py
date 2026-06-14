import uuid
from fastapi import APIRouter, Query
from app.dependencies import CurrentUser, DBSession
from app.schemas.memory import (
    MemoryResponse, MemorySearchRequest, MemorySearchResult, UpdateMemoryRequest
)
from app.services import memory_service
from app.db.models.memory_node import MemoryType

router = APIRouter(prefix="/memory", tags=["Memory"])


@router.get("", response_model=list[MemoryResponse], summary="List all memory nodes")
async def list_memories(
    current_user: CurrentUser,
    db: DBSession,
    memory_type: MemoryType | None = Query(default=None, description="Filter by type: semantic | procedural | episodic"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """
    Return all memory nodes for the current user.

    Memory types:
    - **semantic** — facts and preferences ("User dislikes 9 AM meetings")
    - **procedural** — communication style patterns ("Uses formal tone with clients")
    - **episodic** — conversation episode summaries

    Use this endpoint to **verify the memory system is working** after chatting with the agent.
    """
    nodes = await memory_service.list_memories(db, current_user.id, memory_type, limit, offset)
    return [
        MemoryResponse(
            id=str(n.id),
            memory_type=n.memory_type,
            content=n.content,
            source=n.source,
            importance=n.importance,
            access_count=n.access_count,
            created_at=n.created_at.isoformat(),
        )
        for n in nodes
    ]


@router.post("/search", response_model=list[MemorySearchResult],
             summary="Semantic search over memory")
async def search_memories(body: MemorySearchRequest, current_user: CurrentUser, db: DBSession):
    """
    Search the memory graph using vector similarity (pgvector cosine distance).

    Returns the most relevant memories for the given query, ranked by similarity score (0–1).

    Example query: `"What do I prefer for morning meetings?"`
    """
    results = await memory_service.search_memories(db, current_user.id, body.query, body.top_k)
    return [
        MemorySearchResult(
            memory=MemoryResponse(
                id=str(node.id),
                memory_type=node.memory_type,
                content=node.content,
                source=node.source,
                importance=node.importance,
                access_count=node.access_count,
                created_at=node.created_at.isoformat(),
            ),
            similarity=round(score, 4),
        )
        for node, score in results
    ]


@router.patch("/{memory_id}", response_model=MemoryResponse,
              summary="Update memory importance score")
async def update_memory(
    memory_id: str, body: UpdateMemoryRequest, current_user: CurrentUser, db: DBSession
):
    """
    Adjust the importance score of a memory node (0.0 – 1.0).

    Higher importance = more likely to be surfaced during retrieval.
    Preferences set by the user typically have `importance=0.85`.
    """
    node = await memory_service.update_memory_importance(
        db, current_user.id, uuid.UUID(memory_id), body.importance
    )
    return MemoryResponse(
        id=str(node.id),
        memory_type=node.memory_type,
        content=node.content,
        source=node.source,
        importance=node.importance,
        access_count=node.access_count,
        created_at=node.created_at.isoformat(),
    )


@router.delete("/{memory_id}", status_code=204, summary="Delete a memory node")
async def delete_memory(memory_id: str, current_user: CurrentUser, db: DBSession):
    """Permanently delete a memory node. The agent will no longer recall this information."""
    await memory_service.delete_memory(db, current_user.id, uuid.UUID(memory_id))
