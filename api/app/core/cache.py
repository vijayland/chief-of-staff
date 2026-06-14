"""Redis cache — session data and OAuth state storage.

Falls back to a simple in-memory dict when REDIS_URL is not set so the
application works in local dev without a Redis instance.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

# ── Redis client (lazy) ───────────────────────────────────────────────────────
_redis = None


def _get_redis():
    global _redis
    if _redis is not None:
        return _redis

    if not settings.REDIS_URL:
        return None

    try:
        import redis.asyncio as aioredis
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
        logger.info("Redis connected — session caching active")
    except Exception as exc:
        logger.warning("Redis unavailable, using in-memory fallback: %s", exc)
        _redis = None

    return _redis


# ── In-memory fallback ────────────────────────────────────────────────────────
_memory_store: dict[str, str] = {}


async def close() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


# ── Public API ────────────────────────────────────────────────────────────────

async def set(key: str, value: Any, ttl_seconds: int = 300) -> None:
    """Store a value. TTL defaults to 5 minutes."""
    data = json.dumps(value)
    r = _get_redis()
    if r:
        await r.set(key, data, ex=ttl_seconds)
    else:
        _memory_store[key] = data


async def get(key: str) -> Any | None:
    """Retrieve a value. Returns None if missing or expired."""
    r = _get_redis()
    if r:
        raw = await r.get(key)
    else:
        raw = _memory_store.get(key)

    if raw is None:
        return None
    return json.loads(raw)


async def delete(key: str) -> None:
    r = _get_redis()
    if r:
        await r.delete(key)
    else:
        _memory_store.pop(key, None)


# ── Namespaced helpers ────────────────────────────────────────────────────────

async def set_oauth_state(state: str, code_verifier: str) -> None:
    """Store OAuth PKCE code verifier keyed by state. TTL = 10 minutes."""
    await set(f"oauth:state:{state}", code_verifier, ttl_seconds=600)


async def get_oauth_state(state: str) -> str | None:
    """Retrieve and delete OAuth state (one-time use)."""
    key = f"oauth:state:{state}"
    value = await get(key)
    await delete(key)
    return value


async def set_user_session(user_id: str, data: dict, ttl_seconds: int = 3600) -> None:
    """Cache user session data. TTL = 1 hour."""
    await set(f"session:{user_id}", data, ttl_seconds=ttl_seconds)


async def get_user_session(user_id: str) -> dict | None:
    return await get(f"session:{user_id}")


async def invalidate_user_session(user_id: str) -> None:
    await delete(f"session:{user_id}")
