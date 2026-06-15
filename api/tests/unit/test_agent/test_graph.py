import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_run_agent_returns_response():
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    conv_id = uuid.uuid4()

    mock_memory = AsyncMock()
    mock_memory.retrieve.return_value = MagicMock(to_prompt_block=lambda: "No prior context.")
    mock_memory.store_episode = AsyncMock()

    mock_state = {
        "final_response": "You have 3 meetings today.",
        "messages": [],
        "is_complete": True,
        "tool_outputs": [],
        "memory_context": "",
        "user_id": str(user_id),
        "tenant_id": str(tenant_id),
        "conversation_id": str(conv_id),
    }

    with patch("app.agent.graph.build_graph") as mock_build:
        compiled = AsyncMock()
        compiled.ainvoke = AsyncMock(return_value=mock_state)
        mock_build.return_value = compiled

        from app.agent.graph import run_agent
        result = await run_agent(
            user_message="What are my meetings today?",
            user_id=user_id,
            tenant_id=tenant_id,
            conversation_id=conv_id,
            conversation_history=[],
            memory_manager=mock_memory,
        )

    assert result["final_response"] == "You have 3 meetings today."
    mock_memory.store_episode.assert_called_once()
