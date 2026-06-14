import time
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import make_transient

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.db.models.tenant import Tenant
from app.db.models.user import User
from app.db.session import get_db

# Short-lived process-level cache to avoid a DB hit on every concurrent request.
# Values are detached User instances (make_transient) — scalar columns remain
# accessible; lazy relationships are not used in route handlers.
_USER_CACHE: dict[str, tuple[User, float]] = {}
_USER_CACHE_TTL = 60.0  # seconds


def invalidate_user_cache(user_id: str) -> None:
    """Call after mutating a User row so the next request re-fetches from DB."""
    _USER_CACHE.pop(str(user_id), None)


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedError()

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_token(token)
    except ValueError as err:
        raise UnauthorizedError("Invalid or expired token") from err

    if payload.get("type") != "access":
        raise UnauthorizedError("Expected access token")

    user_id = payload.get("sub")

    now = time.monotonic()
    cached = _USER_CACHE.get(user_id)
    if cached and now - cached[1] < _USER_CACHE_TTL:
        return cached[0]

    result = await db.execute(select(User).where(User.id == user_id, User.is_active))
    user = result.scalar_one_or_none()

    if not user:
        raise UnauthorizedError("User not found or inactive")

    # Detach from session before caching so it is not bound to any transaction.
    db.expunge(user)
    make_transient(user)
    _USER_CACHE[user_id] = (user, now)

    # Prune expired entries to avoid unbounded growth.
    if len(_USER_CACHE) > 1000:
        cutoff = now - _USER_CACHE_TTL
        expired = [k for k, (_, t) in _USER_CACHE.items() if t < cutoff]
        for k in expired:
            _USER_CACHE.pop(k, None)

    return user


async def get_current_tenant(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant or not tenant.is_active:
        raise ForbiddenError("Tenant not found or suspended")
    return tenant


def require_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if not current_user.is_admin:
        raise ForbiddenError("Admin access required")
    return current_user


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentTenant = Annotated[Tenant, Depends(get_current_tenant)]
DBSession = Annotated[AsyncSession, Depends(get_db)]
