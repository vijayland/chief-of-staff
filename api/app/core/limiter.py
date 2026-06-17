"""Rate limiting — slowapi backed by Redis (falls back to memory if Redis unavailable)."""

from app.config import settings
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL if settings.REDIS_URL else "memory://",
    default_limits=["200/minute"],
)
