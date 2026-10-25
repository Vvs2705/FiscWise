"""Upload de documento recusa tipo não aceito, arquivo vazio e arquivo grande (TEN-5)."""

import pytest

from app.api.v1.endpoints import operations
from app.core.config import settings


@pytest.fixture
def storage_on(monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://storage.invalid")
    monkeypatch.setattr(settings, "SUPABASE_SECRET_KEY", "x")
    monkeypatch.setattr(operations, "_DOC_UPLOAD_MAX_BYTES", 10)


@pytest.mark.parametrize(
    "name,data,expected",
    [
        ("virus.exe", b"MZ\x90", 415),
        ("vazio.pdf", b"", 400),
        ("grande.pdf", b"%PDF" + b"x" * 20, 413),
    ],
)
async def test_upload_recusa(client_with_auth_a, storage_on, name, data, expected):
    http, *_ = client_with_auth_a
    resp = http.post("/api/v1/documents/upload", files={"file": (name, data)})
    assert resp.status_code == expected, resp.text
