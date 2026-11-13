"""Um teste grátis por CNPJ/CPF (decisão do dono, 13/11/2026).

- O CNPJ/CPF é obrigatório no cadastro (e-mail, Google e concluir cadastro),
  validado pelos dígitos verificadores e gravado só com dígitos.
- Documento já usado por outro escritório (com ou sem máscara) é recusado
  com DOCUMENT_ALREADY_USED: não ganha novo teste nem nova oferta.

`gerar_cnpj` / `gerar_cpf` também servem aos outros testes de cadastro.
"""

import uuid

import pytest
from sqlalchemy import select

from app.core.security import create_access_token
from app.models.tenant import Tenant
from app.models.user import User, UserRole


def _dv(numeros: list[int], pesos: list[int]) -> int:
    resto = sum(n * p for n, p in zip(numeros, pesos)) % 11
    return 0 if resto < 2 else 11 - resto


def gerar_cnpj(n: int) -> str:
    """CNPJ válido (só dígitos) e diferente para cada n."""
    base = [int(c) for c in f"{(n * 7919 + 1234567) % 10**8:08d}0001"]
    d1 = _dv(base, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    d2 = _dv(base + [d1], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return "".join(map(str, base + [d1, d2]))


def gerar_cpf(n: int) -> str:
    """CPF válido (só dígitos) e diferente para cada n."""
    base = [int(c) for c in f"{(n * 104729 + 12345678) % 10**9:09d}"]
    d1 = (sum(v * p for v, p in zip(base, range(10, 1, -1))) * 10) % 11 % 10
    d2 = (sum(v * p for v, p in zip(base + [d1], range(11, 1, -1))) * 10) % 11 % 10
    return "".join(map(str, base + [d1, d2]))


def mascarar_cnpj(c: str) -> str:
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"


def _payload(email: str, document) -> dict:
    corpo = {
        "company_name": "Escritório Documento",
        "owner_email": email,
        "owner_password": "SenhaSegura123!",
        "terms_accepted": True,
    }
    if document is not None:
        corpo["document"] = document
    return corpo


def test_geradores_produzem_documentos_validos():
    from app.core.validators import validate_cnpj, validate_cpf

    cnpjs = {gerar_cnpj(i) for i in range(50)}
    cpfs = {gerar_cpf(i) for i in range(50)}
    assert len(cnpjs) == 50 and len(cpfs) == 50
    assert all(validate_cnpj(c) for c in cnpjs)
    assert all(validate_cpf(c) for c in cpfs)


@pytest.fixture
def client(test_db):
    from fastapi.testclient import TestClient

    from app.core.deps import get_db
    from app.main import app

    app.dependency_overrides[get_db] = lambda: test_db
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _sem_limite_de_cadastro(monkeypatch):
    """O teto de cadastros por IP não é o assunto aqui."""
    from app.core.auth_rate_limiter import auth_rate_limiter

    monkeypatch.setattr(auth_rate_limiter, "check_login_ip", lambda *_a, **_k: None)


@pytest.mark.asyncio
async def test_cadastro_sem_documento_e_recusado(client):
    resp = client.post("/api/v1/onboarding/register", json=_payload("sem@doc.com", None))
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
@pytest.mark.parametrize("doc", ["123", "11111111111", "00000000000000", "12.345.678/0001-00"])
async def test_documento_invalido_e_recusado(client, doc):
    resp = client.post("/api/v1/onboarding/register", json=_payload(f"{uuid.uuid4().hex[:8]}@doc.com", doc))
    assert resp.status_code == 400, resp.text
    assert resp.headers.get("X-Error-Code") == "INVALID_DOCUMENT"


@pytest.mark.asyncio
async def test_cpf_e_cnpj_validos_gravam_so_digitos(client, test_db):
    cnpj = gerar_cnpj(101)
    cpf = gerar_cpf(101)
    cpf_mascarado = f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
    for email, doc, esperado in (
        ("cnpj@doc.com", mascarar_cnpj(cnpj), cnpj),
        ("cpf@doc.com", cpf_mascarado, cpf),
    ):
        resp = client.post("/api/v1/onboarding/register", json=_payload(email, doc))
        assert resp.status_code == 200, resp.text
        tenant = (
            await test_db.execute(select(Tenant).where(Tenant.id == uuid.UUID(resp.json()["tenant_id"])))
        ).scalar_one()
        assert tenant.document == esperado


@pytest.mark.asyncio
async def test_mesmo_documento_com_e_sem_mascara_e_recusado(client, test_db):
    cnpj = gerar_cnpj(202)
    primeiro = client.post("/api/v1/onboarding/register", json=_payload("um@doc.com", cnpj))
    assert primeiro.status_code == 200, primeiro.text

    segundo = client.post("/api/v1/onboarding/register", json=_payload("dois@doc.com", mascarar_cnpj(cnpj)))
    assert segundo.status_code == 400, segundo.text
    assert segundo.headers.get("X-Error-Code") == "DOCUMENT_ALREADY_USED"
    assert "já tem uma conta" in segundo.json()["detail"]


@pytest.mark.asyncio
async def test_documento_antigo_gravado_com_mascara_tambem_conta(client, test_db):
    """Conta antiga com o CNPJ gravado com pontuação."""
    cnpj = gerar_cnpj(303)
    test_db.add(Tenant(id=uuid.uuid4(), name="Antigo", document=mascarar_cnpj(cnpj)))
    await test_db.commit()

    resp = client.post("/api/v1/onboarding/register", json=_payload("novo@doc.com", cnpj))
    assert resp.status_code == 400, resp.text
    assert resp.headers.get("X-Error-Code") == "DOCUMENT_ALREADY_USED"


@pytest.mark.asyncio
async def test_google_tambem_exige_documento_livre(client, test_db, monkeypatch):
    from app.api.v1.endpoints import onboarding

    cnpj = gerar_cnpj(404)
    test_db.add(Tenant(id=uuid.uuid4(), name="Dono do CNPJ", document=cnpj))
    await test_db.commit()
    monkeypatch.setattr(onboarding, "verify_google_signup_token", lambda _t: ("g@doc.com", "G"))

    base = {"signup_token": "token-assinado-123", "company_name": "Via Google", "terms_accepted": True}
    sem = client.post("/api/v1/onboarding/register-google", json=base)
    assert sem.status_code == 422, sem.text

    usado = client.post("/api/v1/onboarding/register-google", json={**base, "document": cnpj})
    assert usado.status_code == 400, usado.text
    assert usado.headers.get("X-Error-Code") == "DOCUMENT_ALREADY_USED"

    ok = client.post("/api/v1/onboarding/register-google", json={**base, "document": gerar_cnpj(405)})
    assert ok.status_code == 200, ok.text


@pytest.mark.asyncio
async def test_concluir_cadastro_exige_documento_valido_e_livre(client, test_db):
    cnpj_de_outro = gerar_cnpj(505)
    test_db.add(Tenant(id=uuid.uuid4(), name="Outro", document=cnpj_de_outro))
    tenant = Tenant(id=uuid.uuid4(), name="Sem cadastro")  # sem aceite dos Termos
    test_db.add(tenant)
    await test_db.flush()
    dono = User(
        id=uuid.uuid4(), tenant_id=tenant.id, email="incompleto@doc.com",
        hashed_password="x", role=UserRole.OWNER, is_active=True,
    )
    test_db.add(dono)
    await test_db.commit()

    token = create_access_token(user_id=str(dono.id), tenant_id=str(tenant.id), role="owner")
    h = {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant.id)}
    corpo = {"company_name": "Agora completo", "terms_accepted": True}

    assert client.post("/api/v1/onboarding/complete-signup", json=corpo, headers=h).status_code == 422
    invalido = client.post("/api/v1/onboarding/complete-signup", json={**corpo, "document": "123"}, headers=h)
    assert invalido.headers.get("X-Error-Code") == "INVALID_DOCUMENT"
    usado = client.post(
        "/api/v1/onboarding/complete-signup", json={**corpo, "document": mascarar_cnpj(cnpj_de_outro)}, headers=h
    )
    assert usado.status_code == 400, usado.text
    assert usado.headers.get("X-Error-Code") == "DOCUMENT_ALREADY_USED"

    livre = gerar_cnpj(506)
    ok = client.post("/api/v1/onboarding/complete-signup", json={**corpo, "document": mascarar_cnpj(livre)}, headers=h)
    assert ok.status_code == 200, ok.text
    await test_db.refresh(tenant)
    assert tenant.document == livre


def test_normalizar_documento_rejeita_vazio():
    from fastapi import HTTPException

    from app.api.v1.endpoints.onboarding import _normalizar_documento

    for ruim in (None, "", "abc"):
        with pytest.raises(HTTPException) as exc:
            _normalizar_documento(ruim)
        assert exc.value.headers["X-Error-Code"] == "INVALID_DOCUMENT"
    assert _normalizar_documento(mascarar_cnpj(gerar_cnpj(1))) == gerar_cnpj(1)
