"""Integration tests for RAG Fiscal endpoints, service, and isolation."""

import uuid
import pytest
from sqlalchemy import select

from app.models.rag_fiscal import RagDocument
from app.services import rag_service


class TestRagFiscalAPI:
    """Tests for the RAG Fiscal endpoints and similarity search service."""

    @pytest.mark.asyncio
    async def test_crud_rag_documents_success(self, client_with_auth_a, test_db):
        """Create, read, update, and delete RAG documents for tenant A."""
        client, user_a, _, _ = client_with_auth_a

        # 1. Create Document
        payload = {
            "title": "Procedimento de Parcelamento do Simples Nacional",
            "content": "Para realizar o parcelamento do Simples Nacional, o cliente deve acessar o Portal do Simples e solicitar a consolidação de débitos.",
            "source": "Manual Interno v2",
            "category": "procedimento"
        }
        response = client.post("/api/v1/rag/documents", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == payload["title"]
        assert data["content"] == payload["content"]
        assert data["category"] == payload["category"]
        assert "id" in data
        
        doc_id = data["id"]

        # Verify it exists in database
        stmt = select(RagDocument).where(RagDocument.id == uuid.UUID(doc_id))
        res = await test_db.execute(stmt)
        db_doc = res.scalar_one_or_none()
        assert db_doc is not None
        assert db_doc.title == payload["title"]

        # 2. List Documents
        response = client.get("/api/v1/rag/documents")
        assert response.status_code == 200
        docs_list = response.json()
        assert len(docs_list) == 1
        assert docs_list[0]["id"] == doc_id

        # List with filter
        response = client.get("/api/v1/rag/documents?category=faq")
        assert response.status_code == 200
        assert len(response.json()) == 0

        # 3. Update Document
        update_payload = {
            "title": "Procedimento de Parcelamento do Simples Nacional Atualizado",
            "content": "Procedimento atualizado: acesse o e-CAC ou o Portal do Simples.",
            "source": "Manual Interno v3",
            "category": "faq"
        }
        response = client.put(f"/api/v1/rag/documents/{doc_id}", json=update_payload)
        assert response.status_code == 200
        updated_data = response.json()
        assert updated_data["title"] == update_payload["title"]
        assert updated_data["content"] == update_payload["content"]
        assert updated_data["category"] == update_payload["category"]

        # 4. Delete Document
        response = client.delete(f"/api/v1/rag/documents/{doc_id}")
        assert response.status_code == 204

        # Verify it's gone
        res_deleted = await test_db.execute(stmt)
        assert res_deleted.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_similarity_search(self, client_with_auth_a, test_db):
        """Verify the similarity search retrieves matches based on keywords and scores confidence levels."""
        client, user_a, _, _ = client_with_auth_a

        # Add mock documents to base
        doc1 = RagDocument(
            id=uuid.uuid4(),
            tenant_id=user_a.tenant_id,
            title="Isenção de ICMS para Hortifrutigranjeiros",
            content="A saída de produtos hortifrutigranjeiros em estado natural é isenta de ICMS conforme o regulamento do estado.",
            source="Decreto Estadual 45.000",
            category="regulamento"
        )
        doc2 = RagDocument(
            id=uuid.uuid4(),
            tenant_id=user_a.tenant_id,
            title="Procedimento de Declaração de Faturamento DASN-SIMEI",
            content="O microempreendedor individual deve transmitir a DASN-SIMEI anualmente até o último dia de maio.",
            source="Manual do MEI",
            category="procedimento"
        )
        test_db.add_all([doc1, doc2])
        await test_db.commit()

        # Perform searches directly through service to test algorithm
        # Query matching "ICMS" and "Hortifrutigranjeiros"
        results_icms = await rag_service.search_knowledge_base(
            db=test_db,
            query="Como funciona a isenção de ICMS para hortifruti?",
            tenant_id=user_a.tenant_id
        )
        assert len(results_icms) > 0
        matched_doc, confidence = results_icms[0]
        assert matched_doc.id == doc1.id
        assert confidence >= 50.0

        # Query matching "mei" or "dasn-simei"
        results_mei = await rag_service.search_knowledge_base(
            db=test_db,
            query="Qual o prazo da declaração anual do MEI DASN?",
            tenant_id=user_a.tenant_id
        )
        assert len(results_mei) > 0
        matched_doc2, confidence2 = results_mei[0]
        assert matched_doc2.id == doc2.id
        assert confidence2 >= 50.0

        # Query with zero overlaps
        results_none = await rag_service.search_knowledge_base(
            db=test_db,
            query="Imposto sobre Grandes Fortunas IGF",
            tenant_id=user_a.tenant_id
        )
        assert len(results_none) == 0

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, client_with_auth_a, client_with_auth_b, test_db):
        """Ensure RAG documents are strictly isolated between tenants."""
        client_a, user_a, _, _ = client_with_auth_a
        client_b, user_b, _, _ = client_with_auth_b

        # Create a document in Tenant A
        doc_a = RagDocument(
            id=uuid.uuid4(),
            tenant_id=user_a.tenant_id,
            title="Procedimento Secreto do Tenant A",
            content="Este é um procedimento privado.",
            source="Manual A",
            category="procedimento"
        )
        test_db.add(doc_a)
        await test_db.commit()

        # Try listing with User B (should be empty)
        response_b_list = client_b.get("/api/v1/rag/documents")
        assert response_b_list.status_code == 200
        assert len(response_b_list.json()) == 0

        # Try retrieving or modifying Tenant A's document with User B (should fail with 404)
        response_b_put = client_b.put(
            f"/api/v1/rag/documents/{doc_a.id}",
            json={"title": "Modificacao Proibida", "content": "Conteudo invalido de teste", "source": "Hack", "category": "faq"}
        )
        assert response_b_put.status_code == 404

        # Try deleting Tenant A's document with User B (should fail with 404)
        response_b_delete = client_b.delete(f"/api/v1/rag/documents/{doc_a.id}")
        assert response_b_delete.status_code == 404
