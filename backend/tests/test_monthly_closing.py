"""Tests for Monthly Closing domain — fechamento mensal e dossiê fiscal."""
import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_password_hash
from app.models.tenant import Tenant, SubscriptionStatus
from app.models.user import User, UserRole
from app.models.operations import AccountingClient
from app.domain.monthly_closing.models import (
    MonthlyClosing, MonthlyClosingItem, ClosingStatus, ClosingItemStatus
)


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _auth_client(app, db: AsyncSession, user: User) -> TestClient:
    from app.core.deps import get_db
    app.dependency_overrides[get_db] = lambda: db
    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        role=user.role.value,
    )
    c = TestClient(app, raise_server_exceptions=False)
    c.headers.update({
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(user.tenant_id),
    })
    return c


async def _bootstrap(db: AsyncSession, suffix: str):
    tenant = Tenant(id=uuid.uuid4(), name=f"MC_{suffix}", subscription_status=SubscriptionStatus.TRIAL)
    db.add(tenant)
    await db.flush()
    user = User(
        id=uuid.uuid4(), email=f"mc_{suffix}@test.com",
        hashed_password=get_password_hash("Pw123456!"),
        full_name=f"MC {suffix}", tenant_id=tenant.id,
        role=UserRole.OWNER, is_active=True,
    )
    db.add(user)
    client = AccountingClient(
        id=uuid.uuid4(), tenant_id=tenant.id,
        name=f"Client {suffix}", document="76069336914468",
        entity_type="pj", status="active",
    )
    db.add(client)
    await db.commit()
    return tenant, user, client


# ─── Tests ────────────────────────────────────────────────────────────────────


class TestMonthlyClosingCRUD:
    @pytest.mark.asyncio
    async def test_create_closing_returns_201(self, test_db: AsyncSession):
        from app.main import app
        _, user, client = await _bootstrap(test_db, "cr1")
        http = _auth_client(app, test_db, user)

        payload = {"client_id": str(client.id), "competence": "2026-01"}
        resp = http.post("/api/v1/monthly-closings", json=payload)
        app.dependency_overrides.clear()

        assert resp.status_code == 201
        data = resp.json()
        assert data["competence"] == "2026-01"
        assert data["status"] == ClosingStatus.OPEN.value

    @pytest.mark.asyncio
    async def test_duplicate_closing_returns_409(self, test_db: AsyncSession):
        from app.main import app
        tenant, user, client = await _bootstrap(test_db, "dup")

        closing = MonthlyClosing(
            id=uuid.uuid4(), tenant_id=tenant.id, client_id=client.id,
            competence="2026-03", status=ClosingStatus.OPEN.value,
        )
        test_db.add(closing)
        await test_db.commit()

        http = _auth_client(app, test_db, user)
        payload = {"client_id": str(client.id), "competence": "2026-03"}
        resp = http.post("/api/v1/monthly-closings", json=payload)
        app.dependency_overrides.clear()

        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_close_with_pending_required_items_returns_409(self, test_db: AsyncSession):
        from app.main import app
        tenant, user, client = await _bootstrap(test_db, "cl1")

        closing = MonthlyClosing(
            id=uuid.uuid4(), tenant_id=tenant.id, client_id=client.id,
            competence="2026-04", status=ClosingStatus.IN_PROGRESS.value,
        )
        test_db.add(closing)
        await test_db.flush()

        # Add a required pending item
        test_db.add(MonthlyClosingItem(
            id=uuid.uuid4(), tenant_id=tenant.id, closing_id=closing.id,
            item_type="guide", item_status=ClosingItemStatus.PENDING.value,
            description="DAS jan/26", is_required=True,
        ))
        await test_db.commit()

        http = _auth_client(app, test_db, user)
        resp = http.post(f"/api/v1/monthly-closings/{closing.id}/close")
        app.dependency_overrides.clear()

        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_close_without_pending_items_succeeds(self, test_db: AsyncSession):
        from app.main import app
        tenant, user, client = await _bootstrap(test_db, "cl2")

        closing = MonthlyClosing(
            id=uuid.uuid4(), tenant_id=tenant.id, client_id=client.id,
            competence="2026-05", status=ClosingStatus.OPEN.value,
        )
        test_db.add(closing)
        await test_db.commit()

        http = _auth_client(app, test_db, user)
        resp = http.post(f"/api/v1/monthly-closings/{closing.id}/close")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == ClosingStatus.CLOSED.value
        assert data["closed_at"] is not None

    @pytest.mark.asyncio
    async def test_reopen_closed_closing(self, test_db: AsyncSession):
        from app.main import app
        tenant, user, client = await _bootstrap(test_db, "ro1")

        closing = MonthlyClosing(
            id=uuid.uuid4(), tenant_id=tenant.id, client_id=client.id,
            competence="2026-06", status=ClosingStatus.CLOSED.value,
        )
        test_db.add(closing)
        await test_db.commit()

        http = _auth_client(app, test_db, user)
        resp = http.post(f"/api/v1/monthly-closings/{closing.id}/reopen")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        assert resp.json()["status"] == ClosingStatus.REOPENED.value

    @pytest.mark.asyncio
    async def test_add_item_to_closing(self, test_db: AsyncSession):
        from app.main import app
        tenant, user, client = await _bootstrap(test_db, "ai1")

        closing = MonthlyClosing(
            id=uuid.uuid4(), tenant_id=tenant.id, client_id=client.id,
            competence="2026-07", status=ClosingStatus.OPEN.value,
        )
        test_db.add(closing)
        await test_db.commit()

        http = _auth_client(app, test_db, user)
        payload = {
            "item_type": "guide",
            "description": "DAS jul/26",
            "amount": "300.00",
            "is_required": True,
        }
        resp = http.post(f"/api/v1/monthly-closings/{closing.id}/items", json=payload)
        app.dependency_overrides.clear()

        assert resp.status_code == 201
        data = resp.json()
        assert data["item_status"] == ClosingItemStatus.PENDING.value

    @pytest.mark.asyncio
    async def test_generate_dossier(self, test_db: AsyncSession):
        from app.main import app
        tenant, user, client = await _bootstrap(test_db, "dos1")

        closing = MonthlyClosing(
            id=uuid.uuid4(), tenant_id=tenant.id, client_id=client.id,
            competence="2026-08", status=ClosingStatus.CLOSED.value,
        )
        test_db.add(closing)
        await test_db.commit()

        http = _auth_client(app, test_db, user)
        resp = http.post(f"/api/v1/monthly-closings/{closing.id}/dossier/generate")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        data = resp.json()
        assert data["closing_id"] == str(closing.id)
        assert data["competence"] == "2026-08"


class TestMonthlyClosingCrossTenant:
    @pytest.mark.asyncio
    async def test_closing_from_other_tenant_returns_404(self, test_db: AsyncSession):
        from app.main import app
        tenant_a, _, client_a = await _bootstrap(test_db, "ctA")
        _, user_b, _ = await _bootstrap(test_db, "ctB")

        closing = MonthlyClosing(
            id=uuid.uuid4(), tenant_id=tenant_a.id, client_id=client_a.id,
            competence="2026-09", status=ClosingStatus.OPEN.value,
        )
        test_db.add(closing)
        await test_db.commit()

        http_b = _auth_client(app, test_db, user_b)
        resp = http_b.get(f"/api/v1/monthly-closings/{closing.id}")
        app.dependency_overrides.clear()

        assert resp.status_code == 404
