"""Tests for Fiscal Guides domain — DAS, DARF, DAE, GPS, DCTFWeb."""
import uuid
from decimal import Decimal
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.tenant import Tenant, SubscriptionStatus
from app.models.user import User, UserRole
from app.models.operations import AccountingClient
from app.domain.fiscal_guides.models import FiscalGuide, FiscalGuideEvent, GuideStatus


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
    from app.core.security import get_password_hash
    tenant = Tenant(id=uuid.uuid4(), name=f"T_{suffix}", subscription_status=SubscriptionStatus.TRIAL)
    db.add(tenant)
    await db.flush()
    user = User(
        id=uuid.uuid4(), email=f"u_{suffix}@test.com",
        hashed_password=get_password_hash("Pw123456!"),
        full_name=f"U {suffix}", tenant_id=tenant.id,
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


class TestFiscalGuideCRUD:
    @pytest.mark.asyncio
    async def test_create_guide_returns_201(self, test_db: AsyncSession):
        from app.main import app
        tenant, user, client = await _bootstrap(test_db, "fg1")
        http = _auth_client(app, test_db, user)

        payload = {
            "client_id": str(client.id),
            "guide_type": "DAS",
            "competence": "2026-01",
            "due_date": "2026-02-20",
            "amount": "350.00",
        }
        resp = http.post("/api/v1/fiscal-guides", json=payload)
        app.dependency_overrides.clear()

        assert resp.status_code == 201
        data = resp.json()
        assert data["guide_type"] == "DAS"
        assert data["status"] == GuideStatus.DRAFT.value
        assert data["competence"] == "2026-01"

    @pytest.mark.asyncio
    async def test_list_guides_filtered_by_type(self, test_db: AsyncSession):
        from app.main import app
        tenant, user, client = await _bootstrap(test_db, "fg2")

        # Create two guides with different types
        for guide_type in ("DAS", "DARF"):
            test_db.add(FiscalGuide(
                id=uuid.uuid4(), tenant_id=tenant.id, client_id=client.id,
                guide_type=guide_type, competence="2026-01",
                due_date=date(2026, 2, 20), amount=Decimal("200.00"),
                status=GuideStatus.DRAFT.value,
            ))
        await test_db.commit()

        http = _auth_client(app, test_db, user)
        resp = http.get("/api/v1/fiscal-guides?guide_type=DAS")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        results = resp.json()
        assert all(g["guide_type"] == "DAS" for g in results)

    @pytest.mark.asyncio
    async def test_get_guide_404_not_found(self, test_db: AsyncSession):
        from app.main import app
        _, user, _ = await _bootstrap(test_db, "fg3")
        http = _auth_client(app, test_db, user)

        resp = http.get(f"/api/v1/fiscal-guides/{uuid.uuid4()}")
        app.dependency_overrides.clear()

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_mark_guide_paid_transitions_status(self, test_db: AsyncSession):
        from app.main import app
        tenant, user, client = await _bootstrap(test_db, "fg4")
        guide = FiscalGuide(
            id=uuid.uuid4(), tenant_id=tenant.id, client_id=client.id,
            guide_type="DAS", competence="2026-01",
            due_date=date(2026, 2, 20), amount=Decimal("400.00"),
            status=GuideStatus.AWAITING_PAYMENT.value,
        )
        test_db.add(guide)
        await test_db.commit()

        http = _auth_client(app, test_db, user)
        resp = http.post(f"/api/v1/fiscal-guides/{guide.id}/mark-paid")
        app.dependency_overrides.clear()

        assert resp.status_code == 200
        assert resp.json()["status"] == GuideStatus.PAID.value
        assert resp.json()["paid_at"] is not None

    @pytest.mark.asyncio
    async def test_cancel_paid_guide_returns_409(self, test_db: AsyncSession):
        from app.main import app
        tenant, user, client = await _bootstrap(test_db, "fg5")
        guide = FiscalGuide(
            id=uuid.uuid4(), tenant_id=tenant.id, client_id=client.id,
            guide_type="DARF", competence="2026-02",
            due_date=date(2026, 3, 30), amount=Decimal("150.00"),
            status=GuideStatus.PAID.value,
        )
        test_db.add(guide)
        await test_db.commit()

        http = _auth_client(app, test_db, user)
        resp = http.post(f"/api/v1/fiscal-guides/{guide.id}/cancel")
        app.dependency_overrides.clear()

        assert resp.status_code == 409


class TestFiscalGuideCrossTenant:
    @pytest.mark.asyncio
    async def test_guide_from_other_tenant_returns_404(self, test_db: AsyncSession):
        from app.main import app
        tenant_a, user_a, client_a = await _bootstrap(test_db, "fgA")
        _, user_b, _ = await _bootstrap(test_db, "fgB")

        guide = FiscalGuide(
            id=uuid.uuid4(), tenant_id=tenant_a.id, client_id=client_a.id,
            guide_type="GPS", competence="2026-01",
            due_date=date(2026, 2, 15), amount=Decimal("800.00"),
            status=GuideStatus.DRAFT.value,
        )
        test_db.add(guide)
        await test_db.commit()

        http_b = _auth_client(app, test_db, user_b)
        resp = http_b.get(f"/api/v1/fiscal-guides/{guide.id}")
        app.dependency_overrides.clear()

        assert resp.status_code == 404
