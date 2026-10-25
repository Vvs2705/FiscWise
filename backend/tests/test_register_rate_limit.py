"""Cadastro público limitado por IP (SEC-4/SEC-12)."""

from app.core.auth_rate_limiter import LOGIN_MAX_ATTEMPTS


def test_cadastro_em_massa_bloqueia(client):
    codes = [
        client.post(
            "/api/v1/onboarding/register",
            json={"company_name": "Firma", "owner_email": f"dono{i}@firma.com", "owner_password": "SenhaSegura123!"},
        ).status_code
        for i in range(LOGIN_MAX_ATTEMPTS + 1)
    ]
    assert codes[-1] == 429
    assert 429 not in codes[:LOGIN_MAX_ATTEMPTS]
