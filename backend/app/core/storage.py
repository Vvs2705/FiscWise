"""
Supabase Storage service — private buckets, signed URLs only.

All file access goes through this module.
Public URLs are never generated — every download uses a signed URL with TTL.
"""

import logging
from typing import Optional
from uuid import UUID

from app.core.config import settings

logger = logging.getLogger(__name__)

_MAX_TTL = 3600  # 1 hour hard cap
_DEFAULT_TTL = 300  # 5 minutes default


def _get_client():
    """Lazy Supabase client — only created when storage is actually used."""
    if not settings.SUPABASE_URL or not settings.SUPABASE_SECRET_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SECRET_KEY must be set to use storage."
        )
    try:
        from supabase import create_client
        return create_client(settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY)
    except ImportError:
        raise RuntimeError(
            "supabase package not installed. Add supabase to requirements.txt."
        )


def upload_file(
    bucket: str,
    path: str,
    content: bytes,
    content_type: str,
    tenant_id: UUID,
) -> str:
    """
    Upload bytes to a private Supabase bucket.

    Path convention: {tenant_id}/{category}/{filename}
    Buckets must be private — this is enforced at the Supabase dashboard level.

    Returns the storage path (not a URL — use get_signed_url to access).
    """
    # Prefix path with tenant_id to enforce per-tenant namespacing at the storage layer
    tenant_path = f"{tenant_id}/{path}"

    client = _get_client()
    response = client.storage.from_(bucket).upload(
        path=tenant_path,
        file=content,
        file_options={"content-type": content_type, "upsert": "false"},
    )

    if hasattr(response, "error") and response.error:
        raise RuntimeError(f"Storage upload failed: {response.error}")

    logger.info("storage.upload bucket=%s path=%s size=%d", bucket, tenant_path, len(content))
    return tenant_path


def get_signed_url(
    bucket: str,
    path: str,
    ttl_seconds: int = _DEFAULT_TTL,
    tenant_id: Optional[UUID] = None,
) -> str:
    """
    Generate a signed URL for a private file.

    TTL is capped at 3600s. Defaults to 300s.
    If tenant_id is provided, validates that path starts with that tenant's prefix.
    """
    if ttl_seconds > _MAX_TTL:
        raise ValueError(f"TTL máximo é {_MAX_TTL}s, recebido {ttl_seconds}s.")

    # Cross-tenant path check
    if tenant_id is not None and not path.startswith(str(tenant_id)):
        raise PermissionError(
            f"Path '{path}' não pertence ao tenant '{tenant_id}'."
        )

    client = _get_client()
    response = client.storage.from_(bucket).create_signed_url(path, ttl_seconds)

    if isinstance(response, dict):
        url = response.get("signedURL") or response.get("signedUrl")
    else:
        url = getattr(response, "signed_url", None)

    if not url:
        raise RuntimeError(f"Falha ao gerar URL assinada: {response}")

    return url


def delete_file(bucket: str, path: str, tenant_id: Optional[UUID] = None) -> None:
    """Delete a file from storage. Validates tenant ownership if tenant_id provided."""
    if tenant_id is not None and not path.startswith(str(tenant_id)):
        raise PermissionError(
            f"Path '{path}' não pertence ao tenant '{tenant_id}'."
        )

    client = _get_client()
    client.storage.from_(bucket).remove([path])
    logger.info("storage.delete bucket=%s path=%s", bucket, path)
