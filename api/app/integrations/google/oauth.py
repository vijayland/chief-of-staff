import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from app.config import settings
from app.core import cache

os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"


def _client_config() -> dict:
    return {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
        }
    }


def build_flow(state: str | None = None, pkce: bool = False) -> Flow:
    flow = Flow.from_client_config(
        _client_config(),
        scopes=settings.google_scopes_list,
        state=state,
        autogenerate_code_verifier=pkce,
    )
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    return flow


async def get_authorization_url() -> tuple[str, str]:
    # PKCE requires shared state storage; fall back to plain OAuth when Redis is unavailable
    # (in-memory state is lost during rolling ECS deployments)
    use_pkce = bool(settings.REDIS_URL)
    flow = build_flow(pkce=use_pkce)
    url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    if flow.code_verifier:
        await cache.set_oauth_state(state, flow.code_verifier)
    return url, state


async def exchange_code(code: str, state: str) -> dict:
    flow = build_flow(state=state)
    code_verifier = await cache.get_oauth_state(state)
    # If PKCE was used but the verifier is gone (container restart/redeploy), fail fast
    # with a clear message rather than letting Google return an obscure token error.
    if settings.REDIS_URL and code_verifier is None:
        raise ValueError("OAuth session expired — please sign in again.")
    flow.fetch_token(code=code, code_verifier=code_verifier)
    creds = flow.credentials
    return {
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
        "scopes": list(creds.scopes or []),
    }


def build_credentials(access_token: str, refresh_token: str | None = None) -> Credentials:
    return Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=settings.google_scopes_list,
    )


def refresh_credentials(creds: Credentials) -> Credentials:
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds
