"""
Rate limiting middleware for protecting sensitive endpoints.

Implements Redis-backed rate limiting with sliding window algorithm.
Each protected path prefix has its own (limit, window_seconds) tuple.
"""

import logging
from typing import Optional
from datetime import datetime

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

try:
    import redis.asyncio as redis
except ImportError:
    redis = None

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using Redis for sliding window tracking.

    Path prefix → (max_requests, window_seconds).
    First matching prefix wins; order matters (most specific first).
    """

    # (limit, window_seconds) per path prefix — most specific first
    RATE_LIMITS: list[tuple[str, int, int]] = [
        ("/api/v1/auth/login",        5,   60),   # 5 req / 60s per IP
        ("/api/v1/auth/register",     3,  300),   # 3 req / 5min per IP
        ("/api/v1/auth",              10,  60),   # other auth (google, 2fa) 10/min
        ("/api/v1/onboarding",        3,  300),   # signup 3 / 5min per IP
        ("/api/v1/company-documents", 20,  60),   # upload 20 / min per tenant-ip
        ("/api/v1/billing",          100,  60),   # webhook 100 / min per IP
        ("/api/v1/portal",            30,  60),   # portal 30 / min per IP
        ("/api/v1/admin",             10,  60),   # admin 10 / min per IP
    ]

    # Kept for backward compat — not used internally anymore
    ADMIN_LIMIT = 10
    ADMIN_WINDOW = 60

    def __init__(self, app, redis_url: Optional[str] = None, strict: Optional[bool] = None):
        super().__init__(app)
        self.redis_url = redis_url  # None = disabled; no fallback to localhost
        self.redis_client = None
        self._initialized = False
        if strict is None:
            from app.core.config import settings

            strict = settings.RATE_LIMIT_STRICT
        self.strict = strict

    async def _init_redis(self):
        """Lazy initialize Redis connection."""
        if self._initialized:
            return self.redis_client

        if redis is None:
            logger.error("Rate limit Redis client is not installed.")
            self._initialized = True
            return None

        if not self.redis_url:
            # No REDIS_URL configured — rate limiting disabled, skip connection attempt
            self._initialized = True
            return None

        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            self._initialized = True
            # Log only the host portion — never log credentials from the URL
            try:
                from urllib.parse import urlparse as _up
                _h = _up(self.redis_url).hostname or "unknown"
            except Exception:
                _h = "unknown"
            logger.info("Rate limit Redis connection established: %s", _h)
        except Exception as e:
            logger.warning("Rate limit Redis unavailable: %s. Rate limiting disabled.", str(e))
            self.redis_client = None
            self._initialized = True

        return self.redis_client

    def _rate_limit_unavailable_response(self) -> JSONResponse:
        """Return fail-closed response when strict rate limiting is enabled."""
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "detail": "Rate limiting is unavailable",
                "error_code": "RATE_LIMIT_UNAVAILABLE",
                "message": "Request rejected because rate limiting cannot be enforced.",
            },
        )

    def _match_rate_limit(self, path: str) -> tuple[int, int] | None:
        """Return (limit, window_seconds) for the first matching path prefix, or None."""
        for prefix, limit, window in self.RATE_LIMITS:
            if path.startswith(prefix):
                return limit, window
        return None

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, considering X-Forwarded-For header."""
        # Check X-Forwarded-For header first (for proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # Fall back to direct client IP
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        path = request.url.path

        matched = self._match_rate_limit(path)
        if matched is None:
            return await call_next(request)

        limit, window = matched

        # Initialize Redis if needed
        client = await self._init_redis()

        if client is None:
            if self.strict:
                logger.error("Rate limiting unavailable while RATE_LIMIT_STRICT=true")
                return self._rate_limit_unavailable_response()
            logger.debug("Rate limiting disabled - Redis unavailable")
            return await call_next(request)

        current_count = 0
        try:
            client_ip = self._get_client_ip(request)
            # Normalize path to prefix for stable key (avoids per-UUID key explosion)
            key_path = path[:60]
            rate_limit_key = f"rl:{key_path}:{client_ip}"

            current_count = await client.incr(rate_limit_key)

            if current_count == 1:
                await client.expire(rate_limit_key, window)

            if current_count > limit:
                logger.warning(
                    "Rate limit exceeded: ip=%s path=%s count=%d limit=%d window=%ds",
                    client_ip, path, current_count, limit, window,
                )
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "Rate limit exceeded",
                        "error_code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Too many requests. Maximum {limit} per {window}s.",
                        "retry_after": window,
                    },
                    headers={"Retry-After": str(window)},
                )
        except Exception as e:
            logger.error("Rate limit middleware error: %s", str(e), exc_info=True)
            if self.strict:
                return self._rate_limit_unavailable_response()
            current_count = 0

        response = await call_next(request)

        if current_count > 0:
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(max(0, limit - current_count))
            response.headers["X-RateLimit-Reset"] = str(int(datetime.utcnow().timestamp()) + window)

        return response
