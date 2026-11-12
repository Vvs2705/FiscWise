"""Mídia do WhatsApp: download seguro (anti-SSRF, teto, allowlist) → storage → parser."""

import os

import httpx
import pytest
from sqlalchemy import select

from app.api.v1.endpoints import operations
from app.core.config import settings
from app.models.operations import ClientDocument
from app.services import whatsapp_service as wa

PDF = b"%PDF-1.7 comprovante"
URL = "https://media.provedor.example/files/abc"


@pytest.fixture
def env(monkeypatch, test_db):
    state: dict = {"uploaded": None, "parsed": None, "handler": None}

    class _Ctx:
        async def __aenter__(self):
            return test_db

        async def __aexit__(self, *a):
            return False

    async def _noop(*a, **k):
        return None

    async def fake_resolve(host):
        return {"intranet.example": ["10.0.0.5"]}.get(host, ["93.184.216.34"])

    async def fake_upload(bucket, path, data, content_type="application/octet-stream", **kw):
        state["uploaded"] = (bucket, path, data, content_type)
        return path

    async def fake_parse(document_id, file_path, file_name, tenant_id):
        with open(file_path, "rb") as f:
            state["parsed"] = (file_name, f.read())
        os.unlink(file_path)

    def handler(request):
        return state["handler"](request)

    monkeypatch.setattr("app.core.deps.get_sessionmaker", lambda: _Ctx)
    monkeypatch.setattr("app.core.deps._set_current_tenant_context", _noop)
    monkeypatch.setattr(wa, "_resolve_host", fake_resolve)
    monkeypatch.setattr(wa, "_MEDIA_TRANSPORT", httpx.MockTransport(handler))
    monkeypatch.setattr("app.core.storage.upload_bytes", fake_upload)
    monkeypatch.setattr(operations, "_parse_document_background", fake_parse)
    return state


async def _doc(test_db, client_a, name="Comprovante DAS.pdf"):
    doc = ClientDocument(tenant_id=client_a.tenant_id, client_id=client_a.id, name=name,
                         file_url=URL, parse_status="processing")
    test_db.add(doc)
    await test_db.commit()
    return doc


async def test_baixa_sobe_e_so_entao_parseia(env, test_db, client_a):
    env["handler"] = lambda req: httpx.Response(200, content=PDF, headers={"content-type": "application/pdf"})
    doc = await _doc(test_db, client_a)
    await wa.ingest_whatsapp_media(doc.id, URL, client_a.tenant_id)
    await test_db.refresh(doc)
    bucket, path, data, mime = env["uploaded"]
    assert (bucket, data, mime) == ("documents", PDF, "application/pdf")
    assert path.startswith(f"{client_a.tenant_id}/") and path.endswith(".pdf")
    assert doc.file_url == f"documents/{path}"
    assert env["parsed"] == ("Comprovante DAS.pdf", PDF)


async def test_tipo_real_corrige_extensao(env, test_db, client_a):
    xml = b'<?xml version="1.0"?><nfeProc xmlns="http://www.portalfiscal.inf.br/nfe"/>'
    env["handler"] = lambda req: httpx.Response(200, content=xml)
    doc = await _doc(test_db, client_a, name="Nota.pdf")
    await wa.ingest_whatsapp_media(doc.id, URL, client_a.tenant_id)
    await test_db.refresh(doc)
    assert doc.name == "Nota.xml" and env["parsed"][0] == "Nota.xml"


@pytest.mark.parametrize("url,motivo", [
    ("http://media.provedor.example/a", "https"),
    ("https://169.254.169.254/latest/meta-data", "privado"),
    ("https://localhost/a", "interno"),
    ("https://intranet.example/a", "privado"),
    ("https://user:pw@media.provedor.example/a", "inválida"),
    ("https://media.provedor.example:8443/a", "porta"),
])
async def test_ssrf_recusado(env, test_db, client_a, url, motivo):
    env["handler"] = lambda req: pytest.fail("não deveria ter feito a requisição")
    doc = await _doc(test_db, client_a)
    await wa.ingest_whatsapp_media(doc.id, url, client_a.tenant_id)
    await test_db.refresh(doc)
    assert doc.parse_status == "failed" and motivo in doc.parse_error
    assert env["uploaded"] is None and env["parsed"] is None


async def test_redirect_para_ip_interno_recusado(env, test_db, client_a):
    env["handler"] = lambda req: httpx.Response(302, headers={"location": "https://127.0.0.1/x"})
    doc = await _doc(test_db, client_a)
    await wa.ingest_whatsapp_media(doc.id, URL, client_a.tenant_id)
    await test_db.refresh(doc)
    assert doc.parse_status == "failed" and "privado" in doc.parse_error


async def test_maior_que_teto_e_tipo_proibido(env, test_db, client_a, monkeypatch):
    monkeypatch.setattr(wa, "MEDIA_MAX_BYTES", 10)
    env["handler"] = lambda req: httpx.Response(200, content=PDF)
    doc = await _doc(test_db, client_a)
    await wa.ingest_whatsapp_media(doc.id, URL, client_a.tenant_id)
    await test_db.refresh(doc)
    assert "20 MB" in doc.parse_error

    monkeypatch.setattr(wa, "MEDIA_MAX_BYTES", 20 * 1024 * 1024)
    env["handler"] = lambda req: httpx.Response(200, content=b"MZ\x90\x00\x03\x00\xff\xfe")
    doc2 = await _doc(test_db, client_a)
    await wa.ingest_whatsapp_media(doc2.id, URL, client_a.tenant_id)
    await test_db.refresh(doc2)
    assert doc2.parse_status == "failed" and "não permitido" in doc2.parse_error
    assert env["uploaded"] is None


async def test_timeout_vira_falha(env, test_db, client_a):
    def boom(req):
        raise httpx.ReadTimeout("lento", request=req)

    env["handler"] = boom
    doc = await _doc(test_db, client_a)
    await wa.ingest_whatsapp_media(doc.id, URL, client_a.tenant_id)
    await test_db.refresh(doc)
    assert doc.parse_status == "failed" and "ReadTimeout" in doc.parse_error


def _webhook(client, tenant_id):
    return client.post(f"/api/v1/whatsapp/webhooks/{tenant_id}", json={
        "sender_phone": "+5511888888888", "sender_name": "Cliente", "body": "Comprovante",
        "message_type": "document", "media_url": URL,
    })


async def test_webhook_sem_storage_registra_skipped(client, test_db, tenant_a, client_a, monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_URL", "")
    client_a.phone = "+5511888888888"
    await test_db.commit()
    assert _webhook(client, tenant_a.id).status_code == 200
    doc = (await test_db.execute(select(ClientDocument))).scalar_one()
    assert doc.parse_status == "skipped" and "storage não configurado" in doc.parse_error


async def test_webhook_com_storage_agenda_ingest(client, test_db, tenant_a, client_a, monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setattr(settings, "SUPABASE_SECRET_KEY", "x")
    called = {}

    async def fake_ingest(document_id, media_url, tenant_id):
        called.update(document_id=document_id, media_url=media_url, tenant_id=tenant_id)

    monkeypatch.setattr(wa, "ingest_whatsapp_media", fake_ingest)
    client_a.phone = "+5511888888888"
    await test_db.commit()
    assert _webhook(client, tenant_a.id).status_code == 200
    doc = (await test_db.execute(select(ClientDocument))).scalar_one()
    assert doc.parse_status == "processing"
    assert called == {"document_id": doc.id, "media_url": URL, "tenant_id": tenant_a.id}
