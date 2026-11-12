"""Retry/backoff do cliente HTTP externo, handler de ExternalServiceError e cache TTL."""

import asyncio

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core import http_client
from app.core.http_client import (
    ExternalServiceError,
    _backoff_delay,
    request_with_retry,
)
from app.core.ttl_cache import AsyncTTLCache


@pytest.fixture(autouse=True)
def _sem_espera(monkeypatch):
    delays = []

    async def fake_sleep(seconds):
        delays.append(seconds)

    monkeypatch.setattr(http_client, "_sleep", fake_sleep)
    return delays


def _client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_get_repete_em_503_e_depois_sucede(_sem_espera):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503) if len(calls) < 3 else httpx.Response(200, json={"ok": 1})

    async with _client(handler) as c:
        resp = await request_with_retry("GET", "https://x/a", service="mercadopago", client=c)
    assert resp.status_code == 200
    assert len(calls) == 3
    assert len(_sem_espera) == 2
    assert 0.375 <= _sem_espera[0] <= 0.625 and 0.75 <= _sem_espera[1] <= 1.25


async def test_get_esgota_tentativas_em_status_devolve_ultima_resposta():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(504)

    async with _client(handler) as c:
        resp = await request_with_retry("GET", "https://x/a", service="serpro", client=c)
    assert resp.status_code == 504
    assert len(calls) == 3


async def test_erro_nao_transitorio_nao_repete():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(400)

    async with _client(handler) as c:
        resp = await request_with_retry("GET", "https://x/a", service="serpro", client=c)
    assert resp.status_code == 400 and len(calls) == 1


async def test_post_nao_idempotente_nao_repete_em_503():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(503)

    async with _client(handler) as c:
        resp = await request_with_retry("POST", "https://x/preapproval", service="mercadopago", client=c)
    assert resp.status_code == 503 and len(calls) == 1


async def test_post_nao_idempotente_nao_repete_em_timeout_de_leitura():
    calls = []

    def handler(request):
        calls.append(1)
        raise httpx.ReadTimeout("lento", request=request)

    async with _client(handler) as c:
        with pytest.raises(ExternalServiceError) as exc:
            await request_with_retry("POST", "https://x/chat", service="openai", client=c)
    assert len(calls) == 1
    assert exc.value.service == "openai" and exc.value.retryable


async def test_post_nao_idempotente_repete_se_conexao_nem_abriu():
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) == 1:
            raise httpx.ConnectError("recusada", request=request)
        return httpx.Response(201)

    async with _client(handler) as c:
        resp = await request_with_retry("POST", "https://x/up", service="supabase_storage", client=c)
    assert resp.status_code == 201 and len(calls) == 2


async def test_post_idempotente_repete_em_timeout_de_leitura():
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) < 3:
            raise httpx.ReadTimeout("lento", request=request)
        return httpx.Response(200)

    async with _client(handler) as c:
        resp = await request_with_retry(
            "POST", "https://x/emails", service="resend", idempotent=True, client=c
        )
    assert resp.status_code == 200 and len(calls) == 3


async def test_falha_definitiva_levanta_external_service_error_com_mensagem():
    def handler(request):
        raise httpx.ConnectError("fora", request=request)

    async with _client(handler) as c:
        with pytest.raises(ExternalServiceError) as exc:
            await request_with_retry("GET", "https://x", service="sefaz", client=c)
    assert str(exc.value) == "O serviço da SEFAZ não respondeu. Tente novamente em alguns minutos."


def test_backoff_exponencial_com_jitter():
    for attempt, base in ((1, 0.5), (2, 1.0), (3, 2.0)):
        for _ in range(20):
            assert base * 0.75 <= _backoff_delay(attempt) <= base * 1.25


async def test_storage_upload_fora_do_ar_vira_503(client_with_auth_a, monkeypatch):
    """Ponta a ponta: o handler global transforma a falha em 503 com error_code."""
    from app.api.v1.endpoints import operations
    from app.core.config import settings

    monkeypatch.setattr(settings, "SUPABASE_URL", "https://storage.invalid")
    monkeypatch.setattr(settings, "SUPABASE_SECRET_KEY", "x")

    async def fora(*_a, **_k):
        raise ExternalServiceError("supabase_storage")

    monkeypatch.setattr("app.core.http_client.request_with_retry", fora)
    http, *_ = client_with_auth_a
    resp = http.post("/api/v1/documents/upload", files={"file": ("a.pdf", b"%PDF-1")})
    assert resp.status_code == 503, resp.text
    body = resp.json()
    assert body["error_code"] == "EXTERNAL_SERVICE_UNAVAILABLE"
    assert body["service"] == "supabase_storage"
    assert "armazenamento" in body["detail"]
    assert operations  # módulo importado


def test_handler_retryable_false_vira_502():
    from app.main import external_service_error_handler

    app = FastAPI()
    app.add_exception_handler(ExternalServiceError, external_service_error_handler)

    @app.get("/x")
    async def x():
        raise ExternalServiceError("mercadopago", retryable=False)

    resp = TestClient(app).get("/x")
    assert resp.status_code == 502
    assert resp.json()["service"] == "mercadopago"


async def test_mercadopago_get_falha_vira_gateway_error(monkeypatch):
    from app.services import mercadopago

    async def fora(*_a, **_k):
        raise ExternalServiceError("mercadopago")

    monkeypatch.setattr(mercadopago, "request_with_retry", fora)
    gw = mercadopago.GatewayMercadoPago()
    gw._token = "t"
    with pytest.raises(mercadopago.GatewayPagamentoError):
        await gw.obter_pagamento("1")


async def test_mercadopago_criar_assinatura_nao_e_repetida(monkeypatch):
    from app.services import mercadopago

    chamadas = []

    async def capturar(method, url, **kw):
        chamadas.append((method, kw.get("idempotent")))
        return httpx.Response(201, json={"id": "p1", "init_point": "u"})

    monkeypatch.setattr(mercadopago, "request_with_retry", capturar)
    gw = mercadopago.GatewayMercadoPago()
    gw._token = "t"
    await gw.criar_assinatura(plano_nome="P", preco_mensal=10, email_pagador="a@b.c", referencia="r")
    assert chamadas == [("POST", False)]


# ── Cache TTL ───────────────────────────────────────────────────────────────

async def test_cache_ttl_expira_e_invalida(monkeypatch):
    cache = AsyncTTLCache("t", ttl_seconds=300)
    agora = [1000.0]
    monkeypatch.setattr(cache, "_now", lambda: agora[0])
    loads = []

    async def loader():
        loads.append(1)
        return len(loads)

    assert await cache.get_or_load("k", loader) == 1
    assert await cache.get_or_load("k", loader) == 1  # hit
    agora[0] += 299
    assert await cache.get_or_load("k", loader) == 1
    agora[0] += 2  # passou de 300 s
    assert await cache.get_or_load("k", loader) == 2
    cache.invalidate()
    assert await cache.get_or_load("k", loader) == 3
    assert cache.hits == 2 and cache.misses == 3


async def test_cache_requisicoes_frias_simultaneas_fazem_uma_carga():
    cache = AsyncTTLCache("t")
    loads = []

    async def loader():
        loads.append(1)
        await asyncio.sleep(0.01)
        return "v"

    results = await asyncio.gather(*(cache.get_or_load("k", loader) for _ in range(5)))
    assert results == ["v"] * 5 and len(loads) == 1


async def test_plans_endpoint_usa_cache_e_header(client, test_db):
    from decimal import Decimal

    from app.core.ttl_cache import plans_cache
    from app.models.plan import Plan

    test_db.add(Plan(slug="premium", name="Premium", price_monthly=Decimal("99.90"), active=True))
    test_db.add(Plan(slug="free", name="Free", price_monthly=None, active=True))
    await test_db.commit()

    import uuid as _uuid

    h = {"X-Tenant-ID": str(_uuid.uuid4())}  # exigido pelo TenantMiddleware; não muda a resposta
    r1 = client.get("/api/v1/subscription/plans", headers=h)
    assert r1.status_code == 200
    assert r1.headers["cache-control"] == "public, max-age=300"
    assert [p["slug"] for p in r1.json()] == ["free", "premium"]

    # Mudança direta no banco não aparece até invalidar (TTL 5 min).
    test_db.add(Plan(slug="intermediario", name="Inter", price_monthly=Decimal("49.90"), active=True))
    await test_db.commit()
    assert len(client.get("/api/v1/subscription/plans", headers=h).json()) == 2
    assert plans_cache.hits >= 1

    from app.services.catalog_cache import invalidate_plans

    invalidate_plans()
    slugs = [p["slug"] for p in client.get("/api/v1/subscription/plans", headers=h).json()]
    assert slugs == ["free", "intermediario", "premium"]
