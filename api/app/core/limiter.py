"""Rate limiting — slowapi with in-memory storage.

The `limits` library uses a synchronous Redis client which has SSL
compatibility issues (Python 3.12+). In-memory is fine for single-process
deployments (dev and single-instance prod).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",
    default_limits=["200/minute"],
)
