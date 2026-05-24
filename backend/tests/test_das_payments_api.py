import uuid
from decimal import Decimal
from datetime import date
import pytest

from app.models.operations import DasPayment
from app.schemas.das import DasPaymentCreate, DasPaymentUpdate


class TestDasPayments:
    """Integration tests for monthly DAS tax payments endpoints."""

    @pytest.mark.asyncio
    async def test_create_das_payment_success(self, client_with_auth_a):
        """POST /api/v1/das creates a new DAS payment record successfully."""
        client, user_a, client_a, _ = client_with_auth_a

        payload = DasPaymentCreate(
            client_id=client_a.id,
            period="2026-01",
            revenue=Decimal("150000.00"),
            tax_amount=Decimal("9000.00"),
            due_date=date(2026, 2, 20),
            status="pending",
            notes="January Simples Nacional guide",
        )

        response = client.post(
            "/api/v1/das",
            json=payload.model_dump(mode="json"),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["period"] == "2026-01"
        assert Decimal(data["revenue"]) == Decimal("150000.00")
        assert Decimal(data["tax_amount"]) == Decimal("9000.00")
        assert data["status"] == "pending"
        assert data["client_id"] == str(client_a.id)
        assert data["client_name"] == client_a.name

    @pytest.mark.asyncio
    async def test_create_das_payment_invalid_client(self, client_with_auth_a):
        """POST /api/v1/das returns 404 for invalid client ID."""
        client, _, _, _ = client_with_auth_a
        random_uuid = uuid.uuid4()

        payload = DasPaymentCreate(
            client_id=random_uuid,
            period="2026-01",
            revenue=Decimal("10000.00"),
            tax_amount=Decimal("600.00"),
            due_date=date(2026, 2, 20),
            status="pending",
        )

        response = client.post(
            "/api/v1/das",
            json=payload.model_dump(mode="json"),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_das_payments(self, client_with_auth_a, test_db):
        """GET /api/v1/das lists all DAS records filtered by client and year."""
        client, user_a, client_a, _ = client_with_auth_a

        # Pre-populate some DAS entries
        das1 = DasPayment(
            tenant_id=user_a.tenant_id,
            client_id=client_a.id,
            period="2026-01",
            revenue=Decimal("10000.00"),
            tax_amount=Decimal("600.00"),
            due_date=date(2026, 2, 20),
            status="paid",
        )
        das2 = DasPayment(
            tenant_id=user_a.tenant_id,
            client_id=client_a.id,
            period="2026-02",
            revenue=Decimal("12000.00"),
            tax_amount=Decimal("720.00"),
            due_date=date(2026, 3, 20),
            status="pending",
        )
        test_db.add(das1)
        test_db.add(das2)
        await test_db.commit()

        # List all
        response = client.get(f"/api/v1/das?client_id={client_a.id}&year=2026")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["period"] == "2026-01"
        assert data[1]["period"] == "2026-02"

    @pytest.mark.asyncio
    async def test_update_das_payment(self, client_with_auth_a, test_db):
        """PUT /api/v1/das/{das_id} updates a DAS record."""
        client, user_a, client_a, _ = client_with_auth_a

        das = DasPayment(
            tenant_id=user_a.tenant_id,
            client_id=client_a.id,
            period="2026-01",
            revenue=Decimal("10000.00"),
            tax_amount=Decimal("600.00"),
            due_date=date(2026, 2, 20),
            status="pending",
        )
        test_db.add(das)
        await test_db.commit()
        await test_db.refresh(das)

        payload = DasPaymentUpdate(
            revenue=Decimal("12000.00"),
            tax_amount=Decimal("720.00"),
            status="paid",
        )

        response = client.put(
            f"/api/v1/das/{das.id}",
            json=payload.model_dump(mode="json"),
        )
        assert response.status_code == 200
        data = response.json()
        assert Decimal(data["revenue"]) == Decimal("12000.00")
        assert Decimal(data["tax_amount"]) == Decimal("720.00")
        assert data["status"] == "paid"
        assert data["paid_at"] is not None

    @pytest.mark.asyncio
    async def test_mark_das_as_paid(self, client_with_auth_a, test_db):
        """PATCH /api/v1/das/{das_id}/pay marks DAS as paid."""
        client, user_a, client_a, _ = client_with_auth_a

        das = DasPayment(
            tenant_id=user_a.tenant_id,
            client_id=client_a.id,
            period="2026-01",
            revenue=Decimal("10000.00"),
            tax_amount=Decimal("600.00"),
            due_date=date(2026, 2, 20),
            status="pending",
        )
        test_db.add(das)
        await test_db.commit()
        await test_db.refresh(das)

        response = client.patch(f"/api/v1/das/{das.id}/pay")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paid"
        assert data["paid_at"] is not None

    @pytest.mark.asyncio
    async def test_delete_das_payment(self, client_with_auth_a, test_db):
        """DELETE /api/v1/das/{das_id} deletes a DAS record."""
        client, user_a, client_a, _ = client_with_auth_a

        das = DasPayment(
            tenant_id=user_a.tenant_id,
            client_id=client_a.id,
            period="2026-01",
            revenue=Decimal("10000.00"),
            tax_amount=Decimal("600.00"),
            due_date=date(2026, 2, 20),
            status="pending",
        )
        test_db.add(das)
        await test_db.commit()
        await test_db.refresh(das)

        response = client.delete(f"/api/v1/das/{das.id}")
        assert response.status_code == 204

        # Verify deletion
        check = await test_db.get(DasPayment, das.id)
        assert check is None

    @pytest.mark.asyncio
    async def test_tenant_isolation_on_das(self, client_with_auth_a, client_with_auth_b, test_db):
        """User B cannot view or modify DAS payments of Tenant A."""
        client_a, user_a, cl_a, _ = client_with_auth_a
        client_b, user_b, cl_b, _ = client_with_auth_b

        # Create DAS under Tenant A
        das_a = DasPayment(
            tenant_id=user_a.tenant_id,
            client_id=cl_a.id,
            period="2026-01",
            revenue=Decimal("10000.00"),
            tax_amount=Decimal("600.00"),
            due_date=date(2026, 2, 20),
            status="pending",
        )
        test_db.add(das_a)
        await test_db.commit()
        await test_db.refresh(das_a)

        # User B tries to update User A's DAS entry -> 404
        payload = DasPaymentUpdate(status="paid")
        response = client_b.put(
            f"/api/v1/das/{das_a.id}",
            json=payload.model_dump(mode="json"),
        )
        assert response.status_code == 404

        # User B tries to quick pay User A's DAS -> 404
        response = client_b.patch(f"/api/v1/das/{das_a.id}/pay")
        assert response.status_code == 404

        # User B tries to delete User A's DAS -> 404
        response = client_b.delete(f"/api/v1/das/{das_a.id}")
        assert response.status_code == 404
