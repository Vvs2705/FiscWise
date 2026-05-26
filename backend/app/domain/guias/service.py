import uuid
import logging
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from fastapi import HTTPException, status

from app.domain.guias.models import TaxGuide
from app.domain.guias.repository import TaxGuideRepository
from app.domain.guias.schemas import TaxGuideCreate, TaxGuideUpdate
from app.core.file_validator import validate_file_mime
from app.core.storage import get_signed_url
from app.core.audit import audit_log

logger = logging.getLogger(__name__)

class TaxGuideService:
    def __init__(self, repo: TaxGuideRepository):
        self.repo = repo

    async def _check_overdue(self, guide: TaxGuide) -> bool:
        """Helper to mark guide as 'atrasada' if overdue and not paid."""
        if guide.status != "paga" and guide.vencimento < date.today():
            if guide.status != "atrasada":
                guide.status = "atrasada"
                await self.repo.update(guide)
                return True
        return False

    async def create_guide(self, payload: TaxGuideCreate, tenant_id: uuid.UUID) -> TaxGuide:
        guide = TaxGuide(
            tenant_id=tenant_id,
            client_id=payload.client_id,
            tipo=payload.tipo,
            competencia=payload.competencia,
            valor=payload.valor,
            vencimento=payload.vencimento,
            status="pendente"
        )
        await self._check_overdue(guide)
        return await self.repo.create(guide)

    async def get_guide(self, guide_id: uuid.UUID, tenant_id: uuid.UUID) -> TaxGuide:
        guide = await self.repo.get_by_id(guide_id, tenant_id)
        if not guide:
            raise HTTPException(status_code=404, detail="Tax guide not found")
        await self._check_overdue(guide)
        return guide

    async def list_guides(
        self,
        tenant_id: uuid.UUID,
        tipo: Optional[str] = None,
        status_filter: Optional[str] = None,
        competencia: Optional[date] = None,
        client_id: Optional[uuid.UUID] = None,
    ) -> List[TaxGuide]:
        guides = await self.repo.list_all(tenant_id, tipo, status_filter, competencia, client_id)
        for guide in guides:
            await self._check_overdue(guide)
        return guides

    async def list_pending_receipts(self, tenant_id: uuid.UUID) -> List[TaxGuide]:
        return await self.repo.list_pending_receipts(tenant_id)

    async def update_guide(self, guide_id: uuid.UUID, tenant_id: uuid.UUID, payload: TaxGuideUpdate) -> TaxGuide:
        guide = await self.get_guide(guide_id, tenant_id)
        
        for field, val in payload.model_dump(exclude_unset=True).items():
            setattr(guide, field, val)

        if payload.status == "paga":
            guide.paga_em = datetime.now(timezone.utc)
            await audit_log(
                action="guide.paid",
                tenant_id=str(tenant_id),
                details={"guide_id": str(guide_id), "tipo": guide.tipo, "valor": str(guide.valor)}
            )

        await self._check_overdue(guide)
        return await self.repo.update(guide)

    async def save_pdf_path(self, guide_id: uuid.UUID, tenant_id: uuid.UUID, file_name: str, content_type: str) -> TaxGuide:
        # Validate mime
        validate_file_mime(b"", allowed_mimes=["application/pdf"])
        
        guide = await self.get_guide(guide_id, tenant_id)
        path = f"guides/{guide_id}/guide_{file_name}"
        guide.pdf_storage_path = path
        if guide.status == "pendente":
            guide.status = "enviada"
            guide.enviada_em = datetime.now(timezone.utc)
            
        return await self.repo.update(guide)

    async def save_receipt_path(self, guide_id: uuid.UUID, tenant_id: uuid.UUID, file_name: str, content_type: str) -> TaxGuide:
        # Validate mime (pdf or image)
        validate_file_mime(b"", allowed_mimes=["application/pdf", "image/png", "image/jpeg"])
        
        guide = await self.get_guide(guide_id, tenant_id)
        path = f"receipts/{guide_id}/receipt_{file_name}"
        guide.comprovante_storage_path = path
        guide.status = "paga"
        guide.paga_em = datetime.now(timezone.utc)
        
        updated = await self.repo.update(guide)
        
        await audit_log(
            action="guide.receipt_uploaded",
            tenant_id=str(tenant_id),
            details={"guide_id": str(guide_id), "path": path}
        )
        return updated

    async def get_pdf_url(self, guide_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
        guide = await self.get_guide(guide_id, tenant_id)
        if not guide.pdf_storage_path:
            raise HTTPException(status_code=400, detail="No PDF uploaded for this guide")
        return await get_signed_url("guides", guide.pdf_storage_path, ttl=300)

    async def get_receipt_url(self, guide_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
        guide = await self.get_guide(guide_id, tenant_id)
        if not guide.comprovante_storage_path:
            raise HTTPException(status_code=400, detail="No receipt uploaded for this guide")
        return await get_signed_url("receipts", guide.comprovante_storage_path, ttl=300)
