import time
import uuid
from typing import Any

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Any) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        log = logger.bind(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        log.info("request_completed", status=response.status_code, duration_ms=duration_ms)
        response.headers["X-Request-ID"] = request_id
        return response
