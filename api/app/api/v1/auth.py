from fastapi import APIRouter, Query, Request
from fastapi.responses import RedirectResponse

from app.config import settings
from app.core.exceptions import GoogleAuthError, UnauthorizedError
from app.core.limiter import limiter
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.dependencies import CurrentUser, DBSession
from app.schemas.auth import GoogleAuthURLResponse, TokenResponse, UserResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])

FRONTEND_URL = settings.FRONTEND_URL


@router.get("/google", response_model=GoogleAuthURLResponse, summary="Get Google OAuth URL")
@limiter.limit("10/minute")
async def google_auth_url(request: Request):
    """
    Generate the Google OAuth 2.0 authorisation URL.

    Redirect the user to the returned `url` to sign in with Google.
    Grants access to Gmail and Google Calendar.
    After approval, Google redirects to `/auth/google/callback` with tokens.
    """
    try:
        return await auth_service.get_google_auth_url()
    except Exception as exc:
        raise GoogleAuthError(f"Failed to build Google OAuth URL: {exc}") from exc


@router.get("/google/callback", include_in_schema=False)
async def google_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: DBSession = None,
):
    """Google redirects here — exchange code for JWT tokens, redirect to frontend."""
    tokens = await auth_service.handle_google_login(db, code, state)
    redirect_url = (
        f"{FRONTEND_URL}/auth/callback"
        f"?access_token={tokens['access_token']}"
        f"&refresh_token={tokens['refresh_token']}"
    )
    return RedirectResponse(url=redirect_url)


@router.post("/refresh", response_model=TokenResponse, summary="Refresh access token")
@limiter.limit("20/minute")
async def refresh_token(request: Request, body: dict):
    """
    Exchange a valid `refresh_token` for a new token pair.

    Use when the access token expires (60 min TTL).
    """
    token = body.get("refresh_token", "")
    try:
        payload = decode_token(token)
    except ValueError as err:
        raise UnauthorizedError("Invalid refresh token") from err

    if payload.get("type") != "refresh":
        raise UnauthorizedError("Expected refresh token")

    user_id = payload["sub"]
    return {
        "access_token": create_access_token(user_id),
        "refresh_token": create_refresh_token(user_id),
        "token_type": "bearer",
    }


@router.get("/me", response_model=UserResponse, summary="Get current user profile")
async def get_me(current_user: CurrentUser):
    """Return the profile of the currently authenticated user."""
    return current_user
