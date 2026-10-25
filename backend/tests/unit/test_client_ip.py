"""IP usado no rate limit não pode ser escolhido pelo cliente (SEC-4)."""

from starlette.requests import Request

from app.core.auth_rate_limiter import get_client_ip


def _req(headers: dict) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    return Request({"type": "http", "headers": raw, "client": ("10.0.0.1", 1234)})


def test_prefere_fly_client_ip():
    req = _req({"Fly-Client-IP": "200.1.1.1", "X-Forwarded-For": "1.2.3.4, 200.1.1.1"})
    assert get_client_ip(req) == "200.1.1.1"


def test_xff_forjado_nao_troca_o_ip():
    assert get_client_ip(_req({"X-Forwarded-For": "6.6.6.6, 200.1.1.1"})) == "200.1.1.1"


def test_sem_proxy_usa_conexao():
    assert get_client_ip(_req({})) == "10.0.0.1"
