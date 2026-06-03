import logging
import time
import uuid
from contextvars import ContextVar

from jose import jwt as _jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from config import settings
from service.auth_service import ALGORITHM

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

SKIP_PATHS = {"/health", "/version"}


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get("-")
        return True


class LoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.logger = logging.getLogger("middleware.request")

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in SKIP_PATHS:
            return await call_next(request)

        rid = uuid.uuid4().hex[:8]
        request_id_var.set(rid)

        # Best-effort username extraction from JWT
        username = "-"
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            try:
                payload = _jwt.decode(
                    auth[7:], settings.JWT_SECRET_KEY, algorithms=[ALGORITHM]
                )
                username = payload.get("sub", "-")
            except Exception:
                pass

        self.logger.info(
            "%s %s user=%s", request.method, request.url.path, username
        )

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        self.logger.info(
            "%s %s -> %d (%.0fms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response
