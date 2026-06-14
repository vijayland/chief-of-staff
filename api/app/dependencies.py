from typing import Annotated
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.security import decode_token
from app.core.exceptions import UnauthorizedError, ForbiddenError
from app.db.models.user import User
from app.db.models.tenant import Tenant
from sqlalchemy import select


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedError()

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_token(token)
    except ValueError:
        raise UnauthorizedError("Invalid or expired token")

    if payload.get("type") != "access":
        raise UnauthorizedError("Expected access token")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()

    if not user:
        raise UnauthorizedError("User not found or inactive")

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
