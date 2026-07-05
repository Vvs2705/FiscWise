import re
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.domain.monthly_closing.models import MonthlyClosing
from app.domain.monthly_closing.repository import MonthlyClosingRepository
from app.domain.monthly_closing.service import MonthlyClosingService
from app.domain.monthly_closing.dossier_pdf import render_dossier_pdf
from app.domain.monthly_closing.schemas import (
    ChecklistItemUpdate,
    MonthlyClosingResponse,
    GenerateClosingsResult,
    DossierResult,
)

router = APIRouter(prefix="/monthly-closing", tags=["Monthly Closing"])

_COMPETENCE_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _service(db: AsyncSession) -> MonthlyClosingService:
    return MonthlyClosingService(MonthlyClosingRepository(db))


def _to_response(closing: MonthlyClosing) -> MonthlyClosingResponse:
    response = MonthlyClosingResponse.model_validate(closing)
    if closing.client is not None:
        response.client_name = closing.client.name
        response.client_cnpj = closing.client.document
    return response


def _validate_competence(competence: str) -> str:
    if not _COMPETENCE_RE.match(competence):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="competence must be in YYYY-MM format",
        )
    return competence


@router.get("", response_model=List[MonthlyClosingResponse])
async def list_closings(
    competence: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if competence:
        _validate_competence(competence)
    closings = await _service(db).list_closings(current_user.tenant_id, competence)
    return [_to_response(c) for c in closings]


@router.get("/{closing_id}", response_model=MonthlyClosingResponse)
async def get_closing(
    closing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    closing = await _service(db).get_closing(closing_id, current_user.tenant_id)
    if not closing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Closing not found")
    return _to_response(closing)


@router.post("/generate", response_model=GenerateClosingsResult)
async def generate_closings(
    competence: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create the monthly closing pipeline for every active client (idempotent)."""
    _validate_competence(competence)
    return await _service(db).generate_for_competence(current_user.tenant_id, competence)


@router.patch("/{closing_id}/checklist/{item_id}", response_model=MonthlyClosingResponse)
async def update_checklist_item(
    closing_id: uuid.UUID,
    item_id: str,
    payload: ChecklistItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        closing = await _service(db).update_checklist_item(
            closing_id,
            item_id,
            current_user.tenant_id,
            status=payload.status,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if not closing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Closing not found")
    return _to_response(closing)


@router.post("/{closing_id}/dossier", response_model=DossierResult)
async def generate_dossier(
    closing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    closing = await _service(db).generate_dossier(closing_id, current_user.tenant_id)
    if not closing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Closing not found")
    return DossierResult(
        url=f"/api/v1/monthly-closing/{closing.id}/dossier.pdf",
        generated_at=closing.dossier_generated_at,
    )


@router.get("/{closing_id}/dossier.pdf")
async def download_dossier_pdf(
    closing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream the dossier PDF rendered from the current closing state."""
    closing = await _service(db).get_closing(closing_id, current_user.tenant_id)
    if not closing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Closing not found")

    client_name = closing.client.name if closing.client else None
    client_cnpj = closing.client.document if closing.client else None
    pdf_bytes = render_dossier_pdf(closing, client_name=client_name, client_cnpj=client_cnpj)

    filename = f"dossie-{(client_name or 'cliente').replace(' ', '-').lower()}-{closing.competence}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
