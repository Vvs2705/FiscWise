"""Criar registro apontando para cliente de outro escritório devolve 404 (TEN-7)."""

GUIA = {
    "tipo": "DAS",
    "competencia": "2026-09-01",
    "valor": "100.00",
    "vencimento": "2026-10-20",
}


async def test_guia_com_cliente_de_outro_escritorio(client_with_auth_a, client_b):
    http, _, client_a, _ = client_with_auth_a
    assert (
        http.post(
            "/api/v1/guias", json={**GUIA, "client_id": str(client_b.id)}
        ).status_code
        == 404
    )
    assert (
        http.post(
            "/api/v1/guias", json={**GUIA, "client_id": str(client_a.id)}
        ).status_code
        == 201
    )
