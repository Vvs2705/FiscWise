"""e-CAC repository."""
import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.ecac.models import FiscalSubject, EcacRequest, TaxStatusSnapshot


async def get_subject(db: AsyncSession, subject_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[FiscalSubject]:
    result = await db.execute(
        select(FiscalSubject).where(FiscalSubject.id == subject_id, FiscalSubject.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def list_subjects(db: AsyncSession, tenant_id: uuid.UUID) -> list[FiscalSubject]:
    result = await db.execute(
        select(FiscalSubject).where(FiscalSubject.tenant_id == tenant_id, FiscalSubject.active.is_(True))
    )
    return list(result.scalars().all())


async def get_latest_tax_status(db: AsyncSession, subject_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[TaxStatusSnapshot]:
    result = await db.execute(
        select(TaxStatusSnapshot)
        .where(TaxStatusSnapshot.subject_id == subject_id, TaxStatusSnapshot.tenant_id == tenant_id)
        .order_by(TaxStatusSnapshot.fetched_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
