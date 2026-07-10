import uuid
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.domain.guias.service import TaxGuideService
from app.domain.guias.repository import TaxGuideRepository
from app.domain.guias.schemas import TaxGuideCreate, TaxGuideUpdate, TaxGuideResponse

router = APIRouter(prefix="/guias", tags=["Guias de Impostos"])

def _tenant_id(current_user: User) -> uuid.UUID:
    return current_user.tenant_id

@router.post("", response_model=TaxGuideResponse, status_code=status.HTTP_201_CREATED)
async def create_guide(
    payload: TaxGuideCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = TaxGuideRepository(db)
    service = TaxGuideService(repo)
    return await service.create_guide(payload, _tenant_id(current_user))

@router.get("", response_model=List[TaxGuideResponse])
async def list_guides(
    tipo: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    competencia: Optional[date] = Query(None),
    client_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = TaxGuideRepository(db)
    service = TaxGuideService(repo)
    return await service.list_guides(
        _tenant_id(current_user),
        tipo=tipo,
        status_filter=status_filter,
        competencia=competencia,
        client_id=client_id
    )

@router.get("/pending-receipt", response_model=List[TaxGuideResponse])
async def list_pending_receipts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = TaxGuideRepository(db)
    service = TaxGuideService(repo)
    return await service.list_pending_receipts(_tenant_id(current_user))

@router.get("/{id}", response_model=TaxGuideResponse)
async def get_guide(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = TaxGuideRepository(db)
    service = TaxGuideService(repo)
    return await service.get_guide(id, _tenant_id(current_user))

@router.put("/{id}", response_model=TaxGuideResponse)
async def update_guide(
    id: uuid.UUID,
    payload: TaxGuideUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = TaxGuideRepository(db)
    service = TaxGuideService(repo)
    return await service.update_guide(id, _tenant_id(current_user), payload)

@router.put("/{id}/mark-paid", response_model=TaxGuideResponse)
async def mark_paid(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = TaxGuideRepository(db)
    service = TaxGuideService(repo)
    payload = TaxGuideUpdate(status="paga")
    return await service.update_guide(id, _tenant_id(current_user), payload)

@router.post("/{id}/upload-pdf", response_model=TaxGuideResponse)
async def upload_pdf(
    id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = TaxGuideRepository(db)
    service = TaxGuideService(repo)
    file_bytes = await file.read()
    return await service.save_pdf_path(id, _tenant_id(current_user), file.filename, file.content_type, file_bytes)

@router.post("/{id}/upload-comprovante", response_model=TaxGuideResponse)
async def upload_comprovante(
    id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = TaxGuideRepository(db)
    service = TaxGuideService(repo)
    file_bytes = await file.read()
    return await service.save_receipt_path(id, _tenant_id(current_user), file.filename, file.content_type, file_bytes)

@router.get("/{id}/pdf")
async def get_pdf_url(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = TaxGuideRepository(db)
    service = TaxGuideService(repo)
    url = await service.get_pdf_url(id, _tenant_id(current_user))
    return {"url": url}

@router.get("/{id}/comprovante")
async def get_comprovante_url(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = TaxGuideRepository(db)
    service = TaxGuideService(repo)
    url = await service.get_receipt_url(id, _tenant_id(current_user))
    return {"url": url}
