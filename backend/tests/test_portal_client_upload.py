"""Portal do cliente: o cliente vê o que o escritório pediu e envia o arquivo.

Cobre o fluxo de ponta a ponta do lado do cliente: pedido do checklist e
documento "missing" aparecem como pendentes, o upload resolve o pedido, e
nada disso alcança outro cliente do mesmo escritório.
"""

import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token, get_password_hash
from app.models.obligation import DocumentChecklistItem
from app.models.operations import AccountingClient, ClientDocument
from app.models.user import User, UserRole

pytestmark = pytest.mark.integration


@pytest.fixture
async def portal_upload(test_db, tenant_a, client_a):
    from app.core.deps import get_db
    from app.main import app

    user = User(
        id=uuid.uuid4(),
        email="cliente.upload@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Cliente Upload",
        tenant_id=tenant_a.id,
        role=UserRole.CLIENT,
        is_active=True,
    )
    test_db.add(user)
    client_a.portal_user_id = user.id

    neighbor = AccountingClient(
        id=uuid.uuid4(), tenant_id=tenant_a.id, name="Vizinho", document="11222333000181",
        entity_type="pj", status="active",
    )
    test_db.add(neighbor)

    missing = ClientDocument(
        id=uuid.uuid4(), tenant_id=tenant_a.id, client_id=client_a.id,
        name="Contrato social", status="missing",
    )
    item = DocumentChecklistItem(
        id=uuid.uuid4(), tenant_id=tenant_a.id, client_id=client_a.id,
        competence_month=date(2026, 11, 1), document_name="Extrato bancário", status="pending",
    )
    neighbor_doc = ClientDocument(
        id=uuid.uuid4(), tenant_id=tenant_a.id, client_id=neighbor.id,
        name="Doc do vizinho", status="missing",
    )
    test_db.add_all([missing, item, neighbor_doc])
    await test_db.commit()

    app.dependency_overrides[get_db] = lambda: test_db
    http = TestClient(app)
    token = create_access_token(user_id=str(user.id), tenant_id=str(tenant_a.id), role=UserRole.CLIENT.value)
    http.headers.update({"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant_a.id)})
    yield http, missing, item, neighbor_doc
    app.dependency_overrides.clear()


def _pdf():
    return {"file": ("extrato.pdf", b"%PDF-1.4 teste", "application/pdf")}


async def test_overview_lists_requests_as_pending(portal_upload):
    http, missing, item, _ = portal_upload
    docs = http.get("/api/v1/portal/my-overview").json()["documents"]
    by_id = {d["id"]: d for d in docs}
    assert by_id[str(item.id)]["kind"] == "checklist"
    assert by_id[str(item.id)]["status"] == "missing"
    assert by_id[str(item.id)]["can_upload"] is True
    assert by_id[str(missing.id)]["status"] == "missing"
    assert by_id[str(missing.id)]["can_upload"] is True


async def test_upload_fulfils_checklist_item(portal_upload, test_db):
    http, _, item, _ = portal_upload
    resp = http.post(
        "/api/v1/portal/my-documents", files=_pdf(),
        data={"request_id": str(item.id), "kind": "checklist"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "review"
    assert resp.json()["name"] == "Extrato bancário"

    await test_db.refresh(item)
    assert item.status == "received"
    docs = http.get("/api/v1/portal/my-overview").json()["documents"]
    assert str(item.id) not in {d["id"] for d in docs}
    uploaded = next(d for d in docs if d["id"] == resp.json()["id"])
    assert uploaded["status"] == "review"
    assert uploaded["file_url"]

    again = http.post(
        "/api/v1/portal/my-documents", files=_pdf(),
        data={"request_id": str(item.id), "kind": "checklist"},
    )
    assert again.status_code == 409


async def test_upload_fulfils_missing_document(portal_upload, test_db):
    http, missing, _, _ = portal_upload
    resp = http.post(
        "/api/v1/portal/my-documents", files=_pdf(),
        data={"request_id": str(missing.id), "kind": "document"},
    )
    assert resp.status_code == 201, resp.text
    await test_db.refresh(missing)
    assert missing.status == "review"
    assert missing.file_url and missing.file_url.startswith("documents/")


async def test_free_upload_creates_document(portal_upload):
    http, *_ = portal_upload
    resp = http.post("/api/v1/portal/my-documents", files=_pdf())
    assert resp.status_code == 201, resp.text
    assert resp.json()["name"] == "extrato.pdf"


async def test_cannot_upload_to_neighbor_request(portal_upload):
    http, _, _, neighbor_doc = portal_upload
    resp = http.post(
        "/api/v1/portal/my-documents", files=_pdf(),
        data={"request_id": str(neighbor_doc.id), "kind": "document"},
    )
    assert resp.status_code == 404


async def test_rejects_disallowed_extension(portal_upload):
    http, *_ = portal_upload
    resp = http.post(
        "/api/v1/portal/my-documents",
        files={"file": ("certificado.pfx", b"xx", "application/octet-stream")},
    )
    assert resp.status_code == 415


async def test_staff_cannot_use_client_upload(client_with_auth_a):
    http, *_ = client_with_auth_a
    resp = http.post("/api/v1/portal/my-documents", files=_pdf())
    assert resp.status_code == 403
