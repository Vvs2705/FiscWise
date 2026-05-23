"""Integration tests for company official documents CRUD and isolation."""

import uuid
from datetime import date, datetime, timedelta, timezone
import pytest
from app.models.operations import CompanyDocument, CompanyDocumentType
from app.schemas.company_documents import CompanyDocumentCreate, CompanyDocumentUpdate


class TestCompanyDocuments:
    """Tests for the company documents management endpoints."""

    @pytest.mark.asyncio
    async def test_create_company_document_success(self, client_with_auth_a):
        """POST /api/v1/clients/{client_id}/company-documents creates a new document successfully."""
        client, user_a, client_a, _ = client_with_auth_a

        payload = CompanyDocumentCreate(
            document_type="cnpj",
            file_url="https://supabase.com/storage/v1/object/public/documents/cnpj.pdf",
            expiration_date=date(2027, 12, 31),
            status="valid",
            notes="CNPJ active copy",
        )

        response = client.post(
            f"/api/v1/clients/{client_a.id}/company-documents",
            json=payload.model_dump(mode="json"),
        )

        assert response.status_code == 201
        data = response.json()
        assert data["document_type"] == "cnpj"
        assert data["file_url"] == "https://supabase.com/storage/v1/object/public/documents/cnpj.pdf"
        assert data["status"] == "valid"
        assert data["client_id"] == str(client_a.id)
        assert data["tenant_id"] == str(user_a.tenant_id)

    @pytest.mark.asyncio
    async def test_create_company_document_invalid_client(self, client_with_auth_a):
        """POST /api/v1/clients/{client_id}/company-documents returns 404 for invalid client."""
        client, _, _, _ = client_with_auth_a
        random_uuid = uuid.uuid4()

        payload = CompanyDocumentCreate(
            document_type="cnpj",
            file_url="https://supabase.com/storage/v1/object/public/documents/cnpj.pdf",
        )

        response = client.post(
            f"/api/v1/clients/{random_uuid}/company-documents",
            json=payload.model_dump(mode="json"),
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_company_documents(self, client_with_auth_a, test_db):
        """GET /api/v1/clients/{client_id}/company-documents lists documents."""
        client, user_a, client_a, _ = client_with_auth_a

        doc = CompanyDocument(
            tenant_id=user_a.tenant_id,
            client_id=client_a.id,
            document_type=CompanyDocumentType.CNPJ,
            file_url="https://supabase.com/storage/v1/object/public/documents/cnpj.pdf",
            status="valid",
        )
        test_db.add(doc)
        await test_db.commit()

        response = client.get(f"/api/v1/clients/{client_a.id}/company-documents")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["document_type"] == "cnpj"

    @pytest.mark.asyncio
    async def test_get_expiring_documents(self, client_with_auth_a, test_db):
        """GET /api/v1/clients/{client_id}/company-documents/expiring-soon alerts about expiring documents."""
        client, user_a, client_a, _ = client_with_auth_a

        # Document expiring in 10 days (should trigger alert with threshold 30 days)
        exp_date = date.today() + timedelta(days=10)
        doc_expiring = CompanyDocument(
            tenant_id=user_a.tenant_id,
            client_id=client_a.id,
            document_type=CompanyDocumentType.ALVARA_FUNCIONAMENTO,
            file_url="https://supabase.com/storage/v1/object/public/documents/alvara.pdf",
            expiration_date=exp_date,
            status="valid",
        )

        # Document expiring in 60 days (should NOT trigger alert with threshold 30 days)
        far_exp_date = date.today() + timedelta(days=60)
        doc_far = CompanyDocument(
            tenant_id=user_a.tenant_id,
            client_id=client_a.id,
            document_type=CompanyDocumentType.LICENCA_SANITARIA,
            file_url="https://supabase.com/storage/v1/object/public/documents/licenca.pdf",
            expiration_date=far_exp_date,
            status="valid",
        )

        test_db.add_all([doc_expiring, doc_far])
        await test_db.commit()

        response = client.get(
            f"/api/v1/clients/{client_a.id}/company-documents/expiring-soon",
            params={"days_threshold": 30},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["document_type"] == "alvara_funcionamento"

    @pytest.mark.asyncio
    async def test_update_company_document(self, client_with_auth_a, test_db):
        """PUT /api/v1/clients/{client_id}/company-documents/{doc_id} updates document metadata."""
        client, user_a, client_a, _ = client_with_auth_a

        doc = CompanyDocument(
            tenant_id=user_a.tenant_id,
            client_id=client_a.id,
            document_type=CompanyDocumentType.CNPJ,
            file_url="https://supabase.com/storage/v1/object/public/documents/cnpj.pdf",
            status="valid",
        )
        test_db.add(doc)
        await test_db.commit()
        await test_db.refresh(doc)

        payload = CompanyDocumentUpdate(
            status="expired",
            notes="Marked as expired",
        )

        response = client.put(
            f"/api/v1/clients/{client_a.id}/company-documents/{doc.id}",
            json=payload.model_dump(exclude_unset=True, mode="json"),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "expired"
        assert data["notes"] == "Marked as expired"

    @pytest.mark.asyncio
    async def test_delete_company_document(self, client_with_auth_a, test_db):
        """DELETE /api/v1/clients/{client_id}/company-documents/{doc_id} deletes document."""
        client, user_a, client_a, _ = client_with_auth_a

        doc = CompanyDocument(
            tenant_id=user_a.tenant_id,
            client_id=client_a.id,
            document_type=CompanyDocumentType.CNPJ,
            file_url="https://supabase.com/storage/v1/object/public/documents/cnpj.pdf",
            status="valid",
        )
        test_db.add(doc)
        await test_db.commit()
        await test_db.refresh(doc)

        response = client.delete(f"/api/v1/clients/{client_a.id}/company-documents/{doc.id}")
        assert response.status_code == 204

        # Verify not found
        response = client.get(f"/api/v1/clients/{client_a.id}/company-documents/{doc.id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_tenant_isolation_prevents_access(self, client_with_auth_b, client_with_auth_a, test_db):
        """User B cannot view or edit User A's client documents."""
        # Setup document under User A's tenant/client
        _, user_a, client_a, _ = client_with_auth_a

        doc = CompanyDocument(
            tenant_id=user_a.tenant_id,
            client_id=client_a.id,
            document_type=CompanyDocumentType.CNPJ,
            file_url="https://supabase.com/storage/v1/object/public/documents/cnpj.pdf",
            status="valid",
        )
        test_db.add(doc)
        await test_db.commit()
        await test_db.refresh(doc)

        # Access via Client B (authenticated as User B)
        client_b_http, _, _, _ = client_with_auth_b

        # List should fail with 404
        response = client_b_http.get(f"/api/v1/clients/{client_a.id}/company-documents")
        assert response.status_code == 404

        # Detail get should return 404
        response = client_b_http.get(f"/api/v1/clients/{client_a.id}/company-documents/{doc.id}")
        assert response.status_code == 404

        # Edit should return 404
        payload = CompanyDocumentUpdate(status="expired")
        response = client_b_http.put(
            f"/api/v1/clients/{client_a.id}/company-documents/{doc.id}",
            json=payload.model_dump(exclude_unset=True, mode="json"),
        )
        assert response.status_code == 404

        # Delete should return 404
        response = client_b_http.delete(f"/api/v1/clients/{client_a.id}/company-documents/{doc.id}")
        assert response.status_code == 404
