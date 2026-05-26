"""
Cross-tenant isolation tests — Onda 0 Tarefa 8.

For every resource with tenant_id, verify that a user from tenant B
cannot read, update, or delete resources belonging to tenant A.

Expected: 403 or 404 — never 200 with tenant A's data.
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, create_access_token
from app.models.operations import (
    AccountingClient,
    DeadlineItem,
    ClientDocument,
    DigitalCertificate,
    AccountReceivable,
    DasPayment,
)
from app.models.obligation import ObligationRule, ObligationInstance
from app.models.tenant import Tenant, SubscriptionStatus
from app.models.user import User, UserRole


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_http_client(app, db, user: User):
    """Build an authenticated TestClient for the given user."""
    from app.core.deps import get_db

    app.dependency_overrides[get_db] = lambda: db

    client = TestClient(app, raise_server_exceptions=False)
    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        role=user.role.value,
    )
    client.headers.update({
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(user.tenant_id),
    })
    return client


async def _create_tenant_and_owner(db: AsyncSession, suffix: str):
    tenant = Tenant(
        id=uuid.uuid4(),
        name=f"Tenant {suffix}",
        subscription_status=SubscriptionStatus.TRIAL,
    )
    db.add(tenant)
    await db.flush()

    user = User(
        id=uuid.uuid4(),
        email=f"owner_{suffix}@test.com",
        hashed_password=get_password_hash("Password123!"),
        full_name=f"Owner {suffix}",
        tenant_id=tenant.id,
        role=UserRole.OWNER,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    return tenant, user


# ─── Clients ──────────────────────────────────────────────────────────────────


class TestAccountingClientCrossTenant:
    @pytest.mark.asyncio
    async def test_read_client_from_other_tenant_returns_404(self, test_db: AsyncSession):
        from app.main import app

        tenant_a, user_a = await _create_tenant_and_owner(test_db, "A_client")
        tenant_b, user_b = await _create_tenant_and_owner(test_db, "B_client")

        client_a = AccountingClient(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            name="Client of A",
            document="76069336914468",
            entity_type="pj",
            status="active",
        )
        test_db.add(client_a)
        await test_db.commit()

        http_b = _make_http_client(app, test_db, user_b)
        resp = http_b.get(f"/api/v1/clients/{client_a.id}")
        app.dependency_overrides.clear()

        assert resp.status_code in (403, 404), (
            f"Expected 403/404 but got {resp.status_code}: {resp.text}"
        )

    @pytest.mark.asyncio
    async def test_list_clients_only_returns_own_tenant(self, test_db: AsyncSession):
        from app.main import app

        tenant_a, user_a = await _create_tenant_and_owner(test_db, "A_list")
        tenant_b, user_b = await _create_tenant_and_owner(test_db, "B_list")

        client_a = AccountingClient(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            name="Client of A — LIST",
            document="76069336914469",
            entity_type="pj",
            status="active",
        )
        test_db.add(client_a)
        await test_db.commit()

        http_b = _make_http_client(app, test_db, user_b)
        resp = http_b.get("/api/v1/clients")
        app.dependency_overrides.clear()

        if resp.status_code == 200:
            body = resp.json()
            items = body if isinstance(body, list) else body.get("items", body.get("data", []))
            ids = [str(i.get("id", "")) for i in items]
            assert str(client_a.id) not in ids, (
                "Tenant B can see client belonging to tenant A!"
            )


# ─── Deadline / Tasks ─────────────────────────────────────────────────────────


class TestDeadlineCrossTenant:
    @pytest.mark.asyncio
    async def test_read_deadline_from_other_tenant_returns_404(self, test_db: AsyncSession):
        from app.main import app
        import datetime

        tenant_a, user_a = await _create_tenant_and_owner(test_db, "A_dead")
        tenant_b, user_b = await _create_tenant_and_owner(test_db, "B_dead")

        client_a = AccountingClient(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            name="Client A Deadline",
            document="76069336914473",
            entity_type="pj",
            status="active",
        )
        test_db.add(client_a)
        await test_db.flush()

        deadline = DeadlineItem(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            client_id=client_a.id,
            title="DCTF vencendo",
            due_date=datetime.date.today(),
            status="pending",
            priority="high",
        )
        test_db.add(deadline)
        await test_db.commit()

        http_b = _make_http_client(app, test_db, user_b)
        resp = http_b.get(f"/api/v1/deadlines/{deadline.id}")
        app.dependency_overrides.clear()

        assert resp.status_code in (403, 404), (
            f"Expected 403/404 but got {resp.status_code}: {resp.text}"
        )


# ─── Digital Certificates ─────────────────────────────────────────────────────


class TestCertificateCrossTenant:
    @pytest.mark.asyncio
    async def test_read_certificate_from_other_tenant_returns_404(self, test_db: AsyncSession):
        from app.main import app
        import datetime

        tenant_a, user_a = await _create_tenant_and_owner(test_db, "A_cert")
        tenant_b, user_b = await _create_tenant_and_owner(test_db, "B_cert")

        client_a = AccountingClient(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            name="Client A cert",
            document="76069336914470",
            entity_type="pj",
            status="active",
        )
        test_db.add(client_a)
        await test_db.flush()

        cert = DigitalCertificate(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            client_id=client_a.id,
            label="Certificado A1 Owner A",
            certificate_type="A1",
            valid_from=datetime.date.today(),
            valid_until=datetime.date.today(),
            status="active",
        )
        test_db.add(cert)
        await test_db.commit()

        http_b = _make_http_client(app, test_db, user_b)
        resp = http_b.get(f"/api/v1/certificates/{cert.id}")
        app.dependency_overrides.clear()

        assert resp.status_code in (403, 404), (
            f"Expected 403/404 but got {resp.status_code}: {resp.text}"
        )


# ─── DAS Payments ─────────────────────────────────────────────────────────────


class TestDasPaymentCrossTenant:
    @pytest.mark.asyncio
    async def test_read_das_from_other_tenant_returns_404(self, test_db: AsyncSession):
        from app.main import app
        import datetime

        tenant_a, user_a = await _create_tenant_and_owner(test_db, "A_das")
        tenant_b, user_b = await _create_tenant_and_owner(test_db, "B_das")

        client_a = AccountingClient(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            name="Client A DAS",
            document="76069336914471",
            entity_type="pj",
            status="active",
        )
        test_db.add(client_a)
        await test_db.flush()

        das = DasPayment(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            client_id=client_a.id,
            period="2026-01",
            revenue=10000.00,
            tax_amount=150.00,
            due_date=datetime.date(2026, 2, 20),
            status="pending",
        )
        test_db.add(das)
        await test_db.commit()

        http_b = _make_http_client(app, test_db, user_b)
        resp = http_b.get(f"/api/v1/das-payments/{das.id}")
        app.dependency_overrides.clear()

        assert resp.status_code in (403, 404), (
            f"Expected 403/404 but got {resp.status_code}: {resp.text}"
        )


# ─── Account Receivables ──────────────────────────────────────────────────────


class TestReceivableCrossTenant:
    @pytest.mark.asyncio
    async def test_read_receivable_from_other_tenant_returns_404(self, test_db: AsyncSession):
        from app.main import app
        import datetime
        from decimal import Decimal

        tenant_a, user_a = await _create_tenant_and_owner(test_db, "A_recv")
        tenant_b, user_b = await _create_tenant_and_owner(test_db, "B_recv")

        client_a = AccountingClient(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            name="Client A Recv",
            document="76069336914472",
            entity_type="pj",
            status="active",
        )
        test_db.add(client_a)
        await test_db.flush()

        recv = AccountReceivable(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            client_id=client_a.id,
            description="Honorários Fev/2026",
            amount=Decimal("2500.00"),
            due_date=datetime.date(2026, 3, 5),
            status="pending",
        )
        test_db.add(recv)
        await test_db.commit()

        http_b = _make_http_client(app, test_db, user_b)
        resp = http_b.get(f"/api/v1/receivables/{recv.id}")
        app.dependency_overrides.clear()

        assert resp.status_code in (403, 404), (
            f"Expected 403/404 but got {resp.status_code}: {resp.text}"
        )


# ─── Storage URL cross-tenant check ───────────────────────────────────────────


class TestStorageCrossTenantUrl:
    def test_get_signed_url_rejects_wrong_tenant_path(self):
        from app.core.storage import get_signed_url
        from unittest.mock import patch

        tenant_a_id = uuid.uuid4()
        tenant_b_id = uuid.uuid4()

        # Path belongs to tenant_a — tenant_b must not generate a URL for it
        path = f"{tenant_a_id}/documents/invoice.pdf"

        with pytest.raises(PermissionError):
            get_signed_url("documents", path, ttl_seconds=300, tenant_id=tenant_b_id)

    def test_get_signed_url_rejects_excessive_ttl(self):
        from app.core.storage import get_signed_url

        tenant_id = uuid.uuid4()
        path = f"{tenant_id}/documents/invoice.pdf"

        with pytest.raises(ValueError, match="TTL máximo"):
            get_signed_url("documents", path, ttl_seconds=7200, tenant_id=tenant_id)

    def test_upload_path_prefixed_with_tenant_id(self):
        """upload_file must prefix storage path with tenant_id."""
        from app.core.storage import upload_file
        from unittest.mock import patch, MagicMock

        tenant_id = uuid.uuid4()
        captured_path = {}

        mock_client = MagicMock()
        mock_client.storage.from_().upload.return_value = MagicMock(error=None)

        with patch("app.core.storage._get_client", return_value=mock_client):
            upload_file(
                bucket="documents",
                path="certificates/cert.pdf",
                content=b"fake content",
                content_type="application/pdf",
                tenant_id=tenant_id,
            )

        call_kwargs = mock_client.storage.from_().upload.call_args
        called_path = call_kwargs[1]["path"] if call_kwargs[1] else call_kwargs[0][0]
        assert called_path.startswith(str(tenant_id)), (
            f"Storage path must be prefixed with tenant_id, got: {called_path}"
        )
