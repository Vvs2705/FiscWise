"""
Robust CRUD tests for operational entities (clients, deadlines, documents, certificates, receivables).

Tests focus on:
- Business logic validation (required fields, constraints)
- Tenant isolation (users can't access other tenants' data)
- Happy paths (valid CRUD operations)
- Error cases (404, 400, 409)

NOT tested: SQLAlchemy internals, FastAPI framework behavior, library implementations.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.operations import (
    AccountingClient,
    AccountReceivable,
    ClientDocument,
    DeadlineItem,
    DigitalCertificate,
)
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.operations import (
    AccountingClientCreate,
    AccountingClientUpdate,
    CertificateCreate,
    CertificateUpdate,
    DeadlineCreate,
    DeadlineUpdate,
    DocumentCreate,
    DocumentUpdate,
    ReceivableCreate,
    ReceivableUpdate,
)


# ============================================================================
# Clients CRUD Tests
# ============================================================================


class TestClientsCRUD:
    """AccountingClient CRUD operations and validation."""

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_create_client_valid(self, client_with_auth_a):
        """POST /api/v1/clients with valid data."""
        client, user_a, _, _ = client_with_auth_a

        payload = AccountingClientCreate(
            name="New Client",
            document="99.888.777/0001-55",
            entity_type="pj",
            tax_regime="lucro_real",
            email="new@client.com",
        )

        response = client.post("/api/v1/clients", json=payload.model_dump())

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Client"
        assert data["document"] == "99.888.777/0001-55"
        assert data["status"] == "active"
        assert data["tenant_id"] == str(user_a.tenant_id)

    @pytest.mark.asyncio
    async def test_create_client_missing_required_name(self, client_with_auth_a):
        """POST /api/v1/clients without required 'name' field."""
        client, _, _, _ = client_with_auth_a

        payload = {
            "document": "11.222.333/0001-81",
            "entity_type": "pj",
        }

        response = client.post("/api/v1/clients", json=payload)

        assert response.status_code == 422
        assert "name" in str(response.json())

    @pytest.mark.asyncio
    async def test_create_client_name_too_short(self, client_with_auth_a):
        """POST /api/v1/clients with name < 2 chars."""
        client, _, _, _ = client_with_auth_a

        payload = {
            "name": "X",
            "document": "11.222.333/0001-81",
            "entity_type": "pj",
        }

        response = client.post("/api/v1/clients", json=payload)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_client_duplicate_document(self, client_with_auth_a):
        """POST /api/v1/clients with document that already exists in tenant."""
        client, _, existing_client, _ = client_with_auth_a

        payload = AccountingClientCreate(
            name="Another Client",
            document=existing_client.document,
        )

        response = client.post("/api/v1/clients", json=payload.model_dump())

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_clients_for_tenant(self, client_with_auth_a):
        """GET /api/v1/clients lists clients of authenticated tenant only."""
        client, user_a, existing_client, test_db = client_with_auth_a

        response = client.get("/api/v1/clients")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["tenant_id"] == str(user_a.tenant_id)

    @pytest.mark.asyncio
    async def test_list_clients_filter_by_status(self, client_with_auth_a):
        """GET /api/v1/clients?status=inactive filters by status."""
        client, _, existing_client, _ = client_with_auth_a

        response = client.get("/api/v1/clients", params={"status": "inactive"})

        assert response.status_code == 200
        data = response.json()
        for item in data:
            assert item["status"] == "inactive"

    @pytest.mark.asyncio
    async def test_get_client_by_id(self, client_with_auth_a):
        """GET /api/v1/clients/{id} returns single client."""
        client, _, existing_client, _ = client_with_auth_a

        response = client.get(f"/api/v1/clients/{existing_client.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(existing_client.id)
        assert data["name"] == existing_client.name

    @pytest.mark.asyncio
    async def test_get_client_404_when_not_found(self, client_with_auth_a):
        """GET /api/v1/clients/{id} returns 404 if client doesn't exist."""
        client, _, _, _ = client_with_auth_a

        response = client.get(f"/api/v1/clients/{uuid.uuid4()}")

        assert response.status_code == 404
        assert response.json()["detail"] == "Client not found"

    @pytest.mark.asyncio
    async def test_update_client_valid(self, client_with_auth_a):
        """PATCH /api/v1/clients/{id} updates client fields."""
        client, _, existing_client, _ = client_with_auth_a

        payload = AccountingClientUpdate(
            name="Updated Name",
            email="updated@email.com",
        )

        response = client.patch(
            f"/api/v1/clients/{existing_client.id}",
            json=payload.model_dump(exclude_unset=True),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["email"] == "updated@email.com"

    @pytest.mark.asyncio
    async def test_update_client_partial(self, client_with_auth_a):
        """PATCH /api/v1/clients/{id} allows partial updates."""
        client, _, existing_client, _ = client_with_auth_a

        original_email = existing_client.email
        payload = AccountingClientUpdate(name="New Name Only")

        response = client.patch(
            f"/api/v1/clients/{existing_client.id}",
            json=payload.model_dump(exclude_unset=True),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name Only"
        assert data["email"] == original_email

    @pytest.mark.asyncio
    async def test_delete_client_soft_deletes(self, client_with_auth_a):
        """DELETE /api/v1/clients/{id} sets status=inactive (soft delete)."""
        client, _, existing_client, _ = client_with_auth_a

        response = client.delete(f"/api/v1/clients/{existing_client.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "inactive"

    @pytest.mark.asyncio
    async def test_tenant_isolation_client_list(self, test_db: AsyncSession):
        """User A cannot see clients from tenant B in list."""
        # Create two tenants
        ta = Tenant(id=uuid.uuid4(), name="A", plan_slug="pro")
        tb = Tenant(id=uuid.uuid4(), name="B", plan_slug="pro")
        test_db.add_all([ta, tb])
        await test_db.commit()

        # Create clients in each
        ca = AccountingClient(
            id=uuid.uuid4(),
            tenant_id=ta.id,
            name="Client A",
            entity_type="pj",
            status="active",
        )
        cb = AccountingClient(
            id=uuid.uuid4(),
            tenant_id=tb.id,
            name="Client B",
            entity_type="pj",
            status="active",
        )
        test_db.add_all([ca, cb])
        await test_db.commit()

        # Query as tenant A
        result_a = await test_db.execute(
            select(AccountingClient).where(AccountingClient.tenant_id == ta.id)
        )
        clients_a = result_a.scalars().all()

        assert len(clients_a) == 1
        assert clients_a[0].id == ca.id
        assert clients_a[0].tenant_id == ta.id


# ============================================================================
# Deadlines CRUD Tests
# ============================================================================


class TestDeadlinesCRUD:
    """DeadlineItem CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_deadline_valid(self, client_with_auth_a):
        """POST /api/v1/deadlines with valid data."""
        client, _, existing_client, _ = client_with_auth_a

        due = (date.today() + timedelta(days=30)).isoformat()
        payload = DeadlineCreate(
            client_id=existing_client.id,
            title="ECAC Filing",
            category="fiscal",
            due_date=due,
            status="pending",
            priority="high",
        )

        response = client.post("/api/v1/deadlines", json=payload.model_dump(mode="json"))

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "ECAC Filing"
        assert data["status"] == "pending"
        assert data["priority"] == "high"

    @pytest.mark.asyncio
    async def test_create_deadline_missing_required_title(self, client_with_auth_a):
        """POST /api/v1/deadlines without required 'title'."""
        client, _, existing_client, _ = client_with_auth_a

        payload = {
            "client_id": str(existing_client.id),
            "category": "fiscal",
            "due_date": date.today().isoformat(),
        }

        response = client.post("/api/v1/deadlines", json=payload)

        assert response.status_code == 422
        assert "title" in str(response.json())

    @pytest.mark.asyncio
    async def test_create_deadline_invalid_client(self, client_with_auth_a):
        """POST /api/v1/deadlines with non-existent client_id."""
        client, _, _, _ = client_with_auth_a

        payload = DeadlineCreate(
            client_id=uuid.uuid4(),
            title="Test Deadline",
            due_date=date.today() + timedelta(days=1),
        )

        response = client.post("/api/v1/deadlines", json=payload.model_dump(mode="json"))

        assert response.status_code == 404
        assert "Client not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_deadlines(self, client_with_auth_a):
        """GET /api/v1/deadlines lists all deadlines for tenant."""
        client, _, existing_client, _ = client_with_auth_a

        response = client.get("/api/v1/deadlines")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_deadlines_filter_by_client(self, client_with_auth_a):
        """GET /api/v1/deadlines?client_id=... filters by client."""
        client, _, existing_client, _ = client_with_auth_a

        response = client.get(
            "/api/v1/deadlines", params={"client_id": str(existing_client.id)}
        )

        assert response.status_code == 200
        data = response.json()
        for item in data:
            assert item["client_id"] == str(existing_client.id)

    @pytest.mark.asyncio
    async def test_update_deadline_to_completed(self, client_with_auth_a):
        """PATCH /api/v1/deadlines/{id} with status=completed sets completed_at."""
        client, _, existing_client, test_db = client_with_auth_a

        # Create a deadline first
        deadline = DeadlineItem(
            id=uuid.uuid4(),
            tenant_id=existing_client.tenant_id,
            client_id=existing_client.id,
            title="Test Deadline",
            category="fiscal",
            due_date=date.today() + timedelta(days=5),
            status="pending",
            priority="medium",
        )
        test_db.add(deadline)
        await test_db.commit()
        await test_db.refresh(deadline)

        payload = DeadlineUpdate(status="completed")

        response = client.patch(
            f"/api/v1/deadlines/{deadline.id}",
            json=payload.model_dump(exclude_unset=True),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["completed_at"] is not None


# ============================================================================
# Documents CRUD Tests
# ============================================================================


class TestDocumentsCRUD:
    """ClientDocument CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_document_valid(self, client_with_auth_a):
        """POST /api/v1/documents with valid data."""
        client, _, existing_client, _ = client_with_auth_a

        payload = DocumentCreate(
            client_id=existing_client.id,
            name="Contrato Social",
            document_type="contract",
            status="available",
            issued_at=date.today() - timedelta(days=365),
        )

        response = client.post("/api/v1/documents", json=payload.model_dump(mode="json"))

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Contrato Social"
        assert data["document_type"] == "contract"

    @pytest.mark.asyncio
    async def test_create_document_invalid_client(self, client_with_auth_a):
        """POST /api/v1/documents with non-existent client."""
        client, _, _, _ = client_with_auth_a

        payload = DocumentCreate(
            client_id=uuid.uuid4(),
            name="Some Document",
            document_type="other",
        )

        response = client.post("/api/v1/documents", json=payload.model_dump(mode="json"))

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_documents(self, client_with_auth_a):
        """GET /api/v1/documents lists documents for tenant."""
        client, _, _, _ = client_with_auth_a

        response = client.get("/api/v1/documents")

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_update_document_status(self, client_with_auth_a):
        """PATCH /api/v1/documents/{id} updates status."""
        client, _, existing_client, test_db = client_with_auth_a

        doc = ClientDocument(
            id=uuid.uuid4(),
            tenant_id=existing_client.tenant_id,
            client_id=existing_client.id,
            name="Test Doc",
            document_type="other",
            status="available",
        )
        test_db.add(doc)
        await test_db.commit()
        await test_db.refresh(doc)

        payload = DocumentUpdate(status="expired")

        response = client.patch(
            f"/api/v1/documents/{doc.id}",
            json=payload.model_dump(exclude_unset=True),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "expired"


# ============================================================================
# Certificates CRUD Tests
# ============================================================================


class TestCertificatesCRUD:
    """DigitalCertificate CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_certificate_valid(self, client_with_auth_a):
        """POST /api/v1/certificates with valid data."""
        client, _, existing_client, _ = client_with_auth_a

        valid_until = (date.today() + timedelta(days=365)).isoformat()
        payload = CertificateCreate(
            client_id=existing_client.id,
            label="Certificado A1 - João Silva",
            certificate_type="a1",
            valid_until=valid_until,
            status="valid",
        )

        response = client.post("/api/v1/certificates", json=payload.model_dump(mode="json"))

        assert response.status_code == 201
        data = response.json()
        assert data["label"] == "Certificado A1 - João Silva"
        assert data["certificate_type"] == "a1"

    @pytest.mark.asyncio
    async def test_create_certificate_missing_required_valid_until(self, client_with_auth_a):
        """POST /api/v1/certificates without required 'valid_until'."""
        client, _, existing_client, _ = client_with_auth_a

        payload = {
            "client_id": str(existing_client.id),
            "label": "Cert",
            "certificate_type": "a1",
        }

        response = client.post("/api/v1/certificates", json=payload)

        assert response.status_code == 422
        assert "valid_until" in str(response.json())

    @pytest.mark.asyncio
    async def test_list_certificates(self, client_with_auth_a):
        """GET /api/v1/certificates lists certificates for tenant."""
        client, _, _, _ = client_with_auth_a

        response = client.get("/api/v1/certificates")

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_update_certificate_status(self, client_with_auth_a):
        """PATCH /api/v1/certificates/{id} updates status."""
        client, _, existing_client, test_db = client_with_auth_a

        cert = DigitalCertificate(
            id=uuid.uuid4(),
            tenant_id=existing_client.tenant_id,
            client_id=existing_client.id,
            label="Test Cert",
            certificate_type="a1",
            valid_until=date.today() + timedelta(days=30),
            status="valid",
        )
        test_db.add(cert)
        await test_db.commit()
        await test_db.refresh(cert)

        payload = CertificateUpdate(status="expiring")

        response = client.patch(
            f"/api/v1/certificates/{cert.id}",
            json=payload.model_dump(exclude_unset=True),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "expiring"


# ============================================================================
# Receivables CRUD Tests
# ============================================================================


class TestReceivablesCRUD:
    """AccountReceivable CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_receivable_valid(self, client_with_auth_a):
        """POST /api/v1/receivables with valid data."""
        client, _, existing_client, _ = client_with_auth_a

        due = (date.today() + timedelta(days=30)).isoformat()
        payload = ReceivableCreate(
            client_id=existing_client.id,
            description="Honorários Contabilidade Jan",
            amount=Decimal("1500.00"),
            due_date=due,
            status="pending",
        )

        response = client.post("/api/v1/receivables", json=payload.model_dump(mode="json"))

        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "Honorários Contabilidade Jan"
        assert Decimal(data["amount"]) == Decimal("1500.00")
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_create_receivable_zero_amount(self, client_with_auth_a):
        """POST /api/v1/receivables with amount=0 (must be > 0)."""
        client, _, existing_client, _ = client_with_auth_a

        payload = {
            "client_id": str(existing_client.id),
            "description": "Invalid",
            "amount": "0.00",
            "due_date": (date.today() + timedelta(days=1)).isoformat(),
            "status": "pending",
        }

        response = client.post("/api/v1/receivables", json=payload)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_receivable_negative_amount(self, client_with_auth_a):
        """POST /api/v1/receivables with amount < 0."""
        client, _, existing_client, _ = client_with_auth_a

        payload = {
            "client_id": str(existing_client.id),
            "description": "Invalid",
            "amount": "-500.00",
            "due_date": (date.today() + timedelta(days=1)).isoformat(),
            "status": "pending",
        }

        response = client.post("/api/v1/receivables", json=payload)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_receivables(self, client_with_auth_a):
        """GET /api/v1/receivables lists receivables for tenant."""
        client, _, _, _ = client_with_auth_a

        response = client.get("/api/v1/receivables")

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_list_receivables_filter_by_status(self, client_with_auth_a):
        """GET /api/v1/receivables?status=paid filters by status."""
        client, _, _, _ = client_with_auth_a

        response = client.get("/api/v1/receivables", params={"status": "paid"})

        assert response.status_code == 200
        data = response.json()
        for item in data:
            assert item["status"] == "paid"

    @pytest.mark.asyncio
    async def test_update_receivable_to_paid(self, client_with_auth_a):
        """PATCH /api/v1/receivables/{id} with status=paid sets paid_at."""
        client, _, existing_client, test_db = client_with_auth_a

        rec = AccountReceivable(
            id=uuid.uuid4(),
            tenant_id=existing_client.tenant_id,
            client_id=existing_client.id,
            description="Test Receivable",
            amount=Decimal("1000.00"),
            due_date=date.today() - timedelta(days=5),
            status="pending",
        )
        test_db.add(rec)
        await test_db.commit()
        await test_db.refresh(rec)

        payload = ReceivableUpdate(status="paid")

        response = client.patch(
            f"/api/v1/receivables/{rec.id}",
            json=payload.model_dump(exclude_unset=True),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paid"
        assert data["paid_at"] is not None


# ============================================================================
# Tenant Isolation Tests (Critical Security)
# ============================================================================


class TestTenantIsolation:
    """Verify users cannot access data from other tenants."""

    @pytest.mark.asyncio
    async def test_user_a_cannot_get_client_from_tenant_b(self, test_db: AsyncSession):
        """User A cannot GET /api/v1/clients/{id_of_client_from_tenant_b}."""
        # Setup
        ta = Tenant(id=uuid.uuid4(), name="A", plan_slug="pro")
        tb = Tenant(id=uuid.uuid4(), name="B", plan_slug="pro")
        test_db.add_all([ta, tb])
        await test_db.commit()

        ua = User(
            id=uuid.uuid4(),
            email="a@a.com",
            hashed_password="hashed",
            full_name="User A",
            tenant_id=ta.id,
            is_active=True,
        )
        test_db.add(ua)
        await test_db.commit()

        cb = AccountingClient(
            id=uuid.uuid4(),
            tenant_id=tb.id,
            name="Client B",
            entity_type="pj",
            status="active",
        )
        test_db.add(cb)
        await test_db.commit()

        # Act: Query as tenant A, looking for client in tenant B
        result = await test_db.execute(
            select(AccountingClient).where(
                (AccountingClient.tenant_id == ta.id) & (AccountingClient.id == cb.id)
            )
        )
        found = result.scalar_one_or_none()

        # Assert: Should not find the client
        assert found is None

    @pytest.mark.asyncio
    async def test_tenant_isolation_prevents_cross_tenant_updates(self, test_db: AsyncSession):
        """Updating a deadline from another tenant fails (tenant_id check)."""
        ta = Tenant(id=uuid.uuid4(), name="A", plan_slug="pro")
        tb = Tenant(id=uuid.uuid4(), name="B", plan_slug="pro")
        test_db.add_all([ta, tb])
        await test_db.commit()

        ca = AccountingClient(
            id=uuid.uuid4(),
            tenant_id=ta.id,
            name="Client A",
            entity_type="pj",
            status="active",
        )
        cb = AccountingClient(
            id=uuid.uuid4(),
            tenant_id=tb.id,
            name="Client B",
            entity_type="pj",
            status="active",
        )
        test_db.add_all([ca, cb])
        await test_db.commit()

        deadline_b = DeadlineItem(
            id=uuid.uuid4(),
            tenant_id=tb.id,
            client_id=cb.id,
            title="Deadline B",
            category="fiscal",
            due_date=date.today() + timedelta(days=10),
            status="pending",
            priority="medium",
        )
        test_db.add(deadline_b)
        await test_db.commit()

        # Try to query deadline_b as tenant A
        result = await test_db.execute(
            select(DeadlineItem).where(
                (DeadlineItem.tenant_id == ta.id) & (DeadlineItem.id == deadline_b.id)
            )
        )
        found = result.scalar_one_or_none()

        assert found is None
