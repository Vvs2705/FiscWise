"""e-CAC domain service."""
import uuid
import hashlib
import logging
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ecac.models import FiscalSubject, EcacRequest, TaxStatusSnapshot
from app.domain.ecac.repository import get_subject, get_latest_tax_status
from app.domain.fiscal_core.events import ECAC_SYNC_REQUESTED, ECAC_TAX_STATUS_FETCHED
from app.services.audit import log_audit_event

logger = logging.getLogger(__name__)


def _get_provider(provider_slug: str = "mock"):
    from app.domain.ecac.providers.mock import MockEcacProvider
    providers = {"mock": MockEcacProvider(), "serpro_integra_contador": MockEcacProvider()}
    return providers.get(provider_slug, MockEcacProvider())


async def sync_tax_status(
    db: AsyncSession,
    subject_id: uuid.UUID,
    tenant_id: uuid.UUID,
    actor_user_id: uuid.UUID,
) -> TaxStatusSnapshot:
    subject = await get_subject(db, subject_id, tenant_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Fiscal subject not found.")

    idempotency_key = f"tax_status:{subject_id}:{datetime.now(timezone.utc).strftime('%Y%m%d%H')}"
    existing = await db.execute(
        __import__("sqlalchemy", fromlist=["select"]).select(EcacRequest).where(
            EcacRequest.idempotency_key == idempotency_key
        )
    )
    if existing.scalar_one_or_none():
        snap = await get_latest_tax_status(db, subject_id, tenant_id)
        if snap:
            return snap

    req = EcacRequest(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        subject_id=subject_id,
        provider="mock",
        operation="get_tax_status",
        idempotency_key=idempotency_key,
        status="pending",
    )
    db.add(req)
    await db.flush()

    provider = _get_provider()
    try:
        result = await provider.get_tax_status(subject)
        req.status = "success"
        req.response_hash = hashlib.sha256(str(result).encode()).hexdigest()

        snap = TaxStatusSnapshot(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            subject_id=subject_id,
            provider="mock",
            raw_payload=result,
            regularized=result.get("regularized"),
            pending_count=result.get("pending_count", 0),
            fetched_at=datetime.now(timezone.utc),
        )
        db.add(snap)
    except Exception as exc:
        req.status = "error"
        req.error_message = str(exc)
        await db.commit()
        raise HTTPException(status_code=502, detail=f"e-CAC sync failed: {exc}")

    await log_audit_event(
        db=db, tenant_id=tenant_id, action=ECAC_TAX_STATUS_FETCHED,
        entity_type="fiscal_subject", actor_user_id=actor_user_id, entity_id=subject_id,
    )
    await db.commit()
    await db.refresh(snap)
    return snap
