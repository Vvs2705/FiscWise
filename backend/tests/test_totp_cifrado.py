"""Segredo TOTP cifrado no banco (requisito 3 do checklist de compliance).

Um vazamento do banco não pode entregar o segundo fator: com o segredo TOTP
em texto puro, quem tem o dump gera os códigos do autenticador.
"""

from __future__ import annotations

import base64
import os

import pyotp
import pytest

from app.core import campo_cifrado
from app.core.config import settings
from app.core.security import create_mfa_token


@pytest.fixture
def chave_cofre(monkeypatch):
    monkeypatch.setattr(
        settings, "CERT_ENCRYPTION_KEY", base64.b64encode(os.urandom(32)).decode(), raising=False
    )


def _verificar(http, user, segredo):
    return http.post("/api/v1/auth/login/verify-2fa", json={
        "mfa_token": create_mfa_token(str(user.id)),
        "otp_code": pyotp.TOTP(segredo).now(),
    })


async def test_ativar_grava_cifrado_e_login_funciona(client_with_auth_a, chave_cofre):
    http, user, _, db = client_with_auth_a
    segredo = pyotp.random_base32()
    r = http.post("/api/v1/auth/2fa/enable-totp", json={
        "secret": segredo, "otp_code": pyotp.TOTP(segredo).now(),
    })
    assert r.status_code == 200, r.text
    await db.refresh(user)
    assert user.two_factor_secret.startswith(campo_cifrado.PREFIXO)
    assert segredo not in user.two_factor_secret
    assert len(user.two_factor_secret) <= 255

    assert _verificar(http, user, segredo).status_code == 200
    # Código errado continua recusado.
    r = http.post("/api/v1/auth/login/verify-2fa", json={
        "mfa_token": create_mfa_token(str(user.id)), "otp_code": "000000",
    })
    assert r.status_code == 401


async def test_segredo_legado_continua_valendo_e_e_cifrado_no_login(client_with_auth_a, chave_cofre):
    http, user, _, db = client_with_auth_a
    segredo = pyotp.random_base32()
    user.two_factor_enabled, user.two_factor_method, user.two_factor_secret = True, "totp", segredo
    await db.commit()

    assert _verificar(http, user, segredo).status_code == 200
    await db.refresh(user)
    assert campo_cifrado.esta_cifrado(user.two_factor_secret)
    assert _verificar(http, user, segredo).status_code == 200


async def test_valor_cifrado_nao_vale_para_outro_usuario(chave_cofre, user_a, user_b):
    cifrado = campo_cifrado.cifrar("JBSWY3DPEHPK3PXP", contexto=campo_cifrado.contexto_totp(user_a.id))
    with pytest.raises(campo_cifrado.CampoIlegivel):
        campo_cifrado.decifrar(cifrado, contexto=campo_cifrado.contexto_totp(user_b.id))


async def test_sem_chave_grava_como_antes(client_with_auth_a, monkeypatch):
    monkeypatch.setattr(settings, "CERT_ENCRYPTION_KEY", "", raising=False)
    http, user, _, db = client_with_auth_a
    segredo = pyotp.random_base32()
    r = http.post("/api/v1/auth/2fa/enable-totp", json={
        "secret": segredo, "otp_code": pyotp.TOTP(segredo).now(),
    })
    assert r.status_code == 200
    await db.refresh(user)
    assert user.two_factor_secret == segredo
    assert _verificar(http, user, segredo).status_code == 200


async def test_chave_trocada_responde_400_e_nao_500(client_with_auth_a, chave_cofre, monkeypatch):
    http, user, _, db = client_with_auth_a
    segredo = pyotp.random_base32()
    user.two_factor_enabled, user.two_factor_method = True, "totp"
    user.two_factor_secret = campo_cifrado.cifrar(segredo, contexto=campo_cifrado.contexto_totp(user.id))
    await db.commit()
    monkeypatch.setattr(
        settings, "CERT_ENCRYPTION_KEY", base64.b64encode(os.urandom(32)).decode(), raising=False
    )
    assert _verificar(http, user, segredo).status_code == 400
