"""Botão Reativar da aba Desativados: DELETE desativa, PUT status=active reativa."""

import pytest

pytestmark = pytest.mark.integration


async def test_deactivated_client_can_be_reactivated(client_with_auth_a):
    http, _, client, _ = client_with_auth_a

    resp = http.delete(f"/api/v1/clients/{client.id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "inactive"
    before = resp.json()["updated_at"]

    resp = http.put(f"/api/v1/clients/{client.id}", json={"status": "active"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "active"
    assert resp.json()["updated_at"] >= before

    # Repetir é idempotente
    again = http.put(f"/api/v1/clients/{client.id}", json={"status": "active"})
    assert again.status_code == 200 and again.json()["status"] == "active"
