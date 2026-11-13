"""Rate limit por usuário em toda a API (app/core/rate_limit.py)."""

import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.rate_limit import MemoryRateCounter, RateLimitMiddleware
from app.core.security import create_access_token, create_device_token


def _app(user_limit=3, anon_limit=2) -> TestClient:
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, redis_url=None, user_limit=user_limit, anon_limit=anon_limit)

    @app.get("/api/v1/clients")
    async def clients():
        return {"ok": True}

    @app.get("/api/v1/deadlines")
    async def deadlines():
        return {"ok": True}

    @app.get("/live")
    async def live():
        return {"status": "alive"}

    return TestClient(app)


def _bearer(user_id: str | None = None) -> dict:
    token = create_access_token(user_id or str(uuid.uuid4()), str(uuid.uuid4()), "owner")
    return {"Authorization": f"Bearer {token}"}


def test_limite_por_usuario_vale_para_a_api_toda():
    http = _app(user_limit=3)
    alice = _bearer()
    # rotas diferentes somam no mesmo balde do usuário
    assert [http.get(p, headers=alice).status_code for p in ("/api/v1/clients", "/api/v1/deadlines", "/api/v1/clients")] == [200] * 3
    resp = http.get("/api/v1/deadlines", headers=alice)
    assert resp.status_code == 429
    assert resp.json()["error_code"] == "RATE_LIMIT_EXCEEDED"
    assert 1 <= int(resp.headers["Retry-After"]) <= 60

    # outro usuário no mesmo IP não é afetado
    bob = _bearer()
    assert http.get("/api/v1/clients", headers=bob).status_code == 200


def test_mesmo_usuario_com_tokens_diferentes_divide_o_balde():
    http = _app(user_limit=2)
    user_id = str(uuid.uuid4())
    assert http.get("/api/v1/clients", headers=_bearer(user_id)).status_code == 200
    # token de dispositivo do mesmo usuário fora do /sync conta no mesmo balde
    device = create_device_token(user_id, str(uuid.uuid4()), "owner", str(uuid.uuid4()))
    assert http.get("/api/v1/clients", headers={"Authorization": f"Bearer {device}"}).status_code == 200
    assert http.get("/api/v1/clients", headers=_bearer(user_id)).status_code == 429


def test_sem_credencial_ou_token_forjado_limita_por_ip():
    http = _app(user_limit=100, anon_limit=2)
    forjado = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ4In0.assinatura-falsa"}
    assert http.get("/api/v1/clients").status_code == 200
    assert http.get("/api/v1/clients", headers=forjado).status_code == 200
    assert http.get("/api/v1/clients").status_code == 429
    # com credencial válida o balde é o do usuário
    assert http.get("/api/v1/clients", headers=_bearer()).status_code == 200


def test_sondas_e_preflight_ficam_fora():
    http = _app(anon_limit=1)
    assert all(http.get("/live").status_code == 200 for _ in range(5))
    assert all(http.options("/api/v1/clients").status_code in (200, 405) for _ in range(5))
    assert http.get("/api/v1/clients").status_code == 200


def test_resposta_traz_cabecalhos_de_limite():
    http = _app(user_limit=5)
    resp = http.get("/api/v1/clients", headers=_bearer())
    assert resp.headers["X-RateLimit-Limit"] == "5"
    assert resp.headers["X-RateLimit-Remaining"] == "4"


def test_contador_em_memoria_zera_a_janela_e_limita_chaves():
    now = [0.0]
    counter = MemoryRateCounter(clock=lambda: now[0])
    assert counter.hit("a", 60)[0] == 1
    assert counter.hit("a", 60)[0] == 2
    now[0] = 61
    assert counter.hit("a", 60) == (1, 60)

    counter.MAX_KEYS = 10
    for i in range(50):
        counter.hit(f"ip-{i}", 60)
    assert len(counter._windows) <= 10
