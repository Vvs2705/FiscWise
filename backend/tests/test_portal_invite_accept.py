"""Aceite de convite vincula o usuário ao cliente (TEN-9: portal_user_id ficava None)."""

import uuid

from sqlalchemy import select

from app.models.operations import AccountingClient


async def test_aceite_vincula_cliente_e_libera_my_data(client_with_auth_a):
    http, _, client_a, test_db = client_with_auth_a
    resp = http.post(
        "/api/v1/portal/invites",
        json={"client_id": str(client_a.id), "email": "portal@cliente-a.com"},
    )
    assert resp.status_code == 201, resp.text
    invite_id = resp.json()["invite_id"]

    http.headers.pop("Authorization")
    resp = http.post(
        f"/api/v1/portal/invites/{invite_id}/accept",
        json={
            "invite_id": invite_id,
            "password": "senha-forte-123",  # gitleaks:allow (senha de teste)
            "full_name": "Cliente A",
        },
    )
    assert resp.status_code == 200, resp.text
    user_id = uuid.UUID(resp.json()["user_id"])

    client = (
        await test_db.execute(
            select(AccountingClient).where(AccountingClient.id == client_a.id)
        )
    ).scalar_one()
    await test_db.refresh(client)
    assert client.portal_user_id == user_id

    http.headers["Authorization"] = f"Bearer {resp.json()['access_token']}"
    assert http.get("/api/v1/portal/my-data").status_code == 200
