"""Memory API integration tests."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.memory_node import MemoryNode, MemoryType


async def _create_memory(db: AsyncSession, user_id, tenant_id, content="Test fact", importance=0.7):
    node = MemoryNode(
        user_id=user_id,
        tenant_id=tenant_id,
        memory_type=MemoryType.semantic,
        content=content,
        source="test",
        importance=importance,
    )
    db.add(node)
    await db.flush()
    return node


@pytest.mark.asyncio
async def test_list_memories_empty(client, auth_headers):
    resp = await client.get("/api/v1/memory", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_memories_returns_user_nodes(client, db, auth_headers, user, tenant):
    await _create_memory(db, user.id, tenant.id, content="User dislikes 9 AM meetings")
    await db.flush()

    resp = await client.get("/api/v1/memory", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["content"] == "User dislikes 9 AM meetings"
    assert data[0]["memory_type"] == "semantic"


@pytest.mark.asyncio
async def test_list_memories_filter_by_type(client, db, auth_headers, user, tenant):
    await _create_memory(db, user.id, tenant.id, content="Fact")
    ep = MemoryNode(
        user_id=user.id,
        tenant_id=tenant.id,
        memory_type=MemoryType.episodic,
        content="Episode summary",
        source="chat",
        importance=0.5,
    )
    db.add(ep)
    await db.flush()

    resp = await client.get("/api/v1/memory?memory_type=semantic", headers=auth_headers)
    data = resp.json()
    assert all(m["memory_type"] == "semantic" for m in data)

    resp2 = await client.get("/api/v1/memory?memory_type=episodic", headers=auth_headers)
    data2 = resp2.json()
    assert all(m["memory_type"] == "episodic" for m in data2)


@pytest.mark.asyncio
async def test_list_memories_requires_auth(client):
    resp = await client.get("/api/v1/memory")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_update_memory_importance(client, db, auth_headers, user, tenant):
    node = await _create_memory(db, user.id, tenant.id, importance=0.5)
    await db.flush()

    resp = await client.patch(
        f"/api/v1/memory/{node.id}",
        json={"importance": 0.9},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["importance"] == 0.9


@pytest.mark.asyncio
async def test_delete_memory(client, db, auth_headers, user, tenant):
    node = await _create_memory(db, user.id, tenant.id, content="To be deleted")
    await db.flush()

    resp = await client.delete(f"/api/v1/memory/{node.id}", headers=auth_headers)
    assert resp.status_code == 204

    list_resp = await client.get("/api/v1/memory", headers=auth_headers)
    contents = [m["content"] for m in list_resp.json()]
    assert "To be deleted" not in contents


@pytest.mark.asyncio
async def test_memories_isolated_between_users(client, db, auth_headers, user, tenant):
    """Another user's memories must not appear in our list."""
    from app.db.models.user import User
    other_user = User(tenant_id=tenant.id, email="other2@example.com", full_name="Other2", hashed_password="x")
    db.add(other_user)
    await db.flush()

    await _create_memory(db, other_user.id, tenant.id, content="Other user secret")
    await _create_memory(db, user.id, tenant.id, content="My memory")
    await db.flush()

    resp = await client.get("/api/v1/memory", headers=auth_headers)
    contents = [m["content"] for m in resp.json()]
    assert "My memory" in contents
    assert "Other user secret" not in contents
