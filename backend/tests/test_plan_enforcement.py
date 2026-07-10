"""Enforcement de assinatura/trial (plano pago só com pagamento em dia).

Cobre:
  (a) assinatura suspensa/cancelada → features pagas negadas (degrada p/ free)
  (b) trial expirado → degrada p/ free
  (c) trial vigente → plano escolhido vale
  (d) onboarding com plan_slug pago → tenant no plano + sub trialing de 14 dias
  (e) webhook de ativação (Mercado Pago) → atualiza tenant.plan_slug
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.plan_access import PLAN_FREE, effective_plan_slug, resolve_tenant_plan
from app.core.security import create_access_token, get_password_hash
from app.models.billing import TenantSubscription
from app.models.plan import Plan
from app.models.tenant import Tenant, SubscriptionStatus
from app.models.user import User, UserRole


AGORA = datetime.now(timezone.utc)


def _tenant_stub(plan_slug="premium", subscription=None):
    return SimpleNamespace(plan_slug=plan_slug, subscription=subscription)


def _sub_stub(status="trialing", trial_ends_at=None):
    return SimpleNamespace(status=status, trial_ends_at=trial_ends_at)


# ---------------------------------------------------------------------------
# Unit: effective_plan_slug (raiz do enforcement)
# ---------------------------------------------------------------------------


class TestEffectivePlanSlug:
    def test_sub_suspensa_degrada_para_free(self):
        tenant = _tenant_stub("premium", _sub_stub(status="suspended"))
        assert effective_plan_slug(tenant) == PLAN_FREE
        assert resolve_tenant_plan(tenant, "qualquer@x.com") == PLAN_FREE

    def test_sub_cancelada_degrada_para_free(self):
        tenant = _tenant_stub("intermediario", _sub_stub(status="cancelled"))
        assert effective_plan_slug(tenant) == PLAN_FREE

    def test_trial_expirado_degrada_para_free(self):
        tenant = _tenant_stub(
            "premium",
            _sub_stub(status="trialing", trial_ends_at=AGORA - timedelta(days=1)),
        )
        assert effective_plan_slug(tenant) == PLAN_FREE

    def test_trial_expirado_naive_datetime_degrada(self):
        # SQLite devolve datetimes naive — o helper precisa tratar.
        naive_passado = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
        tenant = _tenant_stub(
            "premium", _sub_stub(status="trialing", trial_ends_at=naive_passado)
        )
        assert effective_plan_slug(tenant) == PLAN_FREE

    def test_trial_vigente_mantem_plano_escolhido(self):
        tenant = _tenant_stub(
            "premium",
            _sub_stub(status="trialing", trial_ends_at=AGORA + timedelta(days=10)),
        )
        assert effective_plan_slug(tenant) == "premium"

    def test_trialing_sem_trial_ends_at_nunca_degrada(self):
        tenant = _tenant_stub("premium", _sub_stub(status="trialing", trial_ends_at=None))
        assert effective_plan_slug(tenant) == "premium"

    def test_sub_active_mantem_plano(self):
        tenant = _tenant_stub("premium", _sub_stub(status="active"))
        assert effective_plan_slug(tenant) == "premium"

    def test_past_due_mantem_plano_periodo_de_graca(self):
        tenant = _tenant_stub("premium", _sub_stub(status="past_due"))
        assert effective_plan_slug(tenant) == "premium"

    def test_tenant_legado_sem_subscription_nao_degrada(self):
        tenant = _tenant_stub("premium", subscription=None)
        assert effective_plan_slug(tenant) == "premium"

    def test_tenant_none_devolve_none(self):
        assert effective_plan_slug(None) is None


# ---------------------------------------------------------------------------
# Fixtures de integração (tenant premium + user + client autenticado)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def premium_setup(test_db: AsyncSession):
    """Tenant com plan_slug=premium, plano premium no banco e owner user."""
    plan = Plan(
        id=uuid.uuid4(), slug="premium", name="Premium",
        price_monthly=Decimal("299.00"), active=True,
    )
    tenant = Tenant(
        id=uuid.uuid4(), name="Firma Premium",
        subscription_status=SubscriptionStatus.TRIAL, plan_slug="premium",
    )
    test_db.add_all([plan, tenant])
    await test_db.flush()
    user = User(
        id=uuid.uuid4(), tenant_id=tenant.id, email="dono@premium.com",
        hashed_password=get_password_hash("Password123!"),
        role=UserRole.OWNER, is_active=True,
    )
    test_db.add(user)
    await test_db.commit()
    return plan, tenant, user


@pytest.fixture
def authed_client(test_db: AsyncSession):
    """Factory: TestClient autenticado para um user."""
    from app.main import app
    from app.core.deps import get_db

    app.dependency_overrides[get_db] = lambda: test_db
    created = []

    def _make(user: User) -> TestClient:
        http_client = TestClient(app)
        token = create_access_token(
            user_id=str(user.id), tenant_id=str(user.tenant_id), role=user.role.value,
        )
        http_client.headers.update({
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": str(user.tenant_id),
        })
        created.append(http_client)
        return http_client

    yield _make
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# (a)/(b)/(c) Integração: paywall degrada conforme a assinatura
# ---------------------------------------------------------------------------


PDF_PAYLOAD = {"simulation_id": str(uuid.uuid4())}  # 403 dispara antes do fetch


@pytest.mark.asyncio
async def test_sub_suspensa_nega_feature_premium(test_db, premium_setup, authed_client):
    plan, tenant, user = premium_setup
    test_db.add(TenantSubscription(
        tenant_id=tenant.id, plan_id=plan.id, status="suspended",
        billing_cycle="mensal", amount=plan.price_monthly,
    ))
    await test_db.commit()

    client = authed_client(user)
    resp = client.post("/api/v1/calculator/export-pdf", json=PDF_PAYLOAD)
    assert resp.status_code == 403, resp.text

    # A visão do tenant também mostra o plano degradado
    resp = client.get("/api/v1/auth/tenant")
    assert resp.status_code == 200
    assert resp.json()["plan_slug"] == "free"


@pytest.mark.asyncio
async def test_trial_expirado_degrada_para_free(test_db, premium_setup, authed_client):
    plan, tenant, user = premium_setup
    test_db.add(TenantSubscription(
        tenant_id=tenant.id, plan_id=plan.id, status="trialing",
        trial_ends_at=datetime.now(timezone.utc) - timedelta(days=1),
        billing_cycle="mensal", amount=plan.price_monthly,
    ))
    await test_db.commit()

    client = authed_client(user)
    resp = client.post("/api/v1/calculator/export-pdf", json=PDF_PAYLOAD)
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_trial_vigente_plano_escolhido_vale(test_db, premium_setup, authed_client):
    plan, tenant, user = premium_setup
    test_db.add(TenantSubscription(
        tenant_id=tenant.id, plan_id=plan.id, status="trialing",
        trial_ends_at=datetime.now(timezone.utc) + timedelta(days=14),
        billing_cycle="mensal", amount=plan.price_monthly,
    ))
    await test_db.commit()

    client = authed_client(user)
    # Passa o paywall premium: 404 (simulação inexistente), não 403.
    resp = client.post("/api/v1/calculator/export-pdf", json=PDF_PAYLOAD)
    assert resp.status_code == 404, resp.text

    resp = client.get("/api/v1/auth/tenant")
    assert resp.json()["plan_slug"] == "premium"


@pytest.mark.asyncio
async def test_tenant_legado_sem_sub_continua_funcionando(test_db, premium_setup, authed_client):
    _, tenant, user = premium_setup  # nenhuma TenantSubscription criada

    client = authed_client(user)
    resp = client.post("/api/v1/calculator/export-pdf", json=PDF_PAYLOAD)
    assert resp.status_code == 404, resp.text  # paywall passou (não degradou)


# ---------------------------------------------------------------------------
# (d) Onboarding com plano escolhido → trial honesto de 14 dias
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def register_client(test_db: AsyncSession):
    from app.main import app
    from app.core.deps import get_db

    app.dependency_overrides[get_db] = lambda: test_db
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_onboarding_premium_cria_trial_de_14_dias(register_client, test_db):
    plan = Plan(
        id=uuid.uuid4(), slug="premium", name="Premium",
        price_monthly=Decimal("299.00"), active=True,
    )
    test_db.add(plan)
    await test_db.commit()

    resp = register_client.post("/api/v1/onboarding/register", json={
        "company_name": "Escritório Trial Premium",
        "owner_email": "trial@premium.com",
        "owner_password": "SenhaSegura123!",
        "plan_slug": "premium",
        "terms_accepted": True,
    })
    assert resp.status_code == 200, resp.text
    tenant_id = uuid.UUID(resp.json()["tenant_id"])

    tenant = (
        await test_db.execute(select(Tenant).where(Tenant.id == tenant_id))
    ).scalar_one()
    assert tenant.plan_slug == "premium"

    sub = (
        await test_db.execute(
            select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id)
        )
    ).scalar_one()
    assert sub.status == "trialing"
    assert sub.plan_id == plan.id
    assert sub.billing_cycle == "mensal"

    trial_ends = sub.trial_ends_at
    if trial_ends.tzinfo is None:
        trial_ends = trial_ends.replace(tzinfo=timezone.utc)
    delta = trial_ends - datetime.now(timezone.utc)
    assert timedelta(days=13) < delta <= timedelta(days=14)


@pytest.mark.asyncio
async def test_onboarding_free_sem_subscription(register_client, test_db):
    resp = register_client.post("/api/v1/onboarding/register", json={
        "company_name": "Escritório Free",
        "owner_email": "free@escritorio.com",
        "owner_password": "SenhaSegura123!",
        "terms_accepted": True,
    })
    assert resp.status_code == 200, resp.text
    tenant_id = uuid.UUID(resp.json()["tenant_id"])

    tenant = (
        await test_db.execute(select(Tenant).where(Tenant.id == tenant_id))
    ).scalar_one()
    assert tenant.plan_slug == "free"

    sub = (
        await test_db.execute(
            select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id)
        )
    ).scalar_one_or_none()
    assert sub is None  # free: sem trial, nunca degrada


@pytest.mark.asyncio
async def test_onboarding_plano_invalido_retorna_400(register_client, test_db):
    resp = register_client.post("/api/v1/onboarding/register", json={
        "company_name": "Escritório Hacker",
        "owner_email": "hacker@plano.com",
        "owner_password": "SenhaSegura123!",
        "plan_slug": "enterprise-gratis",
        "terms_accepted": True,
    })
    assert resp.status_code == 400
    assert resp.headers.get("X-Error-Code") == "INVALID_PLAN"


@pytest.mark.asyncio
async def test_onboarding_plano_inativo_retorna_400(register_client, test_db):
    plan = Plan(
        id=uuid.uuid4(), slug="premium-anual", name="Premium Anual (legado)",
        price_monthly=Decimal("249.00"), active=False,
    )
    test_db.add(plan)
    await test_db.commit()

    resp = register_client.post("/api/v1/onboarding/register", json={
        "company_name": "Escritório Legado",
        "owner_email": "legado@plano.com",
        "owner_password": "SenhaSegura123!",
        "plan_slug": "premium-anual",
        "terms_accepted": True,
    })
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# (e) Webhook Mercado Pago: ativação seta tenant.plan_slug
# ---------------------------------------------------------------------------


class _FakeGatewayPreapproval:
    def __init__(self, valor: float):
        self.valor = valor

    def configurado(self) -> bool:
        return True

    async def obter_preapproval(self, recurso_id: str) -> dict:
        return {
            "status": "authorized",
            "auto_recurring": {"transaction_amount": self.valor},
        }


class _FakeGatewayPayment:
    def __init__(self, valor: float, external_reference: str):
        self.valor = valor
        self.external_reference = external_reference

    def configurado(self) -> bool:
        return True

    async def obter_pagamento(self, recurso_id: str) -> dict:
        return {
            "status": "approved",
            "external_reference": self.external_reference,
            "transaction_amount": self.valor,
        }


@pytest.mark.asyncio
async def test_webhook_preapproval_ativa_e_seta_plan_slug(
    test_db, premium_setup, register_client, monkeypatch
):
    plan, tenant, _ = premium_setup
    assert tenant.plan_slug == "premium"
    tenant.plan_slug = "free"  # cliente ainda no free; pagou agora
    sub = TenantSubscription(
        tenant_id=tenant.id, plan_id=plan.id, status="trialing",
        billing_cycle="mensal", amount=plan.price_monthly,
        provider_subscription_id="pre_teste_123", billing_provider="mercadopago",
    )
    test_db.add(sub)
    await test_db.commit()

    from app.api.v1.endpoints import billing as billing_ep
    from app.core.config import settings

    monkeypatch.setattr(settings, "MERCADO_PAGO_WEBHOOK_SECRET", "", raising=False)
    monkeypatch.setattr(billing_ep, "gateway", _FakeGatewayPreapproval(299.0))

    resp = register_client.post(
        "/api/v1/billing/webhook/mercadopago",
        json={"id": "evt-1", "type": "preapproval", "data": {"id": "pre_teste_123"}},
    )
    assert resp.status_code == 200, resp.text

    await test_db.refresh(sub)
    await test_db.refresh(tenant)
    assert sub.status == "active"
    assert tenant.plan_slug == "premium"
    assert tenant.subscription_status == SubscriptionStatus.ACTIVE


@pytest.mark.asyncio
async def test_webhook_payment_prepago_ativa_e_seta_plan_slug(
    test_db, premium_setup, register_client, monkeypatch
):
    from app.core.pricing import valores_aceitos

    plan, tenant, _ = premium_setup
    tenant.plan_slug = "free"
    sub = TenantSubscription(
        tenant_id=tenant.id, plan_id=plan.id, status="trialing",
        billing_cycle="anual", amount=plan.price_monthly,
        billing_provider="mercadopago",
    )
    test_db.add(sub)
    await test_db.commit()

    valor_pago = sorted(valores_aceitos(plan.price_monthly, "anual"))[0]

    from app.api.v1.endpoints import billing as billing_ep
    from app.core.config import settings

    monkeypatch.setattr(settings, "MERCADO_PAGO_WEBHOOK_SECRET", "", raising=False)
    monkeypatch.setattr(
        billing_ep, "gateway", _FakeGatewayPayment(valor_pago, str(sub.id))
    )

    resp = register_client.post(
        "/api/v1/billing/webhook/mercadopago",
        json={"id": "evt-2", "type": "payment", "data": {"id": "999888777"}},
    )
    assert resp.status_code == 200, resp.text

    await test_db.refresh(sub)
    await test_db.refresh(tenant)
    assert sub.status == "active"
    assert tenant.plan_slug == "premium"
