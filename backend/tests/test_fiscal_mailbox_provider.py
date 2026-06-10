"""Tests for the fiscal mailbox provider factory and the SERPRO provider."""

import json

import httpx
import pytest

from app.core.config import settings
from app.domain.fiscal_mailbox.integrations.base import ProviderNotConfiguredError
from app.domain.fiscal_mailbox.integrations.factory import build_fiscal_mailbox_provider
from app.domain.fiscal_mailbox.integrations.mock import MockFiscalMailboxProvider
from app.domain.fiscal_mailbox.integrations.serpro import (
    SerproIntegraContadorProvider,
    _parse_serpro_date,
)

TENANT_ID = "9df4b224-c8dc-4cdf-9bb6-40af6d206e62"


@pytest.mark.asyncio
async def test_factory_defaults_to_mock(monkeypatch):
    monkeypatch.setattr(settings, "FISCAL_MAILBOX_PROVIDER", "mock")
    provider = await build_fiscal_mailbox_provider(None, TENANT_ID)
    assert isinstance(provider, MockFiscalMailboxProvider)


@pytest.mark.asyncio
async def test_factory_serpro_without_credentials_fails_closed(monkeypatch):
    monkeypatch.setattr(settings, "FISCAL_MAILBOX_PROVIDER", "serpro")
    monkeypatch.setattr(settings, "SERPRO_CONSUMER_KEY", "")
    monkeypatch.setattr(settings, "SERPRO_CONSUMER_SECRET", "")
    with pytest.raises(ProviderNotConfiguredError):
        await build_fiscal_mailbox_provider(None, TENANT_ID)


@pytest.mark.asyncio
async def test_factory_unknown_provider_fails_closed(monkeypatch):
    monkeypatch.setattr(settings, "FISCAL_MAILBOX_PROVIDER", "banana")
    with pytest.raises(ProviderNotConfiguredError):
        await build_fiscal_mailbox_provider(None, TENANT_ID)


def _serpro_transport(messages_payload):
    """MockTransport emulating the SERPRO auth + Consultar endpoints."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/authenticate"):
            return httpx.Response(
                200,
                json={"access_token": "tok-123", "jwt_token": "jwt-456", "expires_in": 3600},
            )
        if request.url.path.endswith("/Consultar"):
            assert request.headers["Authorization"] == "Bearer tok-123"
            assert request.headers["jwt_token"] == "jwt-456"
            envelope = json.loads(request.content)
            assert envelope["pedidoDados"]["idSistema"] == "CAIXAPOSTAL"
            return httpx.Response(
                200,
                json={"status": 200, "dados": json.dumps(messages_payload)},
            )
        return httpx.Response(404)

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_serpro_provider_maps_messages_to_contract():
    payload = {
        "mensagens": [
            {
                "isn": "0001",
                "assunto": "Intimacao DCTFWeb",
                "dataEnvio": "20260601120000",
                "relevancia": "1",
                "origem": "Receita Federal",
                "sistema": "DCTFWEB",
            },
            {
                # No id -> skipped by the mapper
                "assunto": "Mensagem sem id",
            },
        ]
    }
    async with httpx.AsyncClient(transport=_serpro_transport(payload)) as http_client:
        provider = SerproIntegraContadorProvider(
            [{"cnpj": "12.345.678/0001-90", "name": "Tech Solutions Ltda"}],
            consumer_key="key",
            consumer_secret="secret",
            auth_url="https://auth.test/authenticate",
            base_url="https://gw.test/integra-contador/v1",
            contratante_cnpj="11111111000111",
            autor_pedido_cnpj="11111111000111",
            http_client=http_client,
        )
        messages = await provider.fetch_messages(TENANT_ID)

    assert len(messages) == 1
    msg = messages[0]
    assert msg["external_id"] == "serpro-12345678000190-0001"
    assert msg["subject"] == "Intimacao DCTFWeb"
    assert msg["client_name"] == "Tech Solutions Ltda"
    assert msg["risk"] == "high"
    assert msg["received_at"].startswith("2026-06-01T12:00:00")
    assert "DCTFWEB" in msg["tags"]


@pytest.mark.asyncio
async def test_serpro_provider_partial_failure_does_not_abort_sync():
    """A contribuinte whose Consultar call errors is skipped, not fatal."""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/authenticate"):
            return httpx.Response(
                200, json={"access_token": "tok", "expires_in": 3600}
            )
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(500, json={"erro": "indisponivel"})
        return httpx.Response(
            200,
            json={"status": 200, "dados": json.dumps({"mensagens": [{"isn": "9", "assunto": "OK"}]})},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        provider = SerproIntegraContadorProvider(
            [
                {"cnpj": "11111111000111", "name": "Falha SA"},
                {"cnpj": "22222222000122", "name": "Sucesso ME"},
            ],
            consumer_key="key",
            consumer_secret="secret",
            auth_url="https://auth.test/authenticate",
            base_url="https://gw.test/v1",
            contratante_cnpj="11111111000111",
            autor_pedido_cnpj="11111111000111",
            http_client=http_client,
        )
        messages = await provider.fetch_messages(TENANT_ID)

    assert len(messages) == 1
    assert messages[0]["external_id"] == "serpro-22222222000122-9"


def test_parse_serpro_date_formats():
    assert _parse_serpro_date("20260601").startswith("2026-06-01")
    assert _parse_serpro_date("20260601120000").startswith("2026-06-01T12:00:00")
    assert _parse_serpro_date("01/06/2026").startswith("2026-06-01")
    assert _parse_serpro_date("2026-06-01T12:00:00Z").startswith("2026-06-01")
    assert _parse_serpro_date("") is None
    assert _parse_serpro_date("not-a-date") is None
