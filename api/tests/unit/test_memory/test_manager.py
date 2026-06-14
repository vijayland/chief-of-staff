import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_memory_manager_retrieve_returns_context(db):
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    with patch("app.memory.semantic.search_similar", new_callable=AsyncMock) as mock_sem, \
         patch("app.memory.procedural.get_style_context", new_callable=AsyncMock) as mock_proc, \
         patch("app.memory.episodic.get_recent_episodes", new_callable=AsyncMock) as mock_ep:

        mock_sem.return_value = []
        mock_proc.return_value = ["Use formal tone with clients"]
        mock_ep.return_value = []

        from app.memory.manager import MemoryManager
        mgr = MemoryManager(db, user_id, tenant_id)
        ctx = await mgr.retrieve("draft email to client")

    assert "formal tone" in ctx.to_prompt_block()


@pytest.mark.asyncio
async def test_memory_context_to_prompt_block():
    from app.memory.manager import MemoryContext
    ctx = MemoryContext(
        facts=["Project X is delayed"],
        style_hints=["Formal with clients"],
        recent_episodes=[],
    )
    block = ctx.to_prompt_block()
    assert "Project X is delayed" in block
    assert "Formal with clients" in block
