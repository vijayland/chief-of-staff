import uuid
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decrypt_value,
    encrypt_value,
)
from app.dependencies import invalidate_user_cache
from app.db.models.oauth_token import OAuthToken
from app.db.models.tenant import Tenant
from app.db.models.user import User
from app.integrations.google import oauth as google_oauth
from app.integrations.google.oauth import build_credentials


def issue_tokens(user: User) -> dict:
    return {
        "access_token": create_access_token(str(user.id), {"tenant_id": str(user.tenant_id)}),
        "refresh_token": create_refresh_token(str(user.id)),
        "token_type": "bearer",
    }


async def get_google_auth_url() -> dict:
    url, state = await google_oauth.get_authorization_url()
    return {"url": url, "state": state}


async def _get_google_profile(access_token: str) -> dict:
    """Fetch the user's profile from Google userinfo endpoint."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        return resp.json()


async def handle_google_login(db: AsyncSession, code: str, state: str) -> dict:
    """
    Full Google login flow — works for both first-time and returning users.
    Returns JWT tokens ready to send to the frontend.
    """
    token_data = await google_oauth.exchange_code(code, state)
    profile = await _get_google_profile(token_data["access_token"])

    email: str = profile["email"]
    full_name: str = profile.get("name", email.split("@")[0])

    # Find existing user or create new one
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        # Auto-create tenant from email domain
        domain = email.split("@")[1].replace(".", "-")
        tenant_result = await db.execute(select(Tenant).where(Tenant.slug == domain))
        tenant = tenant_result.scalar_one_or_none()
        if not tenant:
            tenant = Tenant(name=domain.title(), slug=domain)
            db.add(tenant)
            await db.flush()

        user = User(
            tenant_id=tenant.id,
            email=email,
            full_name=full_name,
            google_connected=True,
        )
        db.add(user)
        await db.flush()

    # Upsert OAuth tokens
    expiry = None
    if token_data.get("expiry"):
        expiry = datetime.fromisoformat(token_data["expiry"])

    token_result = await db.execute(
        select(OAuthToken).where(OAuthToken.user_id == user.id, OAuthToken.provider == "google")
    )
    existing_token = token_result.scalar_one_or_none()

    if existing_token:
        existing_token.encrypted_access_token = encrypt_value(token_data["access_token"])
        if token_data.get("refresh_token"):
            existing_token.encrypted_refresh_token = encrypt_value(token_data["refresh_token"])
        existing_token.token_expiry = expiry
    else:
        oauth_token = OAuthToken(
            user_id=user.id,
            provider="google",
            encrypted_access_token=encrypt_value(token_data["access_token"]),
            encrypted_refresh_token=encrypt_value(token_data["refresh_token"]) if token_data.get("refresh_token") else None,
            token_expiry=expiry,
            scopes=" ".join(token_data.get("scopes", [])),
        )
        db.add(oauth_token)

    user.google_connected = True
    await db.flush()
    invalidate_user_cache(str(user.id))

    return issue_tokens(user)


async def get_google_credentials(db: AsyncSession, user_id: uuid.UUID):
    result = await db.execute(
        select(OAuthToken).where(OAuthToken.user_id == user_id, OAuthToken.provider == "google")
    )
    token = result.scalar_one_or_none()
    if not token:
        return None

    access = decrypt_value(token.encrypted_access_token)
    refresh = decrypt_value(token.encrypted_refresh_token) if token.encrypted_refresh_token else None
    return build_credentials(access, refresh)
