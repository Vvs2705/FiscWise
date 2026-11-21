"""Conferência da senha atual com limite de tentativas (compliance #8 e #5).

Um access token roubado não pode testar senhas à vontade em
/auth/change-password ou /auth/2fa/disable para tomar a conta, e senha nova
acima de 72 bytes (limite do bcrypt) volta 400, não 500.
"""

from app.core.auth_rate_limiter import LOGIN_MAX_ATTEMPTS


def _tentar_ate_bloquear(http, path, body):
    codes = [http.post(path, json=body).status_code for _ in range(LOGIN_MAX_ATTEMPTS + 1)]
    assert codes[:LOGIN_MAX_ATTEMPTS] == [400] * LOGIN_MAX_ATTEMPTS, codes
    assert codes[-1] == 429, codes


async def test_change_password_bloqueia_apos_falhas(client_with_auth_a):
    http, *_ = client_with_auth_a
    _tentar_ate_bloquear(
        http,
        "/api/v1/auth/change-password",
        {"current_password": "errada-123", "new_password": "NovaSenha!2026x"},
    )
    # Bloqueado: nem a senha certa passa até o fim da janela.
    resp = http.post(
        "/api/v1/auth/change-password",
        json={"current_password": "password123", "new_password": "NovaSenha!2026x"},
    )
    assert resp.status_code == 429


async def test_disable_2fa_bloqueia_apos_falhas(client_with_auth_a):
    http, *_ = client_with_auth_a
    _tentar_ate_bloquear(http, "/api/v1/auth/2fa/disable", {"current_password": "errada-123"})


async def test_change_password_acima_de_72_bytes_volta_400(client_with_auth_a):
    http, *_ = client_with_auth_a
    resp = http.post(
        "/api/v1/auth/change-password",
        json={"current_password": "password123", "new_password": "ç" * 40},  # 80 bytes
    )
    assert resp.status_code == 400, resp.text
    assert "72 bytes" in resp.json()["detail"]
