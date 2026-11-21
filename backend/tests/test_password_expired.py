"""Senha expirada: troca obrigatória no próximo acesso.

Cobre o fluxo do login (não entra, recebe token de redefinição), a regra de
que a senha nova precisa ser diferente, e o SQL da migração z2c3senhaexpirada
que expira a conta criada com hash copiado de outra.
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, text

from app.models.user import User, UserRole

LOGIN = "/api/v1/auth/login"
CONFIRM = "/api/v1/auth/password-reset/confirm"


def _login(http, email, senha):
    return http.post(LOGIN, data={"username": email, "password": senha})


async def _expirar(db, user):
    user.password_expired = True
    await db.commit()


async def test_login_com_senha_expirada_nao_entra_e_devolve_token(client, user_a, test_db):
    await _expirar(test_db, user_a)
    resp = _login(client, user_a.email, "password123")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "password_expired"
    assert "access_token" not in body
    assert body["reset_token"]


async def test_senha_errada_continua_401_mesmo_expirada(client, user_a, test_db):
    await _expirar(test_db, user_a)
    assert _login(client, user_a.email, "errada-123").status_code == 401


async def test_troca_obrigatoria_recusa_a_mesma_senha_e_aceita_nova(client, user_a, test_db):
    await _expirar(test_db, user_a)
    token = _login(client, user_a.email, "password123").json()["reset_token"]

    mesma = client.post(CONFIRM, json={"token": token, "new_password": "password123"})
    assert mesma.status_code == 400
    assert "diferente" in mesma.json()["detail"]

    nova = client.post(CONFIRM, json={"token": token, "new_password": "SenhaNova!2026"})
    assert nova.status_code == 200, nova.text

    await test_db.refresh(user_a)
    assert user_a.password_expired is False
    entrou = _login(client, user_a.email, "SenhaNova!2026")
    assert entrou.status_code == 200
    assert "access_token" in entrou.json()


def _sql_da_migracao() -> str:
    caminho = Path(__file__).parents[1] / "alembic/versions/z2c3senhaexpirada_users_password_expired.py"
    fonte = caminho.read_text(encoding="utf-8")
    inicio = fonte.index('"""\n        UPDATE') + 4
    return fonte[inicio:fonte.index('"""', inicio)]


async def test_migracao_expira_so_a_conta_com_hash_copiado(user_a, user_b, test_db):
    # Datas explícitas: no mesmo segundo, quem é "a mais antiga" ficaria no acaso.
    user_a.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    clone = User(
        created_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        id=uuid.uuid4(),
        email="clone@firma-a.com",
        hashed_password=user_a.hashed_password,  # hash copiado, como no script antigo
        full_name="Clone",
        tenant_id=user_a.tenant_id,
        role=UserRole.OWNER,
        is_active=True,
    )
    test_db.add(clone)
    await test_db.commit()

    await test_db.execute(text(_sql_da_migracao()))
    await test_db.commit()

    rows = (await test_db.execute(select(User.email, User.password_expired))).all()
    expirados = {email for email, exp in rows if exp}
    assert expirados == {"clone@firma-a.com"}  # original e user_b (outro sal) ficam
