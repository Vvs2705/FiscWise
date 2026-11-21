"""Exclusão a pedido (LGPD art. 18, VI), retenção dos registros de acesso e
exportação dos documentos fiscais (requisito 18 do checklist de compliance).

- O pedido do dono (POST /account/delete) só ficava gravado: nada o
  executava, e a rotina automática pula de propósito quem pediu. Agora a
  equipe executa em POST /admin/lgpd/exclusao (prévia por padrão).
- A exclusão apagava audit_events, onde ficam os registros de acesso (IP e
  data) que o Marco Civil (art. 15) manda guardar por 6 meses.
- A exportação não trazia as NFS-e emitidas, guias e fechamentos, que o
  escritório precisa guardar por 5 anos antes de os dados serem excluídos.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import func, select

import app.main  # noqa: F401  (registra todos os modelos antes de criar o banco de teste)
from app.api.v1.endpoints import admin
from app.domain.invoices.models import Invoice, InvoiceIssuer
from app.models.audit import AuditEvent
from app.models.operations import AccountingClient
from app.models.tenant import Tenant
from app.models.user import User
from app.services import exclusao_dados

ADMIN = {"Authorization": "Bearer token-admin-teste"}


@pytest.fixture
def admin_ligado(monkeypatch):
    monkeypatch.setattr(admin, "ADMIN_OPERATIONS_ALLOWED", True)
    monkeypatch.setattr(admin, "ADMIN_TOKEN", "token-admin-teste")


@pytest.fixture
def sem_efeitos_externos(monkeypatch):
    from app.core import storage
    from app.services import email_service

    async def _nada(*a, **k):
        return 0

    async def _lista(*a, **k):
        return []

    async def _email(*a, **k):
        return True

    monkeypatch.setattr(storage, "remove_objects", _nada)
    monkeypatch.setattr(storage, "list_prefix", _lista)
    monkeypatch.setattr(email_service, "send_email", _email)


async def _auditoria(test_db, tenant_id, quando):
    ev = AuditEvent(
        tenant_id=tenant_id, action="auth.login_success", entity_type="auth",
        ip_address="203.0.113.7", user_agent="Mozilla/5.0",
        after_data={"cliente": "Fulano de Tal"}, created_at=quando,
    )
    test_db.add(ev)
    await test_db.commit()
    return ev.id


async def _contar(test_db, model, tenant_id):
    return (
        await test_db.execute(select(func.count()).select_from(model).where(model.tenant_id == tenant_id))
    ).scalar_one()


async def test_pedido_lgpd_previa_e_execucao(
    client, test_db, tenant_a, user_a, client_a, admin_ligado, sem_efeitos_externos
):
    corpo = {"tenant_id": str(tenant_a.id), "confirmar_nome": tenant_a.name}

    # Sem pedido do dono: recusado.
    assert client.post("/api/v1/admin/lgpd/exclusao", json=corpo, headers=ADMIN).status_code == 409

    tenant_a.deletion_requested_at = datetime.now(timezone.utc)
    await test_db.commit()
    ev_id = await _auditoria(test_db, tenant_a.id, datetime.now(timezone.utc))

    # Sem token de admin: recusado.
    assert client.post("/api/v1/admin/lgpd/exclusao", json=corpo).status_code == 401
    # Nome errado: recusado.
    r = client.post("/api/v1/admin/lgpd/exclusao", json={**corpo, "confirmar_nome": "Outro"}, headers=ADMIN)
    assert r.status_code == 400

    # Prévia: conta e não apaga.
    r = client.post("/api/v1/admin/lgpd/exclusao", json=corpo, headers=ADMIN)
    assert r.status_code == 200 and r.json()["status"] == "previa"
    assert r.json()["linhas_por_tabela"]["accounting_clients"] == 1
    assert await _contar(test_db, AccountingClient, tenant_a.id) == 1

    r = client.post("/api/v1/admin/lgpd/exclusao", json={**corpo, "executar": True}, headers=ADMIN)
    assert r.status_code == 200 and r.json()["status"] == "excluido", r.text
    assert await _contar(test_db, AccountingClient, tenant_a.id) == 0
    u = (await test_db.execute(
        select(User).where(User.id == user_a.id).execution_options(populate_existing=True)
    )).scalar_one()
    assert u.email.endswith("@fiscwise.invalid") and u.is_active is False

    # Registro de acesso fica, sem o conteúdo.
    ev = (await test_db.execute(
        select(AuditEvent).where(AuditEvent.id == ev_id).execution_options(populate_existing=True)
    )).scalar_one()
    assert ev.ip_address == "203.0.113.7" and ev.after_data is None and ev.user_agent is None

    # De novo: nada a fazer.
    r = client.post("/api/v1/admin/lgpd/exclusao", json={**corpo, "executar": True}, headers=ADMIN)
    assert r.json()["status"] == "ja_excluido"


async def test_registros_de_acesso_expiram_6_meses_apos_a_exclusao(test_db, tenant_a, tenant_b):
    agora = datetime(2026, 11, 21, tzinfo=timezone.utc)
    tenant_a.dados_excluidos_em = agora - timedelta(days=200)
    tenant_b.dados_excluidos_em = agora - timedelta(days=30)
    await test_db.commit()
    antigo_a = await _auditoria(test_db, tenant_a.id, agora - timedelta(days=260))
    antigo_b = await _auditoria(test_db, tenant_b.id, agora - timedelta(days=90))

    assert await exclusao_dados.expurgar_registros_de_acesso(test_db, agora) == 1
    await test_db.commit()
    ids = set((await test_db.execute(select(AuditEvent.id))).scalars())
    assert antigo_a not in ids  # escritório excluído há mais de 6 meses
    assert antigo_b in ids  # excluído há 30 dias: ainda no prazo


async def test_exportacao_traz_as_notas_fiscais_com_xml(client_with_auth_a):
    http, user, client_a, db = client_with_auth_a
    issuer = InvoiceIssuer(
        id=uuid.uuid4(), tenant_id=user.tenant_id, client_id=client_a.id, cnpj=client_a.document,
        regime_tributario="simples", municipio_ibge="3550308", cod_servico_lc116="17.01",
        aliquota_iss=Decimal("0.02"),
    )
    db.add(issuer)
    await db.flush()
    db.add(Invoice(
        id=uuid.uuid4(), tenant_id=user.tenant_id, issuer_id=issuer.id, client_id=client_a.id,
        competencia=date(2026, 10, 1), valor_servico=Decimal("500.00"),
        descricao_servico="Consultoria", status="authorized", xml_content="<NFSe>ok</NFSe>",
    ))
    await db.commit()

    dados = http.get("/api/v1/account/export").json()["dados"]
    notas = dados["notas_fiscais_emitidas"]
    assert [n["xml_content"] for n in notas] == ["<NFSe>ok</NFSe>"]
    assert dados["emissores_nfse"][0]["cnpj"] == client_a.document
    for chave in ("guias_de_impostos", "fechamentos_mensais", "procuracoes_ecac", "certificados_a1"):
        assert dados[chave] == [], chave
