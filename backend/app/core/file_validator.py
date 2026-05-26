"""
File validation utilities — MIME sniffing and size enforcement.

All upload endpoints must call validate_upload() before persisting any file.
This prevents disguised executables, oversized payloads, and unsupported types.
"""

import logging
from typing import Literal

from fastapi import HTTPException, UploadFile, status

logger = logging.getLogger(__name__)

# MIME types accepted anywhere in the system
ALLOWED_MIME_TYPES: frozenset[str] = frozenset({
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/xml",
    "text/xml",
    "application/zip",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/csv",
})

# Max sizes in bytes per upload category
MAX_FILE_SIZES: dict[str, int] = {
    "document":    25 * 1024 * 1024,   # 25 MB
    "certificate":  5 * 1024 * 1024,   # 5 MB
    "xml":         10 * 1024 * 1024,   # 10 MB
    "image":        5 * 1024 * 1024,   # 5 MB
    "default":     10 * 1024 * 1024,   # 10 MB fallback
}

UploadCategory = Literal["document", "certificate", "xml", "image", "default"]


def _detect_mime(content: bytes) -> str:
    """Return real MIME type by inspecting file magic bytes."""
    try:
        import magic  # python-magic
        return magic.from_buffer(content, mime=True)
    except ImportError:
        # python-magic not installed — fall back to a minimal manual check
        logger.warning(
            "python-magic not installed; MIME sniffing degraded. "
            "Add python-magic to requirements.txt."
        )
        return _fallback_mime(content)


def _fallback_mime(content: bytes) -> str:
    """Minimal magic-byte check when python-magic is unavailable."""
    if content[:4] == b"%PDF":
        return "application/pdf"
    if content[:2] in (b"\xff\xd8", b"\xff\xe0", b"\xff\xe1"):
        return "image/jpeg"
    if content[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if content[:2] == b"PK":
        return "application/zip"
    if content[:5] in (b"<?xml", b"<root", b"<nfse"):
        return "application/xml"
    return "application/octet-stream"


async def validate_upload(
    file: UploadFile,
    category: UploadCategory = "default",
) -> bytes:
    """
    Read, size-check, and MIME-sniff the upload.

    Returns the raw bytes so the caller does not need to re-read the file.
    Raises HTTP 413 for oversized files, HTTP 415 for disallowed types.
    """
    content = await file.read()
    await file.seek(0)

    # Size check
    max_bytes = MAX_FILE_SIZES.get(category, MAX_FILE_SIZES["default"])
    if len(content) > max_bytes:
        max_mb = max_bytes // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Arquivo excede o limite de {max_mb} MB para categoria '{category}'.",
        )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Arquivo vazio não é permitido.",
        )

    # MIME sniffing — use real magic bytes, not Content-Type header
    real_mime = _detect_mime(content)

    if real_mime not in ALLOWED_MIME_TYPES:
        logger.warning(
            "Upload rejeitado: real_mime=%s filename=%s size=%d",
            real_mime,
            file.filename,
            len(content),
        )
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Tipo de arquivo não permitido: {real_mime}.",
        )

    return content
