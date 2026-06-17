import uuid
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import (
    get_google_creds,
    invalidate_google_creds,
    invalidate_user,
    set_google_creds,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decrypt_value,
    encrypt_value,
)
from app.db.models.oauth_token import OAuthToken
from app.db.models.tenant import Tenant
from app.db.models.user import User
from app.dependencies import invalidate_user_cache
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
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        return resp.json()


async def handle_google_login(db: AsyncSession, code: str, state: str) -> dict:
    """Full Google login flow. Returns JWT tokens ready to send to the frontend."""
    token_data = await google_oauth.exchange_code(code, state)
    profile = await _get_google_profile(token_data["access_token"])

    email: str = profile["email"]
    full_name: str = profile.get("name", email.split("@")[0])

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
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

    # Postgres updated → invalidate Redis caches so next request re-hydrates
    await invalidate_user(str(user.id))
    await invalidate_google_creds(str(user.id))

    # Pre-warm Google creds cache with fresh tokens
    refresh = token_data.get("refresh_token")
    await set_google_creds(str(user.id), token_data["access_token"], refresh)

    invalidate_user_cache(str(user.id))
    return issue_tokens(user)


async def get_google_credentials(db: AsyncSession, user_id: uuid.UUID):
    """
    Returns Google Credentials for the user.

    Cache flow:
      1. Check Redis (cache hit → no DB query, no decrypt)
      2. Miss → fetch encrypted tokens from Postgres → decrypt → cache in Redis
      3. TTL = 50 min (tokens expire in 60 min, refresh happens before expiry)

    Postgres sync: invalidate_google_creds() called on login and token refresh.
    """
    uid = str(user_id)

    # 1. Try Redis
    cached = await get_google_creds(uid)
    if cached:
        return build_credentials(cached["access"], cached["refresh"])

    # 2. Cache miss → Postgres
    result = await db.execute(
        select(OAuthToken).where(OAuthToken.user_id == user_id, OAuthToken.provider == "google")
    )
    token = result.scalar_one_or_none()
    if not token:
        return None

    access = decrypt_value(token.encrypted_access_token)
    refresh = decrypt_value(token.encrypted_refresh_token) if token.encrypted_refresh_token else None

    # 3. Write to Redis
    await set_google_creds(uid, access, refresh)

    return build_credentials(access, refresh)
