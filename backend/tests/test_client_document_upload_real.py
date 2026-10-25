"""Upload por cliente não grava mais URL de exemplo nem aceita tipo perigoso (TEN-6)."""

from app.api.v1.endpoints import operations


async def test_upload_por_cliente(client_with_auth_a, monkeypatch):
    http, _, client_a, _ = client_with_auth_a
    saved = {}

    async def fake_upload(
        bucket, path, data, content_type="application/octet-stream", **kw
    ):
        saved["path"], saved["size"] = f"{bucket}/{path}", len(data)
        return path

    monkeypatch.setattr("app.core.storage.upload_bytes", fake_upload)
    monkeypatch.setattr(operations, "_parse_document_background", lambda *a, **k: None)
    url = f"/api/v1/clients/{client_a.id}/documents?document_type=contract"

    assert http.post(url, files={"file": ("x.exe", b"MZ\x90")}).status_code == 415
    resp = http.post(url, files={"file": ("contrato.pdf", b"%PDF-1.7 teste")})
    assert resp.status_code == 200, resp.text
    assert "example.com" not in resp.json()["file_url"]
    assert (
        saved["path"].startswith(f"documents/{client_a.tenant_id}/")
        and saved["size"] > 0
    )
