"""Redis cache — session, user, token, embedding, and API result caching.

Falls back to a simple in-memory dict when REDIS_URL is not set so the
application works in local dev without a Redis instance.

Postgres ↔ Redis sync strategy (Write-Through):
  - Always write to Postgres first (source of truth)
  - Immediately invalidate or update the Redis key after the DB write
  - On cache miss → read from Postgres → repopulate Redis
  - TTLs act as a safety net: even if invalidation is missed, data
    auto-expires and the next read re-hydrates from Postgres
"""

from __future__ import annotations

import hashlib
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
        logger.info("Redis connected — caching active")
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


# ── Core get / set / delete ───────────────────────────────────────────────────

async def set(key: str, value: Any, ttl_seconds: int = 300) -> None:
    data = json.dumps(value)
    r = _get_redis()
    if r:
        try:
            await r.set(key, data, ex=ttl_seconds)
            return
        except Exception as exc:
            logger.warning("Redis set failed, falling back to memory: %s", exc)
    _memory_store[key] = data


async def get(key: str) -> Any | None:
    r = _get_redis()
    if r:
        try:
            raw = await r.get(key)
            if raw is not None:
                return json.loads(raw)
        except Exception as exc:
            logger.warning("Redis get failed, falling back to memory: %s", exc)
    raw = _memory_store.get(key)
    if raw is None:
        return None
    return json.loads(raw)


async def delete(key: str) -> None:
    r = _get_redis()
    if r:
        try:
            await r.delete(key)
        except Exception as exc:
            logger.warning("Redis delete failed: %s", exc)
    _memory_store.pop(key, None)


async def delete_pattern(pattern: str) -> None:
    """Delete all keys matching a pattern e.g. 'calendar:user-uuid:*'."""
    r = _get_redis()
    if r:
        try:
            keys = await r.keys(pattern)
            if keys:
                await r.delete(*keys)
            return
        except Exception as exc:
            logger.warning("Redis delete_pattern failed: %s", exc)
    # In-memory fallback: match manually
    to_delete = [k for k in _memory_store if _match_pattern(k, pattern)]
    for k in to_delete:
        _memory_store.pop(k, None)


def _match_pattern(key: str, pattern: str) -> bool:
    """Simple glob-style matching for in-memory fallback (supports * only)."""
    import fnmatch
    return fnmatch.fnmatch(key, pattern)


# ── 1. User cache (replaces in-process dict in dependencies.py) ───────────────
# Postgres sync: invalidate on user update/login. TTL = 60s safety net.

USER_TTL = 60  # seconds


async def set_user(user_id: str, user_data: dict) -> None:
    await set(f"user:{user_id}", user_data, ttl_seconds=USER_TTL)


async def get_user(user_id: str) -> dict | None:
    return await get(f"user:{user_id}")


async def invalidate_user(user_id: str) -> None:
    """Call after any Postgres User row update."""
    await delete(f"user:{user_id}")


# ── 2. Google OAuth credentials cache ────────────────────────────────────────
# Postgres sync: invalidate when token is refreshed or re-authorised.
# TTL = 50 min (Google access tokens expire in 60 min — refresh before expiry).

GOOGLE_CREDS_TTL = 3000  # 50 minutes


async def set_google_creds(user_id: str, access: str, refresh: str | None) -> None:
    await set(
        f"google_creds:{user_id}",
        {"access": access, "refresh": refresh},
        ttl_seconds=GOOGLE_CREDS_TTL,
    )


async def get_google_creds(user_id: str) -> dict | None:
    return await get(f"google_creds:{user_id}")


async def invalidate_google_creds(user_id: str) -> None:
    """Call after Google token refresh or re-auth."""
    await delete(f"google_creds:{user_id}")


# ── 3. Embedding cache ────────────────────────────────────────────────────────
# Same text always produces the same embedding — safe to cache indefinitely.
# TTL = 7 days (balance memory usage vs. API cost savings).

EMBEDDING_TTL = 604800  # 7 days


def _embedding_key(text: str) -> str:
    digest = hashlib.md5(text.strip().lower().encode()).hexdigest()
    return f"embed:{digest}"


async def set_embedding(text: str, embedding: list[float]) -> None:
    await set(_embedding_key(text), embedding, ttl_seconds=EMBEDDING_TTL)


async def get_embedding(text: str) -> list[float] | None:
    return await get(_embedding_key(text))


# ── 4. Calendar results cache ─────────────────────────────────────────────────
# Postgres sync: not applicable (data lives in Google).
# Invalidate on create/update/delete calendar event.
# TTL = 5 min (short enough to stay fresh, long enough to reduce API calls).

CALENDAR_TTL = 300  # 5 minutes


async def set_calendar(user_id: str, days_ahead: int, events: list) -> None:
    await set(f"calendar:{user_id}:{days_ahead}", events, ttl_seconds=CALENDAR_TTL)


async def get_calendar(user_id: str, days_ahead: int) -> list | None:
    return await get(f"calendar:{user_id}:{days_ahead}")


async def invalidate_calendar(user_id: str) -> None:
    """Call after any calendar create/update/delete."""
    await delete_pattern(f"calendar:{user_id}:*")


# ── 5. Email results cache ────────────────────────────────────────────────────
# Invalidate after send/draft/trash.
# TTL = 2 min (emails change frequently).

EMAIL_TTL = 120  # 2 minutes


def _email_key(user_id: str, query: str, max_results: int) -> str:
    digest = hashlib.md5(f"{query}:{max_results}".encode()).hexdigest()
    return f"email:{user_id}:{digest}"


async def set_emails(user_id: str, query: str, max_results: int, data: dict) -> None:
    await set(_email_key(user_id, query, max_results), data, ttl_seconds=EMAIL_TTL)


async def get_emails(user_id: str, query: str, max_results: int) -> dict | None:
    return await get(_email_key(user_id, query, max_results))


async def invalidate_emails(user_id: str) -> None:
    """Call after send/draft/trash — clears all email cache for this user."""
    await delete_pattern(f"email:{user_id}:*")


# ── Legacy helpers (OAuth login flow) ────────────────────────────────────────

async def set_oauth_state(state: str, code_verifier: str) -> None:
    await set(f"oauth:state:{state}", code_verifier, ttl_seconds=600)


async def get_oauth_state(state: str) -> str | None:
    key = f"oauth:state:{state}"
    value = await get(key)
    await delete(key)
    return value


async def set_user_session(user_id: str, data: dict, ttl_seconds: int = 3600) -> None:
    await set(f"session:{user_id}", data, ttl_seconds=ttl_seconds)


async def get_user_session(user_id: str) -> dict | None:
    return await get(f"session:{user_id}")


async def invalidate_user_session(user_id: str) -> None:
    await delete(f"session:{user_id}")
