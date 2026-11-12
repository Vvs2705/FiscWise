"""Cliente HTTP único para serviços externos (Supabase, Resend, Mercado Pago,
OpenAI, SERPRO, webhooks de saída).

O que este módulo garante:

- timeout padrão em toda chamada (conexão 5 s, leitura 20 s), ajustável por chamada;
- `request_with_retry`: até 3 tentativas com backoff exponencial e jitter
  (0,5 s, 1 s, 2 s), só para falhas transitórias;
- nunca repete uma requisição não idempotente que pode ter chegado ao servidor.
  Com `idempotent=False` só há nova tentativa quando a conexão nem abriu
  (o pedido não saiu daqui). Com `idempotent=True` também repete em timeout de
  leitura, queda de conexão e nos status 429/502/503/504;
- falha definitiva vira `ExternalServiceError`, com mensagem em português para o
  usuário. O handler em `app/main.py` a transforma em 503/502.

Respostas HTTP com erro que não é transitório (400, 401, 404, 500...) voltam ao
chamador como resposta normal: cada integração já trata o próprio status.
"""

from __future__ import annotations

import asyncio
import logging
import random
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_CONNECT_TIMEOUT = 5.0
DEFAULT_READ_TIMEOUT = 20.0
DEFAULT_ATTEMPTS = 3
BACKOFF_BASE_SECONDS = 0.5  # 0,5 s → 1 s → 2 s

RETRYABLE_STATUS = frozenset({429, 502, 503, 504})

# Falhas em que o pedido certamente não chegou ao servidor: seguras para repetir
# mesmo em POST não idempotente.
_CONNECT_ERRORS: tuple[type[Exception], ...] = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.PoolTimeout,
)
# Falhas em que o pedido pode ter sido processado: só repete se for idempotente.
_AMBIGUOUS_ERRORS: tuple[type[Exception], ...] = (
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.ReadError,
    httpx.WriteError,
    httpx.RemoteProtocolError,
)

# Nome legível de cada serviço, usado na mensagem ao usuário.
SERVICE_LABELS = {
    "supabase_storage": "de armazenamento de arquivos",
    "resend": "de e-mail",
    "mercadopago": "de pagamento (Mercado Pago)",
    "openai": "de inteligência artificial",
    "serpro": "da Receita Federal (SERPRO)",
    "sefaz": "da SEFAZ",
    "webhook": "do webhook de destino",
}


class ExternalServiceError(Exception):
    """Serviço externo indisponível ou com resposta inválida.

    `retryable=True` → falha transitória (o usuário pode tentar de novo; HTTP 503).
    `retryable=False` → o serviço respondeu algo inesperado (HTTP 502).
    """

    def __init__(
        self,
        service: str,
        message: Optional[str] = None,
        *,
        retryable: bool = True,
        status_code: Optional[int] = None,
    ) -> None:
        self.service = service
        self.retryable = retryable
        self.upstream_status = status_code
        self.user_message = message or default_message(service, retryable)
        super().__init__(self.user_message)


def default_message(service: str, retryable: bool = True) -> str:
    label = SERVICE_LABELS.get(service, "externo")
    if retryable:
        return f"O serviço {label} não respondeu. Tente novamente em alguns minutos."
    return f"O serviço {label} retornou um erro inesperado. Tente novamente mais tarde."


def make_timeout(
    connect: float = DEFAULT_CONNECT_TIMEOUT, read: float = DEFAULT_READ_TIMEOUT
) -> httpx.Timeout:
    return httpx.Timeout(read, connect=connect)


@asynccontextmanager
async def external_client(
    *,
    connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
    read_timeout: float = DEFAULT_READ_TIMEOUT,
    **kwargs: Any,
) -> AsyncIterator[httpx.AsyncClient]:
    """`httpx.AsyncClient` com o timeout padrão. Repassa `base_url`, `cert` etc."""
    kwargs.setdefault("timeout", make_timeout(connect_timeout, read_timeout))
    # Resolve httpx.AsyncClient na hora da chamada: testes que fazem patch em
    # `httpx.AsyncClient` continuam funcionando.
    async with httpx.AsyncClient(**kwargs) as client:
        yield client


def _backoff_delay(attempt: int) -> float:
    """attempt 1 → ~0,5 s, 2 → ~1 s, 3 → ~2 s, com jitter de ±25 %."""
    base = BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
    return base * random.uniform(0.75, 1.25)


async def _sleep(seconds: float) -> None:  # separado para os testes zerarem a espera
    await asyncio.sleep(seconds)


async def request_with_retry(
    method: str,
    url: str,
    *,
    service: str,
    idempotent: Optional[bool] = None,
    client: Optional[httpx.AsyncClient] = None,
    attempts: int = DEFAULT_ATTEMPTS,
    connect_timeout: float = DEFAULT_CONNECT_TIMEOUT,
    read_timeout: float = DEFAULT_READ_TIMEOUT,
    client_kwargs: Optional[dict[str, Any]] = None,
    **request_kwargs: Any,
) -> httpx.Response:
    """Faz a requisição com retry só para falhas transitórias.

    `idempotent` padrão: True para GET/HEAD/OPTIONS/PUT/DELETE, False para POST/PATCH.
    Um POST só é tratado como idempotente se o chamador disser `idempotent=True`
    (ex.: o provedor honra `Idempotency-Key`, ou é uma consulta).

    `client`: reaproveita um cliente já aberto (ex.: injetado nos testes). Sem ele,
    abre um com o timeout padrão para a chamada.
    """
    method = method.upper()
    if idempotent is None:
        idempotent = method in {"GET", "HEAD", "OPTIONS", "PUT", "DELETE"}
    attempts = max(1, attempts)

    async def _once(c: httpx.AsyncClient) -> httpx.Response:
        # Usa client.post/get/... (e não client.request) para manter compatíveis
        # os testes que simulam o cliente com mocks desses métodos.
        verb = method.lower()
        if verb in {"get", "post", "put", "patch", "delete"}:
            return await getattr(c, verb)(url, **request_kwargs)
        return await c.request(method, url, **request_kwargs)

    last_exc: Optional[Exception] = None
    last_resp: Optional[httpx.Response] = None
    for attempt in range(1, attempts + 1):
        try:
            if client is not None:
                resp = await _once(client)
            else:
                async with external_client(
                    connect_timeout=connect_timeout,
                    read_timeout=read_timeout,
                    **(client_kwargs or {}),
                ) as c:
                    resp = await _once(c)
        except _CONNECT_ERRORS as exc:
            last_exc = exc
            retry = True
        except _AMBIGUOUS_ERRORS as exc:
            last_exc = exc
            retry = idempotent
        except httpx.HTTPError as exc:  # erro de transporte não classificado
            last_exc = exc
            retry = False
        else:
            if resp.status_code in RETRYABLE_STATUS and idempotent and attempt < attempts:
                last_resp = resp
                logger.warning(
                    "external_retry service=%s status=%s tentativa=%s/%s",
                    service, resp.status_code, attempt, attempts,
                )
                await _sleep(_backoff_delay(attempt))
                continue
            return resp

        if not retry or attempt >= attempts:
            break
        logger.warning(
            "external_retry service=%s erro=%s tentativa=%s/%s",
            service, type(last_exc).__name__, attempt, attempts,
        )
        await _sleep(_backoff_delay(attempt))

    if last_exc is None and last_resp is not None:  # pragma: no cover - laço sempre retorna
        return last_resp
    logger.warning(
        "external_failed service=%s method=%s erro=%s", service, method, type(last_exc).__name__
    )
    raise ExternalServiceError(service, retryable=True) from last_exc


def raise_for_upstream_status(resp: httpx.Response, service: str) -> None:
    """Converte 5xx/429 do provedor em `ExternalServiceError` (para chamadores que
    não têm tratamento próprio de status)."""
    if resp.status_code in RETRYABLE_STATUS:
        raise ExternalServiceError(service, retryable=True, status_code=resp.status_code)
    if resp.status_code >= 500:
        raise ExternalServiceError(service, retryable=False, status_code=resp.status_code)
