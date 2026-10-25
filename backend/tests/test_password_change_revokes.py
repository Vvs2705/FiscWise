"""Trocar a senha derruba tokens antigos e devolve um novo (SEC-8)."""

import time


async def test_troca_de_senha_invalida_token_antigo(client_with_auth_a):
    http, *_ = client_with_auth_a
    old_auth = http.headers["Authorization"]
    time.sleep(1.1)  # iat tem resolução de segundos
    resp = http.post(
        "/api/v1/auth/change-password",
        json={"current_password": "password123", "new_password": "NovaSenha!2026x"},
    )
    assert resp.status_code == 200, resp.text
    new_token = resp.json()["access_token"]

    assert http.get("/api/v1/auth/me").status_code == 401  # token antigo
    http.headers["Authorization"] = f"Bearer {new_token}"
    assert http.get("/api/v1/auth/me").status_code == 200
    assert old_auth != http.headers["Authorization"]
