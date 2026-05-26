"""e-CAC domain API endpoints."""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.domain.ecac import schemas, service
from app.domain.ecac.models import FiscalSubject
from app.domain.ecac.repository import list_subjects, get_subject
from app.domain.ecac.providers.mock import MockEcacProvider

router = APIRouter(prefix="/ecac", tags=["e-CAC / Integra Contador"])


@router.get("/subjects", response_model=list[schemas.FiscalSubjectOut])
async def list_subjects_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_subjects(db, current_user.tenant_id)


@router.post("/subjects", response_model=schemas.FiscalSubjectOut, status_code=201)
async def create_subject(
    body: schemas.FiscalSubjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    subject = FiscalSubject(id=uuid.uuid4(), tenant_id=current_user.tenant_id, **body.model_dump())
    db.add(subject)
    await db.commit()
    await db.refresh(subject)
    return subject


@router.get("/subjects/{subject_id}", response_model=schemas.FiscalSubjectOut)
async def get_subject_endpoint(
    subject_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    s = await get_subject(db, subject_id, current_user.tenant_id)
    if not s:
        raise HTTPException(status_code=404, detail="Subject not found.")
    return s


@router.post("/subjects/{subject_id}/sync")
async def sync_subject(
    subject_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    snap = await service.sync_tax_status(db, subject_id, current_user.tenant_id, current_user.id)
    return {"status": "synced", "snapshot_id": str(snap.id)}


@router.get("/subjects/{subject_id}/tax-status")
async def get_tax_status(
    subject_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    s = await get_subject(db, subject_id, current_user.tenant_id)
    if not s:
        raise HTTPException(status_code=404, detail="Subject not found.")
    provider = MockEcacProvider()
    return await provider.get_tax_status(s)


@router.get("/subjects/{subject_id}/mailbox")
async def get_mailbox(
    subject_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    s = await get_subject(db, subject_id, current_user.tenant_id)
    if not s:
        raise HTTPException(status_code=404, detail="Subject not found.")
    provider = MockEcacProvider()
    return await provider.get_mailbox_messages(s)


@router.get("/subjects/{subject_id}/guides")
async def get_guides(
    subject_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    s = await get_subject(db, subject_id, current_user.tenant_id)
    if not s:
        raise HTTPException(status_code=404, detail="Subject not found.")
    provider = MockEcacProvider()
    return await provider.get_pgdas(s, "2026-05")
