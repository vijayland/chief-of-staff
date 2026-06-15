"""Rate limiting — slowapi backed by Redis (falls back to in-memory)."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

# Use Redis if available, otherwise in-memory (dev / no-Redis deployments)
_storage = settings.REDIS_URL if settings.REDIS_URL else "memory://"

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_storage,
    default_limits=["200/minute"],
)
