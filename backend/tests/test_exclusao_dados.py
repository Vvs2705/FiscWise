"""Exclusão automática dos dados de contas vencidas (aviso 72 h antes).

Regra: vencida há 57 dias → aviso por e-mail (só marca se o provedor aceitou);
vencida há 60 dias e aviso há 72 h → exclui. Quem assinou depois do aviso é
poupado; conta da equipe, pedido LGPD em tratamento e interruptor desligado
nunca excluem.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.core.document_links import storage_ref
from app.models.billing import BillingWebhookEvent, TenantSubscription
from app.models.operations import AccountingClient, AccountReceivable, ClientDocument
from app.models.tenant import Tenant
from app.models.user import User
from app.services import scheduler
from tests.test_plan_enforcement import premium_setup  # noqa: F401

AGORA = datetime(2026, 11, 14, 6, 30, tzinfo=timezone.utc)  # 03:30 em Brasília


def _aware(dt):
    return dt.replace(tzinfo=timezone.utc) if dt is not None and dt.tzinfo is None else dt


@pytest.fixture
def emails(monkeypatch):
    from app.services import email_service

    enviados: list[tuple[str, str]] = []
    estado = {"aceita": True}

    async def fake_send(to, subject, html, idempotency_key=None):
        if estado["aceita"]:
            enviados.append((to, subject))
        return estado["aceita"]

    monkeypatch.setattr(email_service, "send_email", fake_send)
    return enviados, estado


@pytest.fixture
def arquivos(monkeypatch):
    from app.core import storage

    removidos: list[tuple[str, list[str]]] = []

    async def fake_remove(bucket, paths):
        removidos.append((bucket, list(paths)))
        return len(paths)

    async def fake_list(bucket, prefix, **_):
        return []

    monkeypatch.setattr(storage, "remove_objects", fake_remove)
    monkeypatch.setattr(storage, "list_prefix", fake_list)
    return removidos


async def _conta_vencida(test_db, plan, tenant, dias_vencida: float, avisada_ha_horas: float | None = None):
    sub = TenantSubscription(
        tenant_id=tenant.id, plan_id=plan.id, status="trialing",
        trial_ends_at=AGORA - timedelta(days=dias_vencida),
        billing_cycle="mensal", amount=plan.price_monthly, billing_provider="mercadopago",
    )
    test_db.add(sub)
    cliente = AccountingClient(
        id=uuid.uuid4(), tenant_id=tenant.id, name="Cliente Exclusão",
        document="11222333000181", status="active",
    )
    test_db.add(cliente)
    await test_db.flush()
    test_db.add_all([
        ClientDocument(
            tenant_id=tenant.id, client_id=cliente.id, name="contrato.pdf",
            file_url=storage_ref(f"{tenant.id}/abc.pdf"),
        ),
        AccountReceivable(
            tenant_id=tenant.id, client_id=cliente.id, description="Honorários",
            amount=Decimal("100.00"), due_date=date(2026, 8, 10), status="pending",
        ),
        BillingWebhookEvent(provider="mercadopago", event_id=f"evt-{tenant.id}", event_type="payment", payload={}),
    ])
    if avisada_ha_horas is not None:
        tenant.exclusao_avisada_em = AGORA - timedelta(hours=avisada_ha_horas)
    await test_db.commit()
    return sub, cliente


async def _contar(test_db, model, tenant_id):
    return (await test_db.execute(select(func.count()).select_from(model).where(model.tenant_id == tenant_id))).scalar_one()


async def _rodar(test_db, agora=AGORA):
    return await scheduler.excluir_dados_vencidos_scheduled(now=agora)


async def _ler(test_db, model, obj_id):
    """Relê do banco (a rotina grava em outra sessão)."""
    return (
        await test_db.execute(
            select(model).where(model.id == obj_id).execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()


@pytest.mark.asyncio
async def test_aviso_no_dia_57_so_marca_com_envio_aceito(test_db, premium_setup, emails):  # noqa: F811
    plan, tenant, user = premium_setup
    tenant_id, user_id, user_email = tenant.id, user.id, user.email
    enviados, estado = emails
    await _conta_vencida(test_db, plan, tenant, dias_vencida=57.1)

    estado["aceita"] = False
    res = await _rodar(test_db)
    assert res["aviso_falhou"] == 1
    t = await _ler(test_db, Tenant, tenant_id)
    assert t.exclusao_avisada_em is None

    estado["aceita"] = True
    res = await _rodar(test_db)
    assert res["avisados"] == 1
    t = await _ler(test_db, Tenant, tenant_id)
    assert _aware(t.exclusao_avisada_em) == AGORA
    assert enviados[-1][0] == user_email
    assert "serão excluídos" in enviados[-1][1]

    # Dia 56: ainda não avisa ninguém.
    res = await _rodar(test_db, AGORA - timedelta(days=2))
    assert res["avisados"] == 0


@pytest.mark.asyncio
async def test_sem_aviso_no_dia_60_avisa_e_nao_exclui(test_db, premium_setup, emails, arquivos):  # noqa: F811
    plan, tenant, _ = premium_setup
    tenant_id = tenant.id
    await _conta_vencida(test_db, plan, tenant, dias_vencida=61)
    res = await _rodar(test_db)
    assert res["avisados"] == 1 and res["excluidos"] == 0
    assert await _contar(test_db, AccountingClient, tenant_id) == 1
    assert arquivos == []


@pytest.mark.asyncio
async def test_nao_exclui_antes_de_72_horas_do_aviso(test_db, premium_setup, emails, arquivos):  # noqa: F811
    plan, tenant, _ = premium_setup
    tenant_id = tenant.id
    await _conta_vencida(test_db, plan, tenant, dias_vencida=61, avisada_ha_horas=71)
    res = await _rodar(test_db)
    assert res["excluidos"] == 0
    assert await _contar(test_db, AccountingClient, tenant_id) == 1


@pytest.mark.asyncio
async def test_exclui_no_dia_60_com_aviso_de_72_horas(test_db, premium_setup, emails, arquivos):  # noqa: F811
    plan, tenant, user = premium_setup
    tenant_id, user_id, user_email = tenant.id, user.id, user.email
    enviados, _ = emails
    email_original = user_email
    await _conta_vencida(test_db, plan, tenant, dias_vencida=60.2, avisada_ha_horas=73)

    res = await _rodar(test_db)
    assert res["excluidos"] == 1, res

    # Apagado
    assert await _contar(test_db, AccountingClient, tenant_id) == 0
    assert await _contar(test_db, ClientDocument, tenant_id) == 0
    assert await _contar(test_db, AccountReceivable, tenant_id) == 0
    assert arquivos == [("documents", [f"{tenant_id}/abc.pdf"])]
    # Mantido
    t = await _ler(test_db, Tenant, tenant_id)
    assert t is not None and t.name == "Firma Premium"
    assert _aware(t.dados_excluidos_em) == AGORA
    assert await _contar(test_db, TenantSubscription, tenant_id) == 1
    assert (await test_db.execute(select(func.count()).select_from(BillingWebhookEvent))).scalar_one() >= 1
    # Usuário anonimizado e desativado
    u = await _ler(test_db, User, user_id)
    assert u.email.endswith("@fiscwise.invalid") and u.is_active is False and u.full_name is None
    # Confirmação ao e-mail capturado antes de anonimizar
    assert (email_original, "Seus dados no FiscWise foram excluídos") in enviados

    # Idempotente: rodar de novo não faz nada.
    res = await _rodar(test_db, AGORA + timedelta(days=1))
    assert res["excluidos"] == 0 and res["avisados"] == 0 and res["falhas"] == 0


@pytest.mark.asyncio
async def test_quem_assinou_depois_do_aviso_e_poupado(test_db, premium_setup, emails, arquivos):  # noqa: F811
    plan, tenant, _ = premium_setup
    tenant_id = tenant.id
    sub, _ = await _conta_vencida(test_db, plan, tenant, dias_vencida=61, avisada_ha_horas=100)
    sub.status = "active"
    sub.current_period_end = AGORA + timedelta(days=30)
    await test_db.commit()

    res = await _rodar(test_db)
    assert res["excluidos"] == 0 and res["aviso_cancelado"] == 1
    t = await _ler(test_db, Tenant, tenant_id)
    assert t.exclusao_avisada_em is None and t.dados_excluidos_em is None
    assert await _contar(test_db, AccountingClient, tenant_id) == 1


@pytest.mark.asyncio
async def test_interruptor_desligado_nao_exclui(test_db, premium_setup, emails, arquivos, monkeypatch):  # noqa: F811
    plan, tenant, _ = premium_setup
    tenant_id = tenant.id
    monkeypatch.setenv("EXCLUSAO_AUTOMATICA_ATIVA", "false")
    await _conta_vencida(test_db, plan, tenant, dias_vencida=61, avisada_ha_horas=100)
    res = await _rodar(test_db)
    assert res["excluidos"] == 0 and res["poupados"] == 1
    assert await _contar(test_db, AccountingClient, tenant_id) == 1


@pytest.mark.asyncio
async def test_conta_da_equipe_e_pedido_lgpd_nunca_excluem(test_db, premium_setup, emails, arquivos, monkeypatch):  # noqa: F811
    from app.core import plan_access

    plan, tenant, user = premium_setup
    tenant_id, user_id, user_email = tenant.id, user.id, user.email
    await _conta_vencida(test_db, plan, tenant, dias_vencida=61, avisada_ha_horas=100)

    monkeypatch.setattr(plan_access, "_SUPERUSER_EMAILS", frozenset({user_email.lower()}))
    res = await _rodar(test_db)
    assert res["excluidos"] == 0 and res["protegidos"] == 1

    monkeypatch.setattr(plan_access, "_SUPERUSER_EMAILS", frozenset())
    t = await _ler(test_db, Tenant, tenant_id)
    t.deletion_requested_at = AGORA - timedelta(days=1)
    await test_db.commit()
    res = await _rodar(test_db)
    assert res["excluidos"] == 0 and res["protegidos"] == 1
    assert await _contar(test_db, AccountingClient, tenant_id) == 1


@pytest.mark.asyncio
async def test_rota_mostra_a_data_prevista(test_db, premium_setup, emails):  # noqa: F811
    from tests.test_plan_enforcement import authed_client  # noqa: F401

    plan, tenant, _ = premium_setup
    tenant_id = tenant.id
    await _conta_vencida(test_db, plan, tenant, dias_vencida=58, avisada_ha_horas=24)
    from app.services.exclusao_dados import exclusao_prevista

    t = await _ler(test_db, Tenant, tenant_id)
    prevista = exclusao_prevista(t)
    venc = AGORA - timedelta(days=58)
    assert prevista == max(venc + timedelta(days=60), AGORA - timedelta(hours=24) + timedelta(hours=72))
