"""Production request security, rate limiting, and observability middleware."""

import hashlib
import json
import logging
import time
import uuid
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from contextvars import ContextVar

from fastapi import Request, Response
from prometheus_client import Counter, Histogram
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import Settings
from app.core.errors import error_payload

logger = logging.getLogger("memoryhive.requests")
REQUEST_ID_CONTEXT: ContextVar[str | None] = ContextVar(
    "memoryhive_request_id", default=None
)
REQUEST_COUNT = Counter(
    "memoryhive_http_requests_total",
    "HTTP requests",
    ("method", "route", "status"),
)
REQUEST_DURATION = Histogram(
    "memoryhive_http_request_duration_seconds",
    "HTTP request duration",
    ("method", "route"),
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in (
            "request_id",
            "correlation_id",
            "job_id",
            "workflow_id",
            "provider",
            "stage",
            "method",
            "path",
            "status",
            "duration_ms",
        ):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        supplied_id = request.headers.get("x-request-id", "")
        request_id = supplied_id[:128] if supplied_id.isascii() else ""
        request_id = request_id or str(uuid.uuid4())
        request.state.request_id = request_id
        token = REQUEST_ID_CONTEXT.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            REQUEST_ID_CONTEXT.reset(token)
        duration = time.perf_counter() - started
        route = request.scope.get("route")
        route_path = getattr(route, "path", request.url.path)
        REQUEST_COUNT.labels(request.method, route_path, response.status_code).inc()
        REQUEST_DURATION.labels(request.method, route_path).observe(duration)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round(duration * 1000, 2),
            },
        )
        return response


def current_request_id() -> str | None:
    return REQUEST_ID_CONTEXT.get()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, settings: Settings) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.production = settings.is_production

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'"
        )
        if self.production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, settings: Settings) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.settings = settings
        self.redis = Redis.from_url(settings.redis_url) if settings.redis_url else None
        self.local: dict[str, deque[float]] = defaultdict(deque)

    def _limit(self, path: str) -> int:
        return (
            self.settings.auth_rate_limit_per_minute
            if path
            in {"/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/auth/refresh"}
            else self.settings.rate_limit_per_minute
        )

    def _identity(self, request: Request) -> str:
        authorization = request.headers.get("authorization")
        if authorization:
            return hashlib.sha256(authorization.encode()).hexdigest()[:20]
        return request.client.host if request.client else "unknown"

    async def _increment(self, key: str, now: float) -> int:
        if self.redis:
            try:
                count = await self.redis.incr(key)
                if count == 1:
                    await self.redis.expire(key, 65)
                return count
            except Exception:
                logger.warning("Redis rate limiter unavailable; using local fallback")
        values = self.local[key]
        cutoff = now - 60
        while values and values[0] <= cutoff:
            values.popleft()
        values.append(now)
        return len(values)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path.startswith(("/health", "/metrics")):
            return await call_next(request)
        now = time.time()
        limit = self._limit(request.url.path)
        bucket = int(now // 60)
        key = f"rate:{request.url.path}:{self._identity(request)}:{bucket}"
        count = await self._increment(key, now)
        if count > limit:
            return Response(
                content=json.dumps(error_payload(429, "Rate limit exceeded")),
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(max(1, 60 - int(now % 60)))},
            )
        response = await call_next(request)
        response.headers["RateLimit-Limit"] = str(limit)
        response.headers["RateLimit-Remaining"] = str(max(0, limit - count))
        return response
