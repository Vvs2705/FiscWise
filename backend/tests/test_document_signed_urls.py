"""Documentos: banco guarda referência do bucket privado, API devolve URL assinada (LGPD)."""

import pytest

from app.api.v1.endpoints import operations
from app.core import document_links
from app.core.config import settings
from app.models.operations import ClientDocument

BASE = "https://proj.supabase.co"


@pytest.fixture
def fake_storage(monkeypatch):
    calls: dict = {"signed": []}
    monkeypatch.setattr(settings, "SUPABASE_URL", BASE)
    monkeypatch.setattr(settings, "SUPABASE_SECRET_KEY", "x")

    async def fake_upload(bucket, path, data, content_type="application/octet-stream", **kw):
        calls["uploaded"] = f"{bucket}/{path}"
        return path

    async def fake_sign_many(bucket, paths, ttl=300):
        calls["signed"].append((bucket, list(paths), ttl))
        return {p: f"{BASE}/storage/v1/object/sign/{bucket}/{p}?token=t" for p in paths}

    async def fake_sign(bucket, path, ttl=300):
        return f"{BASE}/storage/v1/object/sign/{bucket}/{path}?token=t"

    monkeypatch.setattr("app.core.storage.upload_bytes", fake_upload)
    monkeypatch.setattr("app.core.storage.get_signed_urls", fake_sign_many)
    monkeypatch.setattr("app.core.storage.get_signed_url", fake_sign)
    monkeypatch.setattr(operations, "_parse_document_background", lambda *a, **k: None)
    return calls


async def test_upload_devolve_referencia_e_leitura_assina(client_with_auth_a, fake_storage):
    http, _, client_a, _ = client_with_auth_a
    up = http.post("/api/v1/documents/upload", files={"file": ("nota.pdf", b"%PDF-1.7 x")})
    assert up.status_code == 200, up.text
    body = up.json()
    assert "/object/public/" not in body["url"]
    assert body["url"] == f"documents/{body['path']}"
    assert body["path"].startswith(f"{client_a.tenant_id}/")
    assert "token=" in body["signed_url"]

    created = http.post(
        "/api/v1/documents",
        json={"client_id": str(client_a.id), "name": "Nota", "file_url": body["url"]},
    )
    assert created.status_code == 201, created.text
    assert created.json()["file_url"].startswith(f"{BASE}/storage/v1/object/sign/documents/")

    listed = http.get("/api/v1/documents").json()
    assert listed[0]["file_url"].endswith("?token=t")
    one = http.get(f"/api/v1/documents/{listed[0]['id']}").json()
    assert "/object/sign/" in one["file_url"]
    by_client = http.get(f"/api/v1/clients/{client_a.id}/documents").json()
    assert "/object/sign/" in by_client[0]["file_url"]
    # TTL curto e um lote só por listagem
    assert all(ttl == document_links.SIGNED_URL_TTL for _, _, ttl in fake_storage["signed"])


async def test_upload_por_cliente_grava_referencia(client_with_auth_a, fake_storage, test_db):
    http, _, client_a, _ = client_with_auth_a
    resp = http.post(
        f"/api/v1/clients/{client_a.id}/documents?document_type=contract",
        files={"file": ("contrato.pdf", b"%PDF-1.7 teste")},
    )
    assert resp.status_code == 200, resp.text
    assert "/object/sign/" in resp.json()["file_url"]
    doc = await test_db.get(ClientDocument, __import__("uuid").UUID(resp.json()["id"]))
    await test_db.refresh(doc)
    assert doc.file_url.startswith(f"documents/{client_a.tenant_id}/")


async def test_compat_e_bloqueios(client_with_auth_a, fake_storage, test_db):
    http, user_a, client_a, _ = client_with_auth_a
    t = client_a.tenant_id
    urls = {
        "antiga_publica": f"{BASE}/storage/v1/object/public/documents/{t}/old.pdf",
        "externa": "https://lookaside.example.net/media/123",
        "outro_tenant": "documents/00000000-0000-0000-0000-000000000000/x.pdf",
        "travessia": f"documents/{t}/../outro/x.pdf",
        "script": "javascript:alert(1)",
    }
    for name, url in urls.items():
        test_db.add(ClientDocument(tenant_id=t, client_id=client_a.id, name=name, file_url=url))
    await test_db.commit()

    got = {d["name"]: d["file_url"] for d in http.get("/api/v1/documents").json()}
    assert got["antiga_publica"] == f"{BASE}/storage/v1/object/sign/documents/{t}/old.pdf?token=t"
    assert got["externa"] == urls["externa"]
    assert got["outro_tenant"] is None
    assert got["travessia"] is None
    assert got["script"] is None


async def test_storage_fora_nao_derruba_lista(client_with_auth_a, fake_storage, test_db, monkeypatch):
    http, _, client_a, _ = client_with_auth_a

    async def boom(*a, **k):
        raise RuntimeError("supabase fora")

    monkeypatch.setattr("app.core.storage.get_signed_urls", boom)
    test_db.add(ClientDocument(
        tenant_id=client_a.tenant_id, client_id=client_a.id, name="Doc",
        file_url=f"documents/{client_a.tenant_id}/a.pdf",
    ))
    await test_db.commit()
    resp = http.get("/api/v1/documents")
    assert resp.status_code == 200
    assert resp.json()[0]["file_url"] is None


async def test_company_documents_assinadas(client_with_auth_a, fake_storage):
    http, _, client_a, _ = client_with_auth_a
    ref = f"documents/{client_a.tenant_id}/cnpj.pdf"
    resp = http.post(
        f"/api/v1/clients/{client_a.id}/company-documents",
        json={"document_type": "cnpj", "file_url": ref},
    )
    assert resp.status_code == 201, resp.text
    assert "/object/sign/" in resp.json()["file_url"]
    listed = http.get(f"/api/v1/clients/{client_a.id}/company-documents").json()
    assert "/object/sign/" in listed[0]["file_url"]


async def test_get_signed_urls_lote(monkeypatch):
    import httpx

    from app.core import storage

    monkeypatch.setattr(settings, "SUPABASE_URL", BASE)
    monkeypatch.setattr(settings, "SUPABASE_SECRET_KEY", "x")
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = request.read()
        return httpx.Response(200, json=[
            {"path": "t/a.pdf", "signedURL": "/object/sign/documents/t/a.pdf?token=1", "error": None},
            {"path": "t/b.pdf", "signedURL": None, "error": "Either the object does not exist"},
        ])

    real = storage.request_with_retry

    async def with_mock_client(method, url, **kw):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await real(method, url, client=c, **kw)

    monkeypatch.setattr(storage, "request_with_retry", with_mock_client)
    out = await storage.get_signed_urls("documents", ["t/a.pdf", "t/b.pdf", "t/a.pdf"], ttl=60)
    assert seen["url"] == f"{BASE}/storage/v1/object/sign/documents"
    assert b'"expiresIn":60' in seen["body"].replace(b" ", b"")
    assert out == {"t/a.pdf": f"{BASE}/storage/v1/object/sign/documents/t/a.pdf?token=1"}
