import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_send_message_creates_conversation(client, auth_headers):
    with patch("app.services.chat_service.run_agent", new_callable=AsyncMock) as mock_agent:
        mock_agent.return_value = {
            "final_response": "Hello! How can I help you today?",
            "messages": [],
        }
        resp = await client.post(
            "/api/v1/chat",
            json={"message": "Hello"},
            headers=auth_headers,
        )

    assert resp.status_code == 200
    body = resp.json()
    assert "conversation_id" in body
    assert "reply" in body
    assert body["reply"] == "Hello! How can I help you today?"


@pytest.mark.asyncio
async def test_list_conversations(client, auth_headers):
    resp = await client.get("/api/v1/chat/conversations", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
