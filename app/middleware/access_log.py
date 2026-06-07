"""Access logging middleware."""

import time
import uuid
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.models.audit import AccessLog


class AccessLogMiddleware(BaseHTTPMiddleware):
    SKIP_PATHS = {"/health", "/static"}

    async def dispatch(self, request: Request, call_next) -> Response:
        if any(request.url.path.startswith(p) for p in self.SKIP_PATHS):
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = int((time.perf_counter() - start) * 1000)

        try:
            from app.database import get_async_session_factory

            async with get_async_session_factory()() as db:
                log = AccessLog(
                    path=str(request.url.path)[:512],
                    method=request.method,
                    status_code=response.status_code,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                    partner_id=getattr(request.state, "partner_id", None),
                    duration_ms=duration_ms,
                    created_at=datetime.now(timezone.utc),
                )
                db.add(log)
                await db.commit()
        except Exception:
            pass

        return response
