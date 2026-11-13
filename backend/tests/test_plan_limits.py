"""Limites da tabela `plans` aplicados no backend (antes alguns só apareciam na tela).

Cobre, sempre pelo plano EFETIVO do escritório:
  - max_clients: cadastro e reativação barrados no limite; erro na checagem
    recusa (falha fechada) no REST e no app offline;
  - max_users: só a equipe conta (clientes do portal não);
  - max_documents_per_client: POST /documents, upload por cliente e upload do
    portal barrados no limite; o que já existe continua;
  - features.portal_cliente / features.obrigacoes: escrita barrada para quem
    não tem o recurso, leitura continua;
  - max_ai_calls_month: classificação de documentos por IA usa o saldo do mês.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core import plan_access
from app.core.plan_access import (
    LIMITE_CLIENTES_CODE,
    LIMITE_DOCUMENTOS_CODE,
    LIMITE_USUARIOS_CODE,
    PLANO_INDISPONIVEL_CODE,
    RECURSO_FORA_DO_PLANO_CODE,
)
from app.core.security import create_access_token, get_password_hash
from app.models.operations import AccountingClient, ClientDocument
from app.models.plan import Plan
from app.models.user import User, UserRole
from app.services.catalog_cache import invalidate_plans

pytestmark = pytest.mark.integration

_TODOS_RECURSOS = {"calculator": True, "ai_chat": True, "portal_cliente": True, "obrigacoes": True}


@pytest.fixture(autouse=True)
def _cache_de_planos_limpo():
    invalidate_plans()
    yield
    invalidate_plans()


async def _plano(test_db, tenant, *, slug="intermediario", features=None, **limites):
    """Grava o plano e coloca o escritório nele (sem assinatura: nunca vence)."""
    valores = dict(max_clients=None, max_users=None, max_ai_calls_month=None, max_documents_per_client=None)
    valores.update(limites)
    test_db.add(Plan(
        id=uuid.uuid4(), slug=slug, name=slug.title(), price_monthly=Decimal("149.00"),
        features=_TODOS_RECURSOS if features is None else features, active=True, **valores,
    ))
    tenant.plan_slug = slug
    await test_db.commit()
    invalidate_plans()


def _cliente(tenant_id, nome, documento, status="active"):
    return AccountingClient(
        id=uuid.uuid4(), tenant_id=tenant_id, name=nome, document=documento,
        entity_type="pj", status=status,
    )


def _codigo(resp):
    return resp.headers.get("x-error-code")


# ---------------------------------------------------------------------------
# max_clients
# ---------------------------------------------------------------------------


async def test_cadastro_de_cliente_barrado_no_limite(client_with_auth_a, tenant_a):
    http, _, _, test_db = client_with_auth_a  # client_a já é 1 cliente ativo
    await _plano(test_db, tenant_a, max_clients=2)

    ok = http.post("/api/v1/clients", json={"name": "Segundo", "entity_type": "pj"})
    assert ok.status_code == 201, ok.text

    barrado = http.post("/api/v1/clients", json={"name": "Terceiro", "entity_type": "pj"})
    assert barrado.status_code == 403
    assert _codigo(barrado) == LIMITE_CLIENTES_CODE
    assert "Limite de clientes" in barrado.json()["detail"]


async def test_quem_ja_passou_do_limite_mantem_os_clientes(client_with_auth_a, tenant_a):
    """Limite menor que o uso atual: nada some, só o novo é barrado."""
    http, _, client, test_db = client_with_auth_a
    test_db.add_all([
        _cliente(tenant_a.id, "Cliente B", "11222333000181"),
        _cliente(tenant_a.id, "Cliente C", "11444777000161"),
    ])
    await test_db.commit()
    await _plano(test_db, tenant_a, max_clients=1)

    lista = http.get("/api/v1/clients")
    assert lista.status_code == 200
    assert len(lista.json()) == 3
    editar = http.put(f"/api/v1/clients/{client.id}", json={"name": "Nome novo"})
    assert editar.status_code == 200, editar.text

    novo = http.post("/api/v1/clients", json={"name": "Cliente D", "entity_type": "pj"})
    assert novo.status_code == 403
    assert _codigo(novo) == LIMITE_CLIENTES_CODE


async def test_reativar_cliente_conta_no_limite(client_with_auth_a, tenant_a):
    http, _, _, test_db = client_with_auth_a
    inativo = _cliente(tenant_a.id, "Inativo", "11222333000181", status="inactive")
    test_db.add(inativo)
    await test_db.commit()
    await _plano(test_db, tenant_a, max_clients=1)

    resp = http.put(f"/api/v1/clients/{inativo.id}", json={"status": "active"})
    assert resp.status_code == 403
    assert _codigo(resp) == LIMITE_CLIENTES_CODE


async def test_trava_de_clientes_falha_fechada(client_with_auth_a, tenant_a, monkeypatch):
    http, _, _, test_db = client_with_auth_a
    await _plano(test_db, tenant_a, max_clients=50)

    async def quebra(*a, **k):
        raise RuntimeError("banco fora")

    monkeypatch.setattr(plan_access, "load_tenant_plan", quebra)
    resp = http.post("/api/v1/clients", json={"name": "Não pode passar", "entity_type": "pj"})
    assert resp.status_code == 503
    assert _codigo(resp) == PLANO_INDISPONIVEL_CODE

    monkeypatch.undo()
    lista = http.get("/api/v1/clients")
    assert [c["name"] for c in lista.json()] == ["Client from Firm A"]


async def test_app_offline_recusa_cliente_no_limite_e_quando_a_checagem_falha(
    test_db, tenant_a, client_a, user_a, monkeypatch
):
    from app.api.v1.endpoints.sync import SyncRejection, _check_client_plan_limit

    await _plano(test_db, tenant_a, max_clients=1)
    ctx = SimpleNamespace(tenant_id=tenant_a.id, user_email=user_a.email)
    with pytest.raises(SyncRejection, match="Limite de clientes"):
        await _check_client_plan_limit(test_db, ctx)

    async def quebra(*a, **k):
        raise RuntimeError("banco fora")

    monkeypatch.setattr(plan_access, "load_tenant_plan", quebra)
    with pytest.raises(SyncRejection, match="Não foi possível conferir"):
        await _check_client_plan_limit(test_db, ctx)


# ---------------------------------------------------------------------------
# max_users
# ---------------------------------------------------------------------------


async def test_limite_de_usuarios_conta_so_a_equipe(test_db, tenant_a, user_a):
    await _plano(test_db, tenant_a, max_users=2)
    # Cliente do portal não ocupa vaga da equipe.
    test_db.add(User(
        id=uuid.uuid4(), email="cliente@portal.com", hashed_password=get_password_hash("x" * 12),
        tenant_id=tenant_a.id, role=UserRole.CLIENT, is_active=True,
    ))
    await test_db.commit()
    await plan_access.ensure_can_add_team_member(test_db, tenant_a.id)  # 1 de 2: passa

    test_db.add(User(
        id=uuid.uuid4(), email="membro@firma-a.com", hashed_password=get_password_hash("x" * 12),
        tenant_id=tenant_a.id, role=UserRole.MEMBER, is_active=True,
    ))
    await test_db.commit()
    with pytest.raises(HTTPException) as exc:
        await plan_access.ensure_can_add_team_member(test_db, tenant_a.id)
    assert exc.value.status_code == 403
    assert exc.value.headers["X-Error-Code"] == LIMITE_USUARIOS_CODE
    assert "Limite de usuários" in exc.value.detail


async def test_uso_de_usuarios_na_tela_nao_conta_cliente_do_portal(client_with_auth_a, tenant_a):
    http, _, _, test_db = client_with_auth_a
    await _plano(test_db, tenant_a, max_users=5)
    test_db.add(User(
        id=uuid.uuid4(), email="cliente2@portal.com", hashed_password=get_password_hash("x" * 12),
        tenant_id=tenant_a.id, role=UserRole.CLIENT, is_active=True,
    ))
    await test_db.commit()

    usage = http.get("/api/v1/subscription/usage")
    assert usage.status_code == 200, usage.text
    assert usage.json()["users"]["used"] == 1
    check = http.get("/api/v1/subscription/limits-check", params={"resource": "user"})
    assert check.json() == {"allowed": True, "used": 1, "limit": 5}


# ---------------------------------------------------------------------------
# max_documents_per_client
# ---------------------------------------------------------------------------


async def test_documento_barrado_no_limite_por_cliente(client_with_auth_a, tenant_a):
    http, _, client, test_db = client_with_auth_a
    outro = _cliente(tenant_a.id, "Outro", "11222333000181")
    test_db.add_all([
        outro,
        ClientDocument(id=uuid.uuid4(), tenant_id=tenant_a.id, client_id=client.id, name="Doc 1"),
        ClientDocument(id=uuid.uuid4(), tenant_id=tenant_a.id, client_id=client.id, name="Doc 2"),
    ])
    await test_db.commit()
    await _plano(test_db, tenant_a, max_documents_per_client=2)

    resp = http.post("/api/v1/documents", json={"client_id": str(client.id), "name": "Doc 3"})
    assert resp.status_code == 403
    assert _codigo(resp) == LIMITE_DOCUMENTOS_CODE
    assert "Limite de documentos" in resp.json()["detail"]

    # Upload direto do arquivo também barra, antes de subir para o storage.
    up = http.post(
        f"/api/v1/clients/{client.id}/documents",
        params={"document_type": "contract"},
        files={"file": ("contrato.pdf", b"%PDF-1.4 teste", "application/pdf")},
    )
    assert up.status_code == 403
    assert _codigo(up) == LIMITE_DOCUMENTOS_CODE

    # O limite é por cliente: o outro cliente segue livre.
    ok = http.post("/api/v1/documents", json={"client_id": str(outro.id), "name": "Doc do outro"})
    assert ok.status_code == 201, ok.text
    # E os documentos que já existiam continuam lá.
    lista = http.get(f"/api/v1/clients/{client.id}/documents")
    assert len(lista.json()) == 2


async def test_portal_do_cliente_respeita_limite_de_documentos(test_db, tenant_a, client_a):
    from app.core.deps import get_db
    from app.main import app

    portal_user = User(
        id=uuid.uuid4(), email="cliente.limite@example.com", hashed_password=get_password_hash("x" * 12),
        full_name="Cliente", tenant_id=tenant_a.id, role=UserRole.CLIENT, is_active=True,
    )
    test_db.add(portal_user)
    client_a.portal_user_id = portal_user.id
    test_db.add(ClientDocument(id=uuid.uuid4(), tenant_id=tenant_a.id, client_id=client_a.id, name="Doc 1"))
    await test_db.commit()
    await _plano(test_db, tenant_a, max_documents_per_client=1)

    app.dependency_overrides[get_db] = lambda: test_db
    try:
        http = TestClient(app)
        token = create_access_token(
            user_id=str(portal_user.id), tenant_id=str(tenant_a.id), role=UserRole.CLIENT.value
        )
        http.headers.update({"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant_a.id)})
        resp = http.post(
            "/api/v1/portal/my-documents",
            files={"file": ("extrato.pdf", b"%PDF-1.4 teste", "application/pdf")},
        )
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 403
    assert _codigo(resp) == LIMITE_DOCUMENTOS_CODE


# ---------------------------------------------------------------------------
# features.portal_cliente / features.obrigacoes
# ---------------------------------------------------------------------------


async def test_plano_sem_portal_nao_convida_nem_envia_link(client_with_auth_a, tenant_a):
    http, _, client, test_db = client_with_auth_a
    await _plano(test_db, tenant_a, features={"calculator": True, "portal_cliente": False, "obrigacoes": True})

    convite = http.post(
        "/api/v1/portal/invites", json={"client_id": str(client.id), "email": "cli@example.com"}
    )
    assert convite.status_code == 403
    assert _codigo(convite) == RECURSO_FORA_DO_PLANO_CODE
    assert "Portal do cliente" in convite.json()["detail"]

    link = http.post("/api/v1/portal/magic-link/request", json={"client_id": str(client.id)})
    assert link.status_code == 403
    assert _codigo(link) == RECURSO_FORA_DO_PLANO_CODE


async def test_plano_sem_obrigacoes_bloqueia_escrita_e_mantem_leitura(client_with_auth_a, tenant_a):
    http, _, client, test_db = client_with_auth_a
    await _plano(test_db, tenant_a, features={"calculator": True, "portal_cliente": True, "obrigacoes": False})

    criar = http.post(
        "/api/v1/obligations/instances",
        json={
            "client_id": str(client.id), "custom_name": "DCTFWeb",
            "competence_month": "2026-11-01", "due_date": "2026-12-15",
        },
    )
    assert criar.status_code == 403
    assert _codigo(criar) == RECURSO_FORA_DO_PLANO_CODE
    assert "Motor de obrigações" in criar.json()["detail"]

    gerar = http.post("/api/v1/obligations/generate", json={"year": 2026, "month": 11})
    assert gerar.status_code == 403
    assert _codigo(gerar) == RECURSO_FORA_DO_PLANO_CODE

    assert http.get("/api/v1/obligations/instances").status_code == 200


async def test_plano_com_recursos_continua_liberado(client_with_auth_a, tenant_a):
    """Intermediário/Premium/Enterprise têm os dois recursos: nada muda para eles."""
    http, _, client, test_db = client_with_auth_a
    await _plano(test_db, tenant_a)  # todos os recursos ligados

    criar = http.post(
        "/api/v1/obligations/instances",
        json={
            "client_id": str(client.id), "custom_name": "DCTFWeb",
            "competence_month": "2026-11-01", "due_date": "2026-12-15",
        },
    )
    assert criar.status_code == 201, criar.text


# ---------------------------------------------------------------------------
# max_ai_calls_month na classificação de documentos
# ---------------------------------------------------------------------------


@pytest.fixture
def ia_falsa(monkeypatch):
    from app.api.v1.endpoints import operations

    chamadas = []

    async def fake_parse(file_path, file_name):
        return {"full_text": "DAS competência 10/2026"}, None

    async def fake_classify(parsed_data, *, file_name, declared_document_type):
        chamadas.append(file_name)
        return {"tipo": "das"}

    monkeypatch.setattr(operations, "parse_document", fake_parse)
    monkeypatch.setattr(operations, "is_skipped", lambda data: None)
    monkeypatch.setattr(operations, "classify_fiscal_document", fake_classify)
    return chamadas


async def _doc(test_db, tenant_id, client_id, nome):
    doc = ClientDocument(
        id=uuid.uuid4(), tenant_id=tenant_id, client_id=client_id, name=nome, parse_status="processing"
    )
    test_db.add(doc)
    await test_db.commit()
    return doc


async def test_classificacao_por_ia_usa_o_saldo_mensal(test_db, tenant_a, client_a, ia_falsa):
    from app.api.v1.endpoints.operations import apply_document_parse

    await _plano(test_db, tenant_a, max_ai_calls_month=1)
    d1 = await _doc(test_db, tenant_a.id, client_a.id, "das1.pdf")
    d2 = await _doc(test_db, tenant_a.id, client_a.id, "das2.pdf")

    assert await apply_document_parse(test_db, d1.id, tenant_a.id, "/tmp/x", "das1.pdf") == "completed"
    assert await apply_document_parse(test_db, d2.id, tenant_a.id, "/tmp/x", "das2.pdf") == "completed"

    assert ia_falsa == ["das1.pdf"]  # a IA só foi chamada uma vez
    await test_db.refresh(d1)
    await test_db.refresh(d2)
    assert d1.ai_classified_at is not None
    assert d1.parsed_data["ai_classification"] == {"tipo": "das"}
    assert d2.ai_classified_at is None
    assert "ai_classification" not in d2.parsed_data
    assert "cota mensal de IA" in d2.parsed_data["ai_classification_skipped"]
    assert d2.parsed_data["full_text"]  # o documento foi lido normalmente

    assert await plan_access.count_ai_calls_this_month(test_db, tenant_a.id) == 1


async def test_plano_sem_ia_nao_classifica(test_db, tenant_a, client_a, ia_falsa):
    from app.api.v1.endpoints.operations import apply_document_parse

    await _plano(test_db, tenant_a, slug="free", max_ai_calls_month=0)
    doc = await _doc(test_db, tenant_a.id, client_a.id, "nota.pdf")
    assert await apply_document_parse(test_db, doc.id, tenant_a.id, "/tmp/x", "nota.pdf") == "completed"
    assert ia_falsa == []


async def test_plano_sem_limite_de_ia_classifica_sempre(test_db, tenant_a, client_a, ia_falsa):
    from app.api.v1.endpoints.operations import apply_document_parse

    await _plano(test_db, tenant_a, slug="premium", max_ai_calls_month=None)
    for i in range(3):
        doc = await _doc(test_db, tenant_a.id, client_a.id, f"doc{i}.pdf")
        await apply_document_parse(test_db, doc.id, tenant_a.id, "/tmp/x", f"doc{i}.pdf")
    assert len(ia_falsa) == 3


async def test_checagem_de_ia_falha_fechada(test_db, tenant_a, client_a, ia_falsa, monkeypatch):
    from app.api.v1.endpoints.operations import apply_document_parse

    await _plano(test_db, tenant_a, max_ai_calls_month=20)

    async def quebra(*a, **k):
        raise RuntimeError("banco fora")

    monkeypatch.setattr(plan_access, "load_tenant_plan", quebra)
    doc = await _doc(test_db, tenant_a.id, client_a.id, "nota.pdf")
    assert await apply_document_parse(test_db, doc.id, tenant_a.id, "/tmp/x", "nota.pdf") == "completed"
    assert ia_falsa == []


async def test_uso_de_ia_na_tela_soma_classificacoes(client_with_auth_a, tenant_a):
    http, _, client, test_db = client_with_auth_a
    await _plano(test_db, tenant_a, max_ai_calls_month=20, max_documents_per_client=100)
    test_db.add(ClientDocument(
        id=uuid.uuid4(), tenant_id=tenant_a.id, client_id=client.id, name="Classificado",
        ai_classified_at=datetime.now(timezone.utc),
    ))
    await test_db.commit()

    usage = http.get("/api/v1/subscription/usage").json()
    assert usage["ai_calls_this_month"]["used"] == 1
    assert usage["documents_per_client_limit"] == 100
