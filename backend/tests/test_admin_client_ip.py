"""IP dos alertas de admin não pode ser forjado pelo X-Forwarded-For (compliance #38/#32)."""

from starlette.requests import Request

from app.api.v1.endpoints import admin


def _request(xff: str) -> Request:
    return Request({
        "type": "http",
        "headers": [(b"x-forwarded-for", xff.encode())],
        "client": ("10.0.0.1", 1234),
    })


def test_admin_ip_usa_a_entrada_acrescentada_pelo_cloud_run():
    # Cliente manda "1.2.3.4"; o Cloud Run acrescenta o IP real no fim.
    assert admin._get_client_ip(_request("1.2.3.4, 203.0.113.9")) == "203.0.113.9"


def test_admin_ip_sem_header_usa_o_socket():
    req = Request({"type": "http", "headers": [], "client": ("10.0.0.1", 1234)})
    assert admin._get_client_ip(req) == "10.0.0.1"
