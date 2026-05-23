"""Integration tests for company partners/shareholders CRUD and isolation."""

import uuid
from decimal import Decimal
from datetime import date
import pytest
from app.models.operations import CompanyPartner
from app.schemas.partners import PartnerCreate, PartnerUpdate


class TestCompanyPartners:
    """Tests for the company partners management endpoints."""

    @pytest.mark.asyncio
    async def test_create_partner_success(self, client_with_auth_a):
        """POST /api/v1/clients/{client_id}/partners creates a new partner successfully."""
        client, user_a, client_a, _ = client_with_auth_a

        payload = PartnerCreate(
            name="Partner One",
            cpf="111.222.333-44",
            participation_percentage=Decimal("50.00"),
            entry_date=date(2026, 1, 1),
            status="active",
            notes="Founder partner",
        )

        response = client.post(
            f"/api/v1/clients/{client_a.id}/partners",
            json=payload.model_dump(mode="json"),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Partner One"
        assert data["cpf"] == "111.222.333-44"
        assert Decimal(data["participation_percentage"]) == Decimal("50.00")
        assert data["status"] == "active"
        assert data["client_id"] == str(client_a.id)
        assert data["tenant_id"] == str(user_a.tenant_id)

    @pytest.mark.asyncio
    async def test_create_partner_not_found_client(self, client_with_auth_a):
        """POST /api/v1/clients/{client_id}/partners returns 404 if client doesn't exist."""
        client, _, _, _ = client_with_auth_a
        random_uuid = uuid.uuid4()

        payload = PartnerCreate(
            name="Partner One",
            cpf="111.222.333-44",
            participation_percentage=Decimal("50.00"),
        )

        response = client.post(
            f"/api/v1/clients/{random_uuid}/partners",
            json=payload.model_dump(mode="json"),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_partners(self, client_with_auth_a, test_db):
        """GET /api/v1/clients/{client_id}/partners returns partners for client."""
        client, user_a, client_a, _ = client_with_auth_a

        partner = CompanyPartner(
            tenant_id=user_a.tenant_id,
            client_id=client_a.id,
            name="Existing Partner",
            cpf="222.333.444-55",
            participation_percentage=Decimal("25.50"),
            entry_date=date(2026, 2, 2),
            status="active",
        )
        test_db.add(partner)
        await test_db.commit()

        response = client.get(f"/api/v1/clients/{client_a.id}/partners")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Existing Partner"

    @pytest.mark.asyncio
    async def test_update_partner(self, client_with_auth_a, test_db):
        """PUT /api/v1/clients/{client_id}/partners/{partner_id} updates partner info."""
        client, user_a, client_a, _ = client_with_auth_a

        partner = CompanyPartner(
            tenant_id=user_a.tenant_id,
            client_id=client_a.id,
            name="Old Name",
            cpf="222.333.444-55",
            participation_percentage=Decimal("25.50"),
            status="active",
        )
        test_db.add(partner)
        await test_db.commit()
        await test_db.refresh(partner)

        update_payload = PartnerUpdate(
            name="New Name",
            participation_percentage=Decimal("30.00"),
        )

        response = client.put(
            f"/api/v1/clients/{client_a.id}/partners/{partner.id}",
            json=update_payload.model_dump(exclude_unset=True, mode="json"),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert Decimal(data["participation_percentage"]) == Decimal("30.00")

    @pytest.mark.asyncio
    async def test_delete_partner(self, client_with_auth_a, test_db):
        """DELETE /api/v1/clients/{client_id}/partners/{partner_id} deletes partner."""
        client, user_a, client_a, _ = client_with_auth_a

        partner = CompanyPartner(
            tenant_id=user_a.tenant_id,
            client_id=client_a.id,
            name="To Delete",
            cpf="333.444.555-66",
            participation_percentage=Decimal("100.00"),
            status="active",
        )
        test_db.add(partner)
        await test_db.commit()
        await test_db.refresh(partner)

        response = client.delete(f"/api/v1/clients/{client_a.id}/partners/{partner.id}")
        assert response.status_code == 204

        # Verify not found
        response = client.get(f"/api/v1/clients/{client_a.id}/partners/{partner.id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_tenant_isolation_prevents_access(self, client_with_auth_b, client_with_auth_a, test_db):
        """User B cannot view or edit User A's client partners."""
        # Setup partner under User A's tenant/client
        _, user_a, client_a, _ = client_with_auth_a

        partner = CompanyPartner(
            tenant_id=user_a.tenant_id,
            client_id=client_a.id,
            name="Tenant A Partner",
            cpf="999.888.777-66",
            participation_percentage=Decimal("10.00"),
            status="active",
        )
        test_db.add(partner)
        await test_db.commit()
        await test_db.refresh(partner)

        # Access via Client B (authenticated as User B)
        client_b_http, _, _, _ = client_with_auth_b

        # List should fail with 404 since client_a doesn't belong to tenant B
        response = client_b_http.get(f"/api/v1/clients/{client_a.id}/partners")
        assert response.status_code == 404

        # Direct detail get should return 404
        response = client_b_http.get(f"/api/v1/clients/{client_a.id}/partners/{partner.id}")
        assert response.status_code == 404

        # Edit should return 404
        update_payload = PartnerUpdate(name="Hacked Name")
        response = client_b_http.put(
            f"/api/v1/clients/{client_a.id}/partners/{partner.id}",
            json=update_payload.model_dump(exclude_unset=True, mode="json"),
        )
        assert response.status_code == 404

        # Delete should return 404
        response = client_b_http.delete(f"/api/v1/clients/{client_a.id}/partners/{partner.id}")
        assert response.status_code == 404
