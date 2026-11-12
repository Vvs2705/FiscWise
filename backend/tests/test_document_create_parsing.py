"""POST /documents agenda a classificação quando o arquivo está no nosso storage.

Antes só /clients/{id}/documents agendava o parser; documentos enviados pela
tela Documentos (upload + POST /documents) ficavam "Aguardando processamento"
para sempre.
"""

import os

import pytest

from app.api.v1.endpoints import operations
from app.core.config import settings

pytestmark = pytest.mark.integration

SUPA = "https://proj.supabase.co"


def _public_url(path: str) -> str:
    return f"{SUPA}/storage/v1/object/public/documents/{path}"


@pytest.fixture
def scheduled(monkeypatch):
    calls = []

    async def fake_bg(document_id, storage_path, file_name, tenant_id):
        calls.append((document_id, storage_path, file_name, tenant_id))

    monkeypatch.setattr(settings, "SUPABASE_URL", SUPA)
    monkeypatch.setattr(operations, "_download_and_parse_background", fake_bg)
    return calls


async def test_post_document_with_own_storage_file_schedules_parsing(client_with_auth_a, scheduled):
    http, user, client, _ = client_with_auth_a
    path = f"{user.tenant_id}/abc123.pdf"
    resp = http.post(
        "/api/v1/documents",
        json={"client_id": str(client.id), "name": "DAS maio.pdf", "file_url": _public_url(path)},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["parse_status"] == "processing"
    assert len(scheduled) == 1
    assert scheduled[0][1] == path
    assert str(scheduled[0][0]) == resp.json()["id"]


@pytest.mark.parametrize(
    "file_url",
    [
        None,
        "https://evil.example.com/arquivo.pdf",
        _public_url("00000000-0000-0000-0000-000000000000/de-outro-tenant.pdf"),
    ],
)
async def test_post_document_without_accessible_file_is_unavailable(client_with_auth_a, scheduled, file_url):
    http, _, client, _ = client_with_auth_a
    payload = {"client_id": str(client.id), "name": "Contrato social"}
    if file_url:
        payload["file_url"] = file_url
    resp = http.post("/api/v1/documents", json=payload)
    assert resp.status_code == 201, resp.text
    assert resp.json()["parse_status"] == "unavailable"
    assert scheduled == []


async def test_download_and_parse_reuses_parser(monkeypatch):
    import uuid

    seen = {}

    async def fake_download(bucket, path):
        seen["download"] = (bucket, path)
        return b"%PDF-1.7 teste"

    async def fake_parse(document_id, file_path, file_name, tenant_id):
        with open(file_path, "rb") as fh:
            seen["content"] = fh.read()
        seen["name"] = file_name
        os.unlink(file_path)

    monkeypatch.setattr("app.core.storage.download_bytes", fake_download)
    monkeypatch.setattr(operations, "_parse_document_background", fake_parse)

    tenant = uuid.uuid4()
    await operations._download_and_parse_background(uuid.uuid4(), f"{tenant}/x.pdf", "x.pdf", tenant)
    assert seen["download"] == ("documents", f"{tenant}/x.pdf")
    assert seen["content"] == b"%PDF-1.7 teste"
    assert seen["name"] == "x.pdf"


async def test_patch_document_marks_as_reviewed(client_with_auth_a, scheduled):
    http, _, client, _ = client_with_auth_a
    created = http.post(
        "/api/v1/documents",
        json={"client_id": str(client.id), "name": "Extrato", "status": "review"},
    ).json()
    resp = http.patch(f"/api/v1/documents/{created['id']}", json={"status": "available"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "available"
    # Repetir é idempotente
    again = http.patch(f"/api/v1/documents/{created['id']}", json={"status": "available"})
    assert again.status_code == 200 and again.json()["status"] == "available"
