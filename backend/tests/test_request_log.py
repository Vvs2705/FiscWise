"""Log estruturado por requisição + Server-Timing (app/core/request_log.py)."""

import json
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

from app.core.middleware import TenantMiddleware
from app.core.request_log import (
    RequestLogMiddleware,
    _scrub_path,
    request_log_enabled,
)

TOKEN = "eyJhbGciOiJIUzI1NiJ9.secret-token-value.signature"
EMAIL = "fulano.contador@example.com"
CPF = "123.456.789-09"
CNPJ = "12345678000195"


def _mini_app(project_id: str | None = None) -> FastAPI:
    app = FastAPI()

    @app.get("/api/v1/clients/{client_id}")
    async def get_client(client_id: str):
        return {"id": client_id}

    @app.get("/live")
    async def live():
        return {"status": "alive"}

    @app.get("/boom")
    async def boom():
        raise HTTPException(status_code=503, detail="fora")

    @app.get("/stream")
    async def stream():
        async def gen():
            for chunk in (b"a", b"b", b"c"):
                yield chunk

        return StreamingResponse(gen(), media_type="text/plain")

    app.add_middleware(TenantMiddleware)
    app.add_middleware(RequestLogMiddleware, project_id=project_id)
    return app


def _lines(captured: str) -> list[dict]:
    out = []
    for raw in captured.splitlines():
        raw = raw.strip()
        if raw.startswith("{") and '"message":"request"' in raw:
            out.append(json.loads(raw))
    return out


def test_enabled_only_in_prod_staging_or_flag():
    assert request_log_enabled("production", "")
    assert request_log_enabled("staging", "false")
    assert not request_log_enabled("development", "")
    assert not request_log_enabled("development", "False")
    assert request_log_enabled("development", "true")
    assert request_log_enabled("test", "True")


def test_server_timing_header_and_json_line(capsys):
    client = TestClient(_mini_app())
    tenant = str(uuid.uuid4())
    capsys.readouterr()

    response = client.get(
        f"/api/v1/clients/{CNPJ}?email={EMAIL}&token={TOKEN}",
        headers={
            "X-Tenant-ID": tenant,
            "Authorization": f"Bearer {TOKEN}",
            "Cookie": f"session={TOKEN}",
            "User-Agent": "pytest-agent/1.0",
        },
    )

    assert response.status_code == 200
    timing = response.headers.get("server-timing")
    assert timing is not None and timing.startswith("app;dur=")
    assert float(timing.split("=", 1)[1]) >= 0

    captured = capsys.readouterr().out
    lines = _lines(captured)
    assert len(lines) == 1
    line = lines[0]
    assert line["severity"] == "INFO"
    assert line["route"] == "/api/v1/clients/{client_id}"
    assert line["tenant_id"] == tenant
    assert line["httpRequest"]["requestMethod"] == "GET"
    assert line["httpRequest"]["requestUrl"] == "/api/v1/clients/{client_id}"
    assert line["httpRequest"]["status"] == 200
    assert line["httpRequest"]["latency"].endswith("s")
    assert line["httpRequest"]["userAgent"] == "pytest-agent/1.0"
    assert isinstance(line["duration_ms"], (int, float))

    # Nada sensível: token, e-mail, CNPJ do path, query string, cookie.
    for secret in (TOKEN, "secret-token-value", EMAIL, CNPJ, "Bearer", "session=", "?"):
        assert secret not in captured


def test_error_status_is_logged_with_severity(capsys):
    client = TestClient(_mini_app())
    capsys.readouterr()
    response = client.get("/boom")  # /boom não está isento: Tenant devolve 400
    assert response.status_code == 400
    assert "server-timing" in response.headers
    line = _lines(capsys.readouterr().out)[0]
    assert line["severity"] == "WARNING"
    assert line["httpRequest"]["status"] == 400
    assert "tenant_id" not in line


def test_streaming_response_not_buffered_and_logged(capsys):
    client = TestClient(_mini_app())
    capsys.readouterr()
    response = client.get("/stream", headers={"X-Tenant-ID": str(uuid.uuid4())})
    assert response.status_code == 200
    assert response.text == "abc"
    assert "server-timing" in response.headers
    assert len(_lines(capsys.readouterr().out)) == 1


def test_unmatched_path_is_scrubbed(capsys):
    client = TestClient(_mini_app())
    capsys.readouterr()
    client.get(f"/live/{EMAIL}/{CPF}/{TOKEN.replace('.', '')}")
    captured = capsys.readouterr().out
    line = _lines(captured)[0]
    assert line["route"] == "unmatched"
    assert EMAIL not in captured and CPF not in captured
    assert line["httpRequest"]["requestUrl"] == "/live/:redacted/:redacted/:id"


def test_scrub_keeps_short_ids():
    assert _scrub_path("/api/v1/clients/42") == "/api/v1/clients/42"
    assert _scrub_path("/x/2026-11-12") == "/x/2026-11-12"
    assert _scrub_path("/x/12.345.678/0001-95/y") == "/x/:redacted/y"  # CNPJ com "/"
    assert _scrub_path("/x/12345678000195") == "/x/:redacted"
    assert _scrub_path("/x/123.456.789-09") == "/x/:redacted"


def test_cloud_trace_header_is_correlated(capsys):
    client = TestClient(_mini_app(project_id="proj-x"))
    capsys.readouterr()
    trace = "105445aa7843bc8bf206b12000100000"
    client.get("/live", headers={"X-Cloud-Trace-Context": f"{trace}/1;o=1"})
    line = _lines(capsys.readouterr().out)[0]
    assert line["logging.googleapis.com/trace"] == f"projects/proj-x/traces/{trace}"
    assert line["logging.googleapis.com/spanId"] == "0000000000000001"
    assert line["logging.googleapis.com/trace_sampled"] is True


def test_traceparent_takes_precedence(capsys):
    client = TestClient(_mini_app())
    capsys.readouterr()
    tp = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    client.get("/live", headers={"traceparent": tp, "X-Cloud-Trace-Context": "a" * 32})
    line = _lines(capsys.readouterr().out)[0]
    assert line["logging.googleapis.com/trace"] == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert line["logging.googleapis.com/spanId"] == "00f067aa0ba902b7"


def test_wraps_real_app_stack_without_leaking_token():
    """Pilha real (CORS → RateLimit → Tenant → rota) embrulhada pelo middleware."""
    from app.main import app as real_app

    lines: list[str] = []
    client = TestClient(RequestLogMiddleware(real_app, emit=lines.append))

    response = client.get("/live")
    assert response.status_code == 200
    assert response.headers["server-timing"].startswith("app;dur=")

    response = client.get(
        "/api/v1/clients",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "X-Tenant-ID": "00000000-0000-0000-0000-000000000000",
        },
    )
    assert response.status_code in (401, 403)
    assert len(lines) == 2
    assert all(TOKEN not in raw and "Bearer" not in raw for raw in lines)
    parsed = json.loads(lines[-1])
    assert parsed["httpRequest"]["status"] == response.status_code
    # Router incluído com prefixo /api/v1: o template sai completo.
    assert parsed["route"] == "/api/v1/clients"


def test_route_template_keeps_router_prefix(capsys):
    from fastapi import APIRouter

    inner = APIRouter()

    @inner.get("/items/{item_id}")
    async def item(item_id: str):
        return {"id": item_id}

    outer = APIRouter()
    outer.include_router(inner, prefix="/v9")
    app = FastAPI()
    app.include_router(outer, prefix="/api")
    app.add_middleware(RequestLogMiddleware)

    capsys.readouterr()
    assert TestClient(app).get(f"/api/v9/items/{CNPJ}").status_code == 200
    line = _lines(capsys.readouterr().out)[0]
    assert line["route"] == "/api/v9/items/{item_id}"
    assert line["httpRequest"]["requestUrl"] == "/api/v9/items/{item_id}"
