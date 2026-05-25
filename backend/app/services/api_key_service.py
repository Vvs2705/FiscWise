"""
API Key Service for FiscWise — Phase 12: Public API & Webhooks.

Handles secure API key generation, hashing, and verification.
Keys are stored only as SHA-256 hashes; the raw key is shown once on creation.
"""

import uuid
import hashlib
import secrets
import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_webhooks import TenantApiKey
from app.schemas.developer import ApiKeyCreate

logger = logging.getLogger(__name__)

# Key format: fw_live_<random 40 hex chars>
KEY_PREFIX_STATIC = "fw_live_"
KEY_RANDOM_BYTES = 24  # 48 hex chars


def _generate_raw_key() -> str:
    """Generate a cryptographically secure API key."""
    token = secrets.token_hex(KEY_RANDOM_BYTES)
    return f"{KEY_PREFIX_STATIC}{token}"


def _hash_key(raw_key: str) -> str:
    """Return SHA-256 hash of raw key (stored in DB)."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def _extract_prefix(raw_key: str) -> str:
    """Extract the first 16 chars as a human-readable prefix for display."""
    return raw_key[:16]


async def create_api_key(
    db: AsyncSession,
    payload: ApiKeyCreate,
    tenant_id: uuid.UUID,
) -> tuple[TenantApiKey, str]:
    """
    Create a new API key for a tenant.
    Returns (TenantApiKey ORM object, raw_key).
    The raw_key must be shown to the user once and is never stored again.
    """
    raw_key = _generate_raw_key()
    key_hash = _hash_key(raw_key)
    prefix = _extract_prefix(raw_key)

    api_key = TenantApiKey(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=payload.name,
        key_hash=key_hash,
        prefix=prefix,
        is_active=True,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    logger.info("API key created: tenant=%s name=%s prefix=%s", tenant_id, payload.name, prefix)
    return api_key, raw_key


async def list_api_keys(
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> List[TenantApiKey]:
    """List all API keys for a tenant (without raw key)."""
    stmt = select(TenantApiKey).where(TenantApiKey.tenant_id == tenant_id).order_by(TenantApiKey.created_at)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def revoke_api_key(
    db: AsyncSession,
    key_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> bool:
    """Soft-delete an API key by marking it as inactive."""
    stmt = select(TenantApiKey).where(
        (TenantApiKey.id == key_id) & (TenantApiKey.tenant_id == tenant_id)
    )
    result = await db.execute(stmt)
    key = result.scalar_one_or_none()
    if not key:
        return False
    key.is_active = False
    await db.commit()
    logger.info("API key revoked: tenant=%s key_id=%s", tenant_id, key_id)
    return True


async def verify_api_key(db: AsyncSession, raw_key: str) -> Optional[TenantApiKey]:
    """
    Verify a raw API key from an incoming request.
    Returns the TenantApiKey if valid and active, else None.
    Also updates last_used_at.
    """
    key_hash = _hash_key(raw_key)
    stmt = select(TenantApiKey).where(
        (TenantApiKey.key_hash == key_hash) & (TenantApiKey.is_active == True)  # noqa: E712
    )
    result = await db.execute(stmt)
    key = result.scalar_one_or_none()
    if key:
        key.last_used_at = datetime.now(timezone.utc)
        await db.commit()
    return key
