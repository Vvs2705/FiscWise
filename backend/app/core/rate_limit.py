"""
Rate limiting middleware for protecting sensitive endpoints.

Implements Redis-backed rate limiting with sliding window algorithm.
Protection for /api/v1/admin/* endpoints (10 attempts per minute per IP).
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

    Configuration:
    - Admin endpoints (/api/v1/admin/*): 10 requests per minute per IP
    - Stores key: rate_limit:{endpoint}:{client_ip}
    - TTL: 60 seconds
    """

    ADMIN_LIMIT = 10  # requests per minute
    ADMIN_WINDOW = 60  # seconds
    PROTECTED_PATHS = {"/api/v1/admin"}
    # Sync offline (OFFLINE_SYNC.md 9): por dispositivo (hash do token) + IP, porque
    # vários dispositivos do mesmo escritório saem pelo mesmo IP.
    SYNC_PREFIX = "/api/v1/sync"
    SYNC_LIMIT = 240
    SYNC_WINDOW = 60

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
            logger.info("Rate limit Redis connection established: %s", self.redis_url[:30])
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

    def _is_protected_path(self, path: str) -> bool:
        """Check if path matches protected prefixes."""
        return self._is_sync_path(path) or any(path.startswith(prefix) for prefix in self.PROTECTED_PATHS)

    def _is_sync_path(self, path: str) -> bool:
        return path == self.SYNC_PREFIX or path.startswith(f"{self.SYNC_PREFIX}/")

    def _limits_for(self, path: str) -> tuple[int, int]:
        if self._is_sync_path(path):
            return self.SYNC_LIMIT, self.SYNC_WINDOW
        return self.ADMIN_LIMIT, self.ADMIN_WINDOW

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request (same trusted-proxy rule as auth)."""
        from app.core.auth_rate_limiter import get_client_ip

        return get_client_ip(request)

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        path = request.url.path

        # Only apply rate limiting to protected endpoints
        if not self._is_protected_path(path):
            return await call_next(request)

        # Initialize Redis if needed
        client = await self._init_redis()

        # If Redis is unavailable, either fail closed or allow request.
        if client is None:
            if self.strict:
                logger.error("Rate limiting unavailable while RATE_LIMIT_STRICT=true")
                return self._rate_limit_unavailable_response()
            logger.debug("Rate limiting disabled - Redis unavailable")
            return await call_next(request)

        current_count = 0
        limit, window = self._limits_for(path)
        try:
            client_ip = self._get_client_ip(request)
            rate_limit_key = f"rate_limit:{path}:{client_ip}"
            if self._is_sync_path(path):
                import hashlib

                auth = request.headers.get("Authorization", "")
                rate_limit_key += ":" + hashlib.sha256(auth.encode()).hexdigest()[:16]

            # Get current request count for this client
            current_count = await client.incr(rate_limit_key)

            # Set expiration on first request
            if current_count == 1:
                await client.expire(rate_limit_key, window)

            # Check if limit exceeded
            if current_count > limit:
                logger.warning(
                    f"Rate limit exceeded for {client_ip} on {path} "
                    f"({current_count}/{limit} requests in {window}s)"
                )
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "Rate limit exceeded",
                        "error_code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Too many requests. Maximum {limit} requests per {window} seconds allowed.",
                        "retry_after": window
                    }
                )
        except Exception as e:
            logger.error(f"Rate limit middleware error: {str(e)}", exc_info=True)
            if self.strict:
                return self._rate_limit_unavailable_response()
            current_count = 0

        # Execute downstream handlers. Any exception raised here will propagate naturally.
        response = await call_next(request)

        # Add rate limit headers to response only if rate limiting logic was successfully executed
        if current_count > 0:
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(max(0, limit - current_count))
            response.headers["X-RateLimit-Reset"] = str(datetime.utcnow().timestamp() + window)

        return response
