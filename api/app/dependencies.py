import uuid
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import make_transient

from app.core.cache import get_user, invalidate_user, set_user
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.db.models.tenant import Tenant
from app.db.models.user import User
from app.db.session import get_db


def _user_to_dict(user: User) -> dict:
    return {
        "id": str(user.id),
        "tenant_id": str(user.tenant_id),
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_admin": user.is_admin,
        "google_connected": user.google_connected,
        "timezone": user.timezone,
        "preferred_name": user.preferred_name,
    }


def _dict_to_user(data: dict) -> User:
    user = User()
    user.id = uuid.UUID(data["id"])
    user.tenant_id = uuid.UUID(data["tenant_id"])
    user.email = data["email"]
    user.full_name = data["full_name"]
    user.is_active = data["is_active"]
    user.is_admin = data["is_admin"]
    user.google_connected = data["google_connected"]
    user.timezone = data["timezone"]
    user.preferred_name = data["preferred_name"]
    make_transient(user)
    return user


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

    # 1. Try Redis first
    cached = await get_user(user_id)
    if cached:
        return _dict_to_user(cached)

    # 2. Cache miss → hit Postgres
    result = await db.execute(select(User).where(User.id == user_id, User.is_active))
    user = result.scalar_one_or_none()

    if not user:
        raise UnauthorizedError("User not found or inactive")

    # 3. Write to Redis, detach from session
    await set_user(user_id, _user_to_dict(user))
    db.expunge(user)
    make_transient(user)

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


# Replace the old in-process invalidate_user_cache with Redis version
def invalidate_user_cache(user_id: str) -> None:
    """Sync shim — schedules Redis invalidation. Use invalidate_user() directly in async code."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(invalidate_user(user_id))
        else:
            loop.run_until_complete(invalidate_user(user_id))
    except Exception:
        pass


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentTenant = Annotated[Tenant, Depends(get_current_tenant)]
DBSession = Annotated[AsyncSession, Depends(get_db)]
