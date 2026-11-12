"""DELETE como exclusão lógica em prazos, certificados e cobranças (B-01)."""

import pytest

DEADLINE = {"title": "DCTFWeb", "category": "fiscal", "due_date": "2026-12-15"}
CERT = {"label": "e-CNPJ A1", "certificate_type": "a1", "valid_until": "2027-06-30"}
RECEIVABLE = {"description": "Honorário 11/2026", "amount": "500.00", "due_date": "2026-12-10"}

CASES = [
    # (base, payload, status terminal, status que bloqueia a exclusão)
    ("/api/v1/deadlines", DEADLINE, "cancelled", "completed"),
    ("/api/v1/certificates", CERT, "revoked", None),
    ("/api/v1/receivables", RECEIVABLE, "cancelled", "paid"),
]
IDS = ["deadline", "certificate", "receivable"]


def _criar(http, base, payload, client_id):
    resp = http.post(base, json={**payload, "client_id": str(client_id)})
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.parametrize("base,payload,terminal,_blocked", CASES, ids=IDS)
def test_delete_leva_ao_status_terminal_e_e_idempotente(client_with_auth_a, base, payload, terminal, _blocked):
    http, _, client_a, _ = client_with_auth_a
    item = _criar(http, base, payload, client_a.id)

    first = http.delete(f"{base}/{item['id']}")
    assert first.status_code == 200, first.text
    assert first.json()["status"] == terminal

    again = http.delete(f"{base}/{item['id']}")
    assert again.status_code == 200
    assert again.json()["status"] == terminal

    # Continua existindo (não é DELETE físico)
    assert http.get(f"{base}/{item['id']}").json()["status"] == terminal


@pytest.mark.parametrize("base,payload,terminal,_blocked", CASES, ids=IDS)
def test_delete_de_outro_tenant_e_404(client_with_auth_a, client_with_auth_b, base, payload, terminal, _blocked):
    http_a, _, client_a, _ = client_with_auth_a
    http_b = client_with_auth_b[0]
    item = _criar(http_a, base, payload, client_a.id)

    assert http_b.delete(f"{base}/{item['id']}").status_code == 404
    assert http_a.get(f"{base}/{item['id']}").json()["status"] == item["status"]


@pytest.mark.parametrize(
    "base,payload,blocked",
    [(b, p, blk) for b, p, _t, blk in CASES if blk],
    ids=["deadline", "receivable"],
)
def test_delete_de_status_terminal_e_409(client_with_auth_a, base, payload, blocked):
    http, _, client_a, _ = client_with_auth_a
    item = _criar(http, base, payload, client_a.id)
    assert http.patch(f"{base}/{item['id']}", json={"status": blocked}).status_code == 200

    resp = http.delete(f"{base}/{item['id']}")
    assert resp.status_code == 409
    assert http.get(f"{base}/{item['id']}").json()["status"] == blocked


def test_delete_certificado_marca_bloqueado_como_o_block(client_with_auth_a):
    http, _, client_a, _ = client_with_auth_a
    cert = _criar(http, "/api/v1/certificates", CERT, client_a.id)
    body = http.delete(f"/api/v1/certificates/{cert['id']}").json()
    assert body["status"] == "revoked"
    trail = http.get(f"/api/v1/certificates/{cert['id']}/usage-trail").json()
    assert [e["action"] for e in trail] == ["certificate.blocked"]
