"""Certificates domain API endpoints."""
import uuid
from typing import Optional
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.operations import DigitalCertificate  # canonical model in operations.py
from app.domain.certificates.models import CertificateUsageEvent
from app.domain.certificates.schemas import CertificateCreate, CertificatePatch, CertificateOut
from app.domain.fiscal_core.events import CERTIFICATE_ACCESSED, CERTIFICATE_UPLOADED
from app.services.audit import log_audit_event

router = APIRouter(prefix="/certificates", tags=["Certificados Digitais"])


@router.get("", response_model=list[CertificateOut])
async def list_certificates(
    expiring_days: Optional[int] = Query(None, description="Alert if expiring within N days"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(DigitalCertificate).where(DigitalCertificate.tenant_id == current_user.tenant_id)
    if expiring_days is not None:
        threshold = date.today() + timedelta(days=expiring_days)
        q = q.where(DigitalCertificate.valid_until <= threshold)
    result = await db.execute(q.order_by(DigitalCertificate.valid_until.asc()))
    return list(result.scalars().all())


@router.post("", response_model=CertificateOut, status_code=201)
async def create_certificate(
    body: CertificateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cert = DigitalCertificate(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        **body.model_dump(),
    )
    db.add(cert)
    await db.flush()
    await log_audit_event(
        db=db, tenant_id=current_user.tenant_id,
        action=CERTIFICATE_UPLOADED, entity_type="certificate",
        actor_user_id=current_user.id, entity_id=cert.id,
    )
    await db.commit()
    await db.refresh(cert)
    return cert


@router.get("/{cert_id}", response_model=CertificateOut)
async def get_certificate(
    cert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DigitalCertificate).where(
            DigitalCertificate.id == cert_id,
            DigitalCertificate.tenant_id == current_user.tenant_id,
        )
    )
    cert = result.scalar_one_or_none()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found.")

    usage = CertificateUsageEvent(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        certificate_id=cert_id,
        operation="read",
        actor_user_id=current_user.id,
    )
    db.add(usage)
    await log_audit_event(
        db=db, tenant_id=current_user.tenant_id,
        action=CERTIFICATE_ACCESSED, entity_type="certificate",
        actor_user_id=current_user.id, entity_id=cert_id,
    )
    await db.commit()
    return cert


@router.patch("/{cert_id}", response_model=CertificateOut)
async def patch_certificate(
    cert_id: uuid.UUID,
    body: CertificatePatch,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DigitalCertificate).where(
            DigitalCertificate.id == cert_id,
            DigitalCertificate.tenant_id == current_user.tenant_id,
        )
    )
    cert = result.scalar_one_or_none()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found.")
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(cert, field, val)
    await db.commit()
    await db.refresh(cert)
    return cert


@router.post("/{cert_id}/validate")
async def validate_certificate(
    cert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DigitalCertificate).where(
            DigitalCertificate.id == cert_id,
            DigitalCertificate.tenant_id == current_user.tenant_id,
        )
    )
    cert = result.scalar_one_or_none()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found.")
    expired = cert.valid_until and cert.valid_until < date.today()
    return {
        "certificate_id": str(cert_id),
        "status": cert.status,
        "valid_until": cert.valid_until,
        "expired": expired,
        "valid": not expired,
    }
