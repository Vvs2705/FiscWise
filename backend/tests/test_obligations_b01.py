"""Obrigações: geração por tenant, nome da avulsa e exclusão lógica (B-01)."""

from sqlalchemy import select

from app.models.obligation import ObligationInstance
from app.services.obligation_engine import generate_obligations_for_month

AVULSA = {
    "competence_month": "2026-09-01",
    "due_date": "2026-10-20",
    "priority": "medium",
}


def _perfil_simples(client):
    client.regime_tributario = "simples_nacional"
    client.tem_funcionarios = True
    client.municipio_ibge = "3550308"
    client.uf = "SP"
    client.cnae = "6201500"


async def _instancias(db, client_id):
    result = await db.execute(
        select(ObligationInstance).where(ObligationInstance.client_id == client_id)
    )
    return result.scalars().all()


async def test_generate_endpoint_so_cria_para_o_proprio_tenant(client_with_auth_a, client_b):
    http, _, client_a, db = client_with_auth_a
    _perfil_simples(client_a)
    _perfil_simples(client_b)
    await db.commit()

    resp = http.post("/api/v1/obligations/generate", json={"year": 2026, "month": 5})
    assert resp.status_code == 200, resp.text
    assert resp.json()["created"] > 0
    assert len(await _instancias(db, client_a.id)) > 0
    assert await _instancias(db, client_b.id) == []


async def test_engine_sem_tenant_continua_cobrindo_todos(client_with_auth_a, client_b):
    _, _, client_a, db = client_with_auth_a
    _perfil_simples(client_a)
    _perfil_simples(client_b)
    await db.commit()

    await generate_obligations_for_month(db, 2026, 5)
    assert len(await _instancias(db, client_a.id)) > 0
    assert len(await _instancias(db, client_b.id)) > 0


def test_avulsa_guarda_e_devolve_custom_name(client_with_auth_a):
    http, _, client_a, _ = client_with_auth_a
    resp = http.post(
        "/api/v1/obligations/instances",
        json={**AVULSA, "client_id": str(client_a.id), "custom_name": "Alvará anual", "notes": "pedir ao cliente"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["custom_name"] == "Alvará anual"
    assert body["notes"] == "pedir ao cliente"

    listed = http.get("/api/v1/obligations/instances").json()
    assert [i["custom_name"] for i in listed] == ["Alvará anual"]

    # Editar observações não apaga o nome
    upd = http.patch(f"/api/v1/obligations/instances/{body['id']}", json={"notes": "recebido"})
    assert upd.status_code == 200
    assert upd.json()["custom_name"] == "Alvará anual"
    assert upd.json()["notes"] == "recebido"


def _criar(http, client_id):
    resp = http.post("/api/v1/obligations/instances", json={**AVULSA, "client_id": str(client_id)})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_delete_cancela_e_e_idempotente(client_with_auth_a):
    http, _, client_a, _ = client_with_auth_a
    inst_id = _criar(http, client_a.id)

    first = http.delete(f"/api/v1/obligations/instances/{inst_id}")
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "cancelled"

    again = http.delete(f"/api/v1/obligations/instances/{inst_id}")
    assert again.status_code == 200
    assert again.json()["status"] == "cancelled"


def test_delete_de_outro_tenant_e_404(client_with_auth_a, client_with_auth_b):
    http_a, _, client_a, _ = client_with_auth_a
    http_b = client_with_auth_b[0]
    inst_id = _criar(http_a, client_a.id)
    assert http_b.delete(f"/api/v1/obligations/instances/{inst_id}").status_code == 404
    assert http_a.get("/api/v1/obligations/instances").json()[0]["status"] == "pending"


def test_delete_de_obrigacao_entregue_e_409(client_with_auth_a):
    http, _, client_a, _ = client_with_auth_a
    inst_id = _criar(http, client_a.id)
    assert http.patch(f"/api/v1/obligations/instances/{inst_id}", json={"status": "delivered"}).status_code == 200
    assert http.delete(f"/api/v1/obligations/instances/{inst_id}").status_code == 409
