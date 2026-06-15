"""Chat / Conversations API integration tests."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.conversation import Conversation


async def _create_conversation(db: AsyncSession, user_id, tenant_id, title="Test Chat"):
    conv = Conversation(
        user_id=user_id,
        tenant_id=tenant_id,
        title=title,
        is_active=True,
    )
    db.add(conv)
    await db.flush()
    return conv


@pytest.mark.asyncio
async def test_list_conversations_empty(client, auth_headers):
    resp = await client.get("/api/v1/chat/conversations", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_conversations_returns_user_conversations(client, db, auth_headers, user, tenant):
    conv = await _create_conversation(db, user.id, tenant.id, title="Meeting notes")
    await db.flush()

    resp = await client.get("/api/v1/chat/conversations", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Meeting notes"
    assert data[0]["id"] == str(conv.id)


@pytest.mark.asyncio
async def test_list_conversations_requires_auth(client):
    resp = await client.get("/api/v1/chat/conversations")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_conversation_detail(client, db, auth_headers, user, tenant):
    conv = await _create_conversation(db, user.id, tenant.id, title="Calendar check")
    await db.flush()

    resp = await client.get(f"/api/v1/chat/conversations/{conv.id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(conv.id)
    assert data["title"] == "Calendar check"


@pytest.mark.asyncio
async def test_get_conversation_not_found(client, auth_headers):
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/chat/conversations/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_conversation(client, db, auth_headers, user, tenant):
    conv = await _create_conversation(db, user.id, tenant.id)
    await db.flush()

    resp = await client.delete(f"/api/v1/chat/conversations/{conv.id}", headers=auth_headers)
    assert resp.status_code == 204

    # Should no longer appear in list
    list_resp = await client.get("/api/v1/chat/conversations", headers=auth_headers)
    ids = [c["id"] for c in list_resp.json()]
    assert str(conv.id) not in ids


@pytest.mark.asyncio
async def test_delete_conversation_not_found(client, auth_headers):
    fake_id = uuid.uuid4()
    resp = await client.delete(f"/api/v1/chat/conversations/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_conversations_isolated_between_users(client, db, auth_headers, user, tenant):
    """Another user's conversation must not appear in our list."""
    from app.db.models.user import User
    other_user = User(tenant_id=tenant.id, email="other@example.com", full_name="Other", hashed_password="x")
    db.add(other_user)
    await db.flush()

    await _create_conversation(db, other_user.id, tenant.id, title="Other user chat")
    await _create_conversation(db, user.id, tenant.id, title="My chat")
    await db.flush()

    resp = await client.get("/api/v1/chat/conversations", headers=auth_headers)
    titles = [c["title"] for c in resp.json()]
    assert "My chat" in titles
    assert "Other user chat" not in titles
