"""
Rate limiting da API inteira.

Três faixas, todas em janela fixa de 60 s:

- ``/api/v1/admin/*``: 10 req/min por IP e rota (painel interno).
- ``/api/v1/sync/*``: 240 req/min por dispositivo (hash do token) + IP, porque
  vários dispositivos do mesmo escritório saem pelo mesmo IP (OFFLINE_SYNC.md 9).
- Todo o resto de ``/api/``: por **usuário** (``sub`` do JWT com assinatura
  válida) ou por chave de API; sem credencial válida, por IP. Limites em
  ``RATE_LIMIT_USER_PER_MINUTE`` e ``RATE_LIMIT_ANON_PER_MINUTE``.

Contador em memória do processo por padrão: com uma instância só no Cloud Run
é exato e não custa nada. Quando o serviço passar de uma instância, configurar
``REDIS_URL`` para o contador valer para todas (sem Redis cada instância conta
o seu, e o limite efetivo vira limite x instâncias).

``RATE_LIMIT_STRICT=true`` com ``REDIS_URL`` configurado e Redis fora do ar
recusa as rotas protegidas com 503 em vez de cair para a memória.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Optional

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

try:
    import redis.asyncio as redis
except ImportError:  # pragma: no cover - dependência do requirements
    redis = None

logger = logging.getLogger(__name__)


class MemoryRateCounter:
    """Contador de janela fixa em memória (mesma semântica do INCR + EXPIRE)."""

    MAX_KEYS = 50_000

    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._windows: dict[str, tuple[float, int]] = {}

    def hit(self, key: str, window: int) -> tuple[int, float]:
        """Conta uma requisição. Devolve (contagem na janela, segundos até zerar)."""
        now = self._clock()
        started, count = self._windows.get(key, (now, 0))
        if now - started >= window:
            started, count = now, 0
        count += 1
        self._windows[key] = (started, count)
        if len(self._windows) > self.MAX_KEYS:
            self._prune(now, window)
        return count, max(0.0, window - (now - started))

    def _prune(self, now: float, window: int) -> None:
        self._windows = {k: v for k, v in self._windows.items() if now - v[0] < window}
        if len(self._windows) > self.MAX_KEYS:
            # Inundação de chaves (IPs variados): descarta as janelas mais antigas.
            ordered = sorted(self._windows.items(), key=lambda kv: kv[1][0])
            self._windows = dict(ordered[len(ordered) // 2:])

    def clear(self) -> None:
        self._windows.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    ADMIN_LIMIT = 10  # requests per minute
    ADMIN_WINDOW = 60  # seconds
    PROTECTED_PATHS = {"/api/v1/admin"}
    SYNC_PREFIX = "/api/v1/sync"
    SYNC_LIMIT = 240
    SYNC_WINDOW = 60
    API_PREFIX = "/api/"
    GENERAL_WINDOW = 60
    # Sondas e documentação ficam fora (o Cloud Run sonda /live com frequência).
    EXEMPT_PREFIXES = ("/api/v1/health", "/api/v1/live", "/api/v1/ready")

    def __init__(
        self,
        app,
        redis_url: Optional[str] = None,
        strict: Optional[bool] = None,
        user_limit: Optional[int] = None,
        anon_limit: Optional[int] = None,
    ):
        super().__init__(app)
        from app.core.config import settings

        self.redis_url = redis_url  # None = contador em memória
        self.redis_client = None
        self._initialized = False
        self.strict = settings.RATE_LIMIT_STRICT if strict is None else strict
        self._user_limit = user_limit
        self._anon_limit = anon_limit
        self.memory = MemoryRateCounter()

    # Lidos a cada requisição (None = settings): permite ajustar sem recriar a app.
    @property
    def user_limit(self) -> int:
        from app.core.config import settings

        return settings.RATE_LIMIT_USER_PER_MINUTE if self._user_limit is None else self._user_limit

    @property
    def anon_limit(self) -> int:
        from app.core.config import settings

        return settings.RATE_LIMIT_ANON_PER_MINUTE if self._anon_limit is None else self._anon_limit

    async def _init_redis(self):
        """Conecta no Redis uma vez (só quando REDIS_URL existe)."""
        if self._initialized:
            return self.redis_client
        self._initialized = True
        if not self.redis_url:
            return None
        if redis is None:
            logger.error("REDIS_URL configurado mas o cliente redis não está instalado.")
            return None
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            await self.redis_client.ping()
            logger.info("Rate limit com Redis: %s", self.redis_url[:30])
        except Exception as e:
            logger.warning("Redis do rate limit indisponível (%s): usando contador em memória.", str(e))
            self.redis_client = None
        return self.redis_client

    def _rate_limit_unavailable_response(self) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "detail": "Rate limiting is unavailable",
                "error_code": "RATE_LIMIT_UNAVAILABLE",
                "message": "Request rejected because rate limiting cannot be enforced.",
            },
        )

    def _is_sync_path(self, path: str) -> bool:
        return path == self.SYNC_PREFIX or path.startswith(f"{self.SYNC_PREFIX}/")

    def _is_admin_path(self, path: str) -> bool:
        return any(path.startswith(prefix) for prefix in self.PROTECTED_PATHS)

    def _is_protected_path(self, path: str) -> bool:
        return path.startswith(self.API_PREFIX) and not path.startswith(self.EXEMPT_PREFIXES)

    def _get_client_ip(self, request: Request) -> str:
        """Mesmo IP confiável do limitador de login (último X-Forwarded-For)."""
        from app.core.auth_rate_limiter import get_client_ip

        return get_client_ip(request)

    @staticmethod
    def _identity(request: Request) -> Optional[str]:
        """Quem fez a requisição: ``user:<sub>`` (JWT válido) ou ``key:<hash>``.

        A assinatura é conferida: um token forjado não escolhe o próprio balde
        e cai no limite por IP. Token vencido ainda identifica o usuário (a rota
        responde 401 de qualquer forma).
        """
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return "key:" + hashlib.sha256(api_key.encode()).hexdigest()[:24]
        auth = request.headers.get("Authorization", "")
        if not auth.lower().startswith("bearer "):
            return None
        token = auth[7:].strip()
        if not token:
            return None
        from jose import JWTError, jwt

        from app.core.config import settings

        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                options={"verify_exp": False, "verify_aud": False},
            )
        except JWTError:
            return None
        sub = payload.get("sub")
        return f"user:{sub}" if sub else None

    def _bucket(self, request: Request, path: str) -> tuple[str, int, int, str]:
        """(chave, limite, janela, descrição para o log)."""
        client_ip = self._get_client_ip(request)
        if self._is_admin_path(path):
            return f"rate_limit:{path}:{client_ip}", self.ADMIN_LIMIT, self.ADMIN_WINDOW, client_ip
        if self._is_sync_path(path):
            auth = request.headers.get("Authorization", "")
            digest = hashlib.sha256(auth.encode()).hexdigest()[:16]
            return f"rate_limit:{path}:{client_ip}:{digest}", self.SYNC_LIMIT, self.SYNC_WINDOW, client_ip
        identity = self._identity(request)
        if identity:
            return f"rate_limit:api:{identity}", self.user_limit, self.GENERAL_WINDOW, identity
        return f"rate_limit:api:ip:{client_ip}", self.anon_limit, self.GENERAL_WINDOW, client_ip

    async def _hit(self, client, key: str, window: int) -> tuple[int, float]:
        if client is None:
            return self.memory.hit(key, window)
        count = await client.incr(key)
        if count == 1:
            await client.expire(key, window)
        return int(count), float(window)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if request.method == "OPTIONS" or not self._is_protected_path(path):
            return await call_next(request)

        client = await self._init_redis()
        if client is None and self.redis_url and self.strict:
            logger.error("Redis do rate limit indisponível com RATE_LIMIT_STRICT=true")
            return self._rate_limit_unavailable_response()

        key, limit, window, who = self._bucket(request, path)
        try:
            count, reset_in = await self._hit(client, key, window)
        except Exception as e:
            logger.error("Erro no Redis do rate limit: %s", str(e), exc_info=True)
            if self.strict:
                return self._rate_limit_unavailable_response()
            count, reset_in = self.memory.hit(key, window)

        if count > limit:
            retry_after = max(1, int(reset_in + 0.999))
            logger.warning("Rate limit excedido: %s em %s (%s/%s em %ss)", who, path, count, limit, window)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(retry_after)},
                content={
                    "detail": "Muitas requisições em pouco tempo. Aguarde alguns segundos e tente de novo.",
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "message": f"Too many requests. Maximum {limit} requests per {window} seconds allowed.",
                    "retry_after": retry_after,
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - count))
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + reset_in))
        return response
