"""email_service: envio pelo Resend com a API mockada (nenhuma chamada real)."""

import httpx
import pytest

from app.core import http_client
from app.services import email_service


@pytest.fixture
def resend(monkeypatch):
    """Liga o envio e troca a rede por um MockTransport com respostas em fila."""
    state = {"responses": [], "calls": []}

    def handler(request: httpx.Request) -> httpx.Response:
        state["calls"].append(request)
        return state["responses"].pop(0)

    real = http_client.request_with_retry

    async def fake_request(*args, **kwargs):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await real(*args, client=c, **kwargs)

    async def no_sleep(_):
        return None

    monkeypatch.setattr(email_service, "request_with_retry", fake_request)
    monkeypatch.setattr(http_client, "_sleep", no_sleep)
    monkeypatch.setattr(email_service, "_is_enabled", lambda: True)
    monkeypatch.setattr(email_service, "_get_api_key", lambda: "re_test_fake")
    return state


async def test_sucesso_envia_remetente_do_dominio(resend):
    resend["responses"] = [httpx.Response(200, json={"id": "abc"})]
    ok = await email_service.send_email("cliente@exemplo.com", "Assunto", "<p>oi</p>")
    assert ok is True
    req = resend["calls"][0]
    assert req.headers["Authorization"] == "Bearer re_test_fake"
    assert req.headers["Idempotency-Key"]
    body = req.read().decode()
    assert "@fiscwise.com.br" in body and "cliente@exemplo.com" in body


async def test_erro_4xx_nao_repete_e_retorna_false(resend):
    resend["responses"] = [httpx.Response(422, json={"message": "invalid"})]
    ok = await email_service.send_email("x@exemplo.com", "A", "<p>b</p>")
    assert ok is False
    assert len(resend["calls"]) == 1


async def test_erro_transitorio_repete_com_a_mesma_chave(resend):
    resend["responses"] = [
        httpx.Response(503),
        httpx.Response(429),
        httpx.Response(200, json={"id": "ok"}),
    ]
    ok = await email_service.send_email("x@exemplo.com", "A", "<p>b</p>")
    assert ok is True
    assert len(resend["calls"]) == 3
    keys = {r.headers["Idempotency-Key"] for r in resend["calls"]}
    assert len(keys) == 1  # o Resend não duplica o e-mail nas tentativas


async def test_sem_chave_nao_chama_a_api(resend, monkeypatch):
    monkeypatch.setattr(email_service, "_get_api_key", lambda: "")
    ok = await email_service.send_email("x@exemplo.com", "A", "<p>b</p>")
    assert ok is False
    assert resend["calls"] == []
    assert email_service.is_configured() is False
