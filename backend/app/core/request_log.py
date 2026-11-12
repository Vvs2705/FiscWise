"""
Log estruturado por requisição (uma linha JSON no stdout) + header Server-Timing.

Por que não o SDK do OpenTelemetry: ele pesa no cold start do Cloud Run
(min-instances 0) e precisaria de um coletor. O Cloud Logging já entende JSON
no stdout como *structured log*: `severity`, `httpRequest` e
`logging.googleapis.com/trace` viram campos nativos (filtro, latência,
correlação com o Cloud Trace) sem custo extra.

É um middleware ASGI **puro** (não `BaseHTTPMiddleware`): não bufferiza o
corpo da resposta, não cria task extra e só olha a mensagem
`http.response.start` para pegar o status e acrescentar o header.

Privacidade (LGPD): nunca loga query string, corpo, headers de autenticação,
cookies, IP, e-mail nem CPF/CNPJ. A URL registrada é o *template* da rota
(`/api/v1/clients/{client_id}`); quando nenhuma rota casa (404), o caminho
passa por `_scrub_path`, que mascara segmentos com e-mail, números longos
(CPF/CNPJ) e tokens.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from typing import Any, Callable

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_ENABLED_ENVIRONMENTS = {"production", "staging"}
_TRUTHY = {"1", "true", "yes", "on"}

_UA_MAX = 256
_NUMERIC_DOC = re.compile(r"\d[\d.\-/]*\d")
_TOKEN_LIKE = re.compile(r"^[A-Za-z0-9_\-]{24,}$")
_CLOUD_TRACE = re.compile(r"^([0-9a-fA-F]{32})(?:/(\d+))?(?:;o=([01]))?$")
_TRACEPARENT = re.compile(r"^[0-9a-f]{2}-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


def request_log_enabled(environment: str, flag: str | None = None) -> bool:
    """Liga em production/staging, ou quando REQUEST_LOG_JSON=true."""
    if flag is None:
        flag = os.getenv("REQUEST_LOG_JSON", "")
    return environment in _ENABLED_ENVIRONMENTS or flag.strip().lower() in _TRUTHY


def _scrub_segment(segment: str) -> str:
    if not segment or segment == ":redacted":
        return segment
    if "@" in segment or "%40" in segment.lower():
        return ":redacted"
    if _TOKEN_LIKE.match(segment):
        return ":id"
    return segment


def _mask_long_number(match: re.Match[str]) -> str:
    # CPF (11 dígitos), CNPJ (14) e qualquer número longo, mesmo formatado com
    # . - / (o "/" do CNPJ atravessaria a divisão por segmentos). Ids curtos ficam.
    return ":redacted" if sum(c.isdigit() for c in match.group(0)) >= 11 else match.group(0)


def _scrub_path(path: str) -> str:
    path = _NUMERIC_DOC.sub(_mask_long_number, path)
    return "/".join(_scrub_segment(s) for s in path.split("/"))


def _route_template(scope: Scope) -> str | None:
    """Template completo da rota (`/api/v1/clients/{client_id}`).

    Em routers incluídos com prefixo, o FastAPI recente deixa em
    scope["route"].path só a parte relativa (`/clients/{client_id}`). O
    prefixo é recuperado achando o menor sufixo do caminho real que casa com
    o regex da rota; o que vem antes é o prefixo (sem parâmetros).
    """
    route = scope.get("route")
    template = getattr(route, "path", None)
    if not template:
        return None
    regex = getattr(route, "path_regex", None)
    path = scope.get("path", "")
    if regex is None or regex.match(path):
        return template
    for i, char in enumerate(path):
        if char == "/" and i > 0 and regex.match(path[i:]):
            return path[:i] + template
    return template


def _header(scope: Scope, name: bytes) -> str | None:
    for key, value in scope.get("headers") or ():
        if key == name:
            return value.decode("latin-1")
    return None


def _trace_fields(scope: Scope, project_id: str | None) -> dict[str, Any]:
    """Extrai trace/span de traceparent (W3C) ou X-Cloud-Trace-Context."""
    trace_id = span_id = None
    sampled: bool | None = None

    raw = _header(scope, b"traceparent")
    match = _TRACEPARENT.match(raw.strip()) if raw else None
    if match:
        trace_id, span_id = match.group(1), match.group(2)
        sampled = bool(int(match.group(3), 16) & 1)
    else:
        raw = _header(scope, b"x-cloud-trace-context")
        match = _CLOUD_TRACE.match(raw.strip()) if raw else None
        if match:
            trace_id = match.group(1).lower()
            if match.group(2):
                span_id = format(int(match.group(2)) & 0xFFFFFFFFFFFFFFFF, "016x")
            if match.group(3) is not None:
                sampled = match.group(3) == "1"

    if not trace_id:
        return {}
    fields: dict[str, Any] = {
        "logging.googleapis.com/trace": (
            f"projects/{project_id}/traces/{trace_id}" if project_id else trace_id
        ),
    }
    if span_id:
        fields["logging.googleapis.com/spanId"] = span_id
    if sampled is not None:
        fields["logging.googleapis.com/trace_sampled"] = sampled
    return fields


def _severity(status: int) -> str:
    if status >= 500:
        return "ERROR"
    if status >= 400:
        return "WARNING"
    return "INFO"


def _write_line(line: str) -> None:
    # sys.stdout é resolvido na hora da chamada (o capsys do pytest o substitui).
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


class RequestLogMiddleware:
    """Mede a duração da requisição, emite 1 linha JSON e devolve Server-Timing."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        project_id: str | None = None,
        emit: Callable[[str], None] | None = None,
    ) -> None:
        self.app = app
        self.project_id = (
            project_id
            or os.getenv("GOOGLE_CLOUD_PROJECT")
            or os.getenv("GCP_PROJECT")
            or None
        )
        self.emit = emit or _write_line

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                dur_ms = (time.perf_counter() - start) * 1000
                # Tempo até os headers (o que o navegador mostra no DevTools).
                MutableHeaders(scope=message).append("Server-Timing", f"app;dur={dur_ms:.1f}")
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            # Duração total, inclusive o envio do corpo. Numa exceção não tratada
            # o status fica 500 (é o que o ServerErrorMiddleware, mais externo, responde).
            duration = time.perf_counter() - start
            try:
                self.emit(self._build_line(scope, status_code, duration))
            except Exception:  # noqa: BLE001 - log nunca derruba a requisição
                pass

    def _build_line(self, scope: Scope, status_code: int, duration: float) -> str:
        route_path = _route_template(scope)
        url = route_path or _scrub_path(scope.get("path", ""))

        # request.state.tenant_id (gravado pelo TenantMiddleware) mora em scope["state"].
        state = scope.get("state")
        tenant_id = state.get("tenant_id") if isinstance(state, dict) else None

        user_agent = _header(scope, b"user-agent") or ""
        payload: dict[str, Any] = {
            "severity": _severity(status_code),
            "message": "request",
            "httpRequest": {
                "requestMethod": scope.get("method", ""),
                "requestUrl": url,
                "status": status_code,
                "latency": f"{duration:.3f}s",
                "userAgent": user_agent[:_UA_MAX],
                "protocol": f"HTTP/{scope.get('http_version', '1.1')}",
            },
            "route": route_path or "unmatched",
            "duration_ms": round(duration * 1000, 1),
        }
        if tenant_id:
            payload["tenant_id"] = str(tenant_id)
        payload.update(_trace_fields(scope, self.project_id))
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
