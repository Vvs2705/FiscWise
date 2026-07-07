"""Asaas gateway integration tests (hosted checkout — no card data on our side).

The single HTTP seam `billing_service._asaas_request` is monkeypatched;
env vars are read at call time, so monkeypatch.setenv works per test.
"""

import uuid
from decimal import Decimal

import pytest
from fastapi import status
from sqlalchemy import select

from app.models.billing import TenantSubscription
from app.models.plan import Plan
from app.models.tenant import SubscriptionStatus
from app.services import billing_service

pytestmark = pytest.mark.integration

CHECKOUT_URL = "https://sandbox.asaas.com/i/pay_001"


@pytest.fixture
def asaas_env(monkeypatch):
    """Gateway fully configured + fake Asaas API. Yields the recorded calls."""
    monkeypatch.setenv("BILLING_PROVIDER", "asaas")
    monkeypatch.setenv("ASAAS_API_KEY", "test-key")
    monkeypatch.setenv("ENVIRONMENT", "development")

    calls = []

    async def fake_asaas_request(method, path, json=None, allow_404=False):
        calls.append((method, path, json))
        if method == "POST" and path == "/customers":
            return {"id": "cus_001"}
        if method == "POST" and path == "/subscriptions":
            return {"id": "sub_001"}
        if method == "GET" and path == "/subscriptions/sub_001/payments":
            return {"data": [{"id": "pay_001", "invoiceUrl": CHECKOUT_URL}]}
        if method == "DELETE":
            return {"deleted": True}
        raise AssertionError(f"Unexpected Asaas call: {method} {path}")

    monkeypatch.setattr(billing_service, "_asaas_request", fake_asaas_request)
    return calls


async def _create_plan(db) -> Plan:
    plan = Plan(
        id=uuid.uuid4(),
        slug=f"premium-{uuid.uuid4().hex[:6]}",
        name="Premium",
        price_monthly=Decimal("149.90"),
    )
    db.add(plan)
    await db.commit()
    return plan


# ─── POST /billing/subscription ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_subscribe_creates_customer_and_subscription(client_with_auth_a, asaas_env):
    http_client, user, _, db = client_with_auth_a
    plan = await _create_plan(db)

    resp = http_client.post(
        "/api/v1/billing/subscription",
        json={
            "plan_id": str(plan.id),
            "billing_provider": "asaas",
            "cpf_cnpj": "12345678000199",
            "name": "Firma A LTDA",
            "email": "financeiro@firma-a.com",
        },
    )
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.json()
    assert data["checkout_url"] == CHECKOUT_URL
    assert data["billing_provider"] == "asaas"

    # Gateway received customer + subscription (billingType UNDEFINED = hosted choice)
    methods_paths = [(m, p) for m, p, _ in asaas_env]
    assert ("POST", "/customers") in methods_paths
    sub_call = next(j for m, p, j in asaas_env if p == "/subscriptions")
    assert sub_call["billingType"] == "UNDEFINED"
    assert sub_call["cycle"] == "MONTHLY"
    assert sub_call["value"] == pytest.approx(149.90)

    # Provider ids persisted
    sub = (await db.execute(
        select(TenantSubscription).where(
            TenantSubscription.tenant_id == user.tenant_id
        )
    )).scalar_one()
    assert sub.provider_customer_id == "cus_001"
    assert sub.provider_subscription_id == "sub_001"
    assert sub.status == "trialing"  # only the webhook activates


@pytest.mark.asyncio
async def test_subscribe_fails_closed_in_production_without_gateway(
    client_with_auth_a, monkeypatch
):
    http_client, _, _, db = client_with_auth_a
    plan = await _create_plan(db)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("ASAAS_API_KEY", raising=False)
    monkeypatch.delenv("BILLING_PROVIDER", raising=False)

    resp = http_client.post(
        "/api/v1/billing/subscription", json={"plan_id": str(plan.id)}
    )
    assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


@pytest.mark.asyncio
async def test_subscribe_dev_mode_without_gateway_keeps_old_flow(
    client_with_auth_a, monkeypatch
):
    http_client, _, _, db = client_with_auth_a
    plan = await _create_plan(db)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("ASAAS_API_KEY", raising=False)
    monkeypatch.delenv("BILLING_PROVIDER", raising=False)

    resp = http_client.post(
        "/api/v1/billing/subscription", json={"plan_id": str(plan.id)}
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.json()["checkout_url"] is None


# ─── Webhook /billing/webhooks/asaas ─────────────────────────────────────────

def _webhook_payload(subscription_id="sub_001", event="PAYMENT_CONFIRMED"):
    return {
        "event": event,
        "payment": {"id": f"pay_{uuid.uuid4().hex[:8]}", "subscription": subscription_id},
    }


@pytest.mark.asyncio
async def test_webhook_rejects_wrong_token(client, monkeypatch):
    monkeypatch.setenv("BILLING_WEBHOOK_SECRET", "correct-secret")
    resp = client.post(
        "/api/v1/billing/webhooks/asaas",
        json=_webhook_payload(),
        headers={"asaas-access-token": "wrong-secret"},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_webhook_fails_closed_in_production_without_secret(client, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("BILLING_WEBHOOK_SECRET", raising=False)
    resp = client.post(
        "/api/v1/billing/webhooks/asaas",
        json=_webhook_payload(),
        headers={"asaas-access-token": "anything"},
    )
    assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


@pytest.mark.asyncio
async def test_webhook_payment_confirmed_activates_subscription(
    client_with_auth_a, monkeypatch
):
    http_client, user, _, db = client_with_auth_a
    monkeypatch.setenv("BILLING_WEBHOOK_SECRET", "correct-secret")

    plan = await _create_plan(db)
    sub = TenantSubscription(
        tenant_id=user.tenant_id,
        plan_id=plan.id,
        billing_provider="asaas",
        provider_customer_id="cus_001",
        provider_subscription_id="sub_001",
        status="trialing",
        amount=plan.price_monthly,
        currency="BRL",
    )
    db.add(sub)
    await db.commit()

    resp = http_client.post(
        "/api/v1/billing/webhooks/asaas",
        json=_webhook_payload("sub_001", "PAYMENT_CONFIRMED"),
        headers={"asaas-access-token": "correct-secret"},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "processed"

    await db.refresh(sub)
    assert sub.status == "active"

    from app.models.tenant import Tenant
    tenant = await db.get(Tenant, user.tenant_id)
    await db.refresh(tenant)
    assert tenant.subscription_status == SubscriptionStatus.ACTIVE
    assert tenant.plan_slug == plan.slug


@pytest.mark.asyncio
async def test_webhook_payment_overdue_marks_past_due(client_with_auth_a, monkeypatch):
    http_client, user, _, db = client_with_auth_a
    monkeypatch.setenv("BILLING_WEBHOOK_SECRET", "correct-secret")

    plan = await _create_plan(db)
    sub = TenantSubscription(
        tenant_id=user.tenant_id,
        plan_id=plan.id,
        billing_provider="asaas",
        provider_subscription_id="sub_001",
        status="active",
        currency="BRL",
    )
    db.add(sub)
    await db.commit()

    resp = http_client.post(
        "/api/v1/billing/webhooks/asaas",
        json=_webhook_payload("sub_001", "PAYMENT_OVERDUE"),
        headers={"asaas-access-token": "correct-secret"},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "processed"

    await db.refresh(sub)
    assert sub.status == "past_due"
