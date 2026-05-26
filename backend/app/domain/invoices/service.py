import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.invoices.models import Invoice, InvoiceIssuer, InvoiceEvent, InvoiceRejection
from app.domain.invoices.repository import InvoiceRepository
from app.domain.invoices.schemas import InvoiceIssuerCreate, InvoiceCreate
from app.domain.invoices.validators import validate_cpf_cnpj
from app.domain.invoices.events import dispatch_invoice_event
from app.domain.invoices.providers.base import NfseProvider
from app.core.storage import get_signed_url
from app.core.audit import audit_log

class InvoiceService:
    def __init__(self, repo: InvoiceRepository):
        self.repo = repo

    async def create_issuer(self, payload: InvoiceIssuerCreate, tenant_id: uuid.UUID) -> InvoiceIssuer:
        # Check if CNPJ already registered for this tenant
        existing = await self.repo.get_issuer_by_cnpj(payload.cnpj, tenant_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An issuer with this CNPJ already exists for this tenant."
            )
            
        issuer = InvoiceIssuer(
            tenant_id=tenant_id,
            client_id=payload.client_id,
            cnpj=payload.cnpj,
            inscricao_municipal=payload.inscricao_municipal,
            regime_tributario=payload.regime_tributario,
            municipio_ibge=payload.municipio_ibge,
            cod_servico_lc116=payload.cod_servico_lc116,
            aliquota_iss=payload.aliquota_iss,
            retencao_iss=payload.retencao_iss,
        )
        return await self.repo.create_issuer(issuer)

    async def list_issuers(self, tenant_id: uuid.UUID) -> List[InvoiceIssuer]:
        return await self.repo.list_issuers(tenant_id)

    async def create_invoice(self, payload: InvoiceCreate, tenant_id: uuid.UUID) -> Invoice:
        # 1. Validar CPF/CNPJ do tomador se fornecido
        if payload.tomador_cpf_cnpj and not validate_cpf_cnpj(payload.tomador_cpf_cnpj):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid CPF or CNPJ for tomador."
            )
        
        # 2. Valor do serviço deve ser > 0
        if payload.valor_servico <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Valor do serviço must be greater than zero."
            )

        # 3. Competência não pode ser futura (mês/ano)
        today = date.today()
        # Compare year and month
        if payload.competencia.year > today.year or (
            payload.competencia.year == today.year and payload.competencia.month > today.month
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Competência cannot be a future month."
            )

        # 4. Confirm issuer exists
        issuer = await self.repo.get_issuer_by_id(payload.issuer_id, tenant_id)
        if not issuer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice issuer not found."
            )

        invoice = Invoice(
            tenant_id=tenant_id,
            issuer_id=payload.issuer_id,
            client_id=payload.client_id,
            status="draft",
            competencia=payload.competencia,
            valor_servico=payload.valor_servico,
            valor_deducoes=payload.valor_deducoes,
            valor_iss=payload.valor_iss,
            descricao_servico=payload.descricao_servico,
            tomador_nome=payload.tomador_nome,
            tomador_cpf_cnpj=payload.tomador_cpf_cnpj,
            tomador_email=payload.tomador_email,
            tomador_municipio_ibge=payload.tomador_municipio_ibge,
            billing_charge_id=payload.billing_charge_id,
        )
        
        invoice = await self.repo.create_invoice(invoice)
        await dispatch_invoice_event(self.repo.db, invoice, "created", {"status": "draft"})
        return invoice

    async def get_invoice(self, invoice_id: uuid.UUID, tenant_id: uuid.UUID) -> Invoice:
        invoice = await self.repo.get_by_id(invoice_id, tenant_id)
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found."
            )
        return invoice

    async def list_invoices(
        self,
        tenant_id: uuid.UUID,
        status_filter: Optional[str] = None,
        client_id: Optional[uuid.UUID] = None,
        competencia: Optional[date] = None,
    ) -> List[Invoice]:
        return await self.repo.list_all(tenant_id, status_filter, client_id, competencia)

    async def queue_emission(self, invoice_id: uuid.UUID, tenant_id: uuid.UUID) -> Invoice:
        """Validates transitions and queues invoice for emission."""
        invoice = await self.get_invoice(invoice_id, tenant_id)
        
        # Valid state transitions: draft -> validating -> queued, or rejected -> draft -> validating -> queued
        if invoice.status not in ("draft", "rejected"):
            raise ValueError(f"Cannot emit invoice from status: {invoice.status}")

        invoice.status = "validating"
        await self.repo.update_invoice(invoice)
        await dispatch_invoice_event(self.repo.db, invoice, "validating")

        invoice.status = "queued"
        await self.repo.update_invoice(invoice)
        await dispatch_invoice_event(self.repo.db, invoice, "queued")
        
        return invoice

    async def process_emission_sync(self, invoice_id: uuid.UUID, tenant_id: uuid.UUID, provider: NfseProvider) -> Invoice:
        """Helper for executing emission synchronously (primarily for tests)."""
        invoice = await self.get_invoice(invoice_id, tenant_id)
        
        if invoice.status != "queued":
            raise ValueError(f"Cannot process emission from status: {invoice.status}")
            
        invoice.status = "processing"
        await self.repo.update_invoice(invoice)
        await dispatch_invoice_event(self.repo.db, invoice, "processing")

        # Call provider
        invoice_data = {
            "valor_servico": float(invoice.valor_servico),
            "descricao_servico": invoice.descricao_servico,
            "numero": invoice.numero or "000000",
            "cnpj_emissor": invoice.issuer.cnpj,
        }
        
        try:
            res = await provider.emit(invoice_data)
            status_res = res.get("status")

            if status_res == "issued":
                # Success
                invoice.status = "issued"
                invoice.numero = res.get("numero")
                invoice.provider_protocol = res.get("protocol")
                invoice.provider_response = res.get("raw")
                invoice.xml_content = res.get("xml")
                invoice.pdf_storage_path = f"invoices/{invoice.id}/pdf_{invoice.id}.pdf"
                invoice.xml_storage_path = f"invoices/{invoice.id}/xml_{invoice.id}.xml"
                invoice.issued_at = datetime.now(timezone.utc)
                await self.repo.update_invoice(invoice)
                
                await dispatch_invoice_event(self.repo.db, invoice, "issued", {"protocol": res.get("protocol")})
                await audit_log(
                    action="invoice.issued",
                    tenant_id=str(tenant_id),
                    details={"invoice_id": str(invoice.id), "numero": invoice.numero}
                )

            elif status_res == "rejected":
                # Rejected
                invoice.status = "rejected"
                await self.repo.update_invoice(invoice)
                
                rejection = InvoiceRejection(
                    invoice_id=invoice.id,
                    tenant_id=tenant_id,
                    codigo_rejeicao=res.get("codigo_rejeicao"),
                    descricao=res.get("descricao") or "Rejected by municipal server",
                    raw_response=res.get("raw")
                )
                await self.repo.create_rejection(rejection)
                
                await dispatch_invoice_event(self.repo.db, invoice, "rejected", {
                    "code": res.get("codigo_rejeicao"),
                    "description": res.get("descricao")
                })
                
            else:
                # Failed
                invoice.status = "failed"
                await self.repo.update_invoice(invoice)
                
                rejection = InvoiceRejection(
                    invoice_id=invoice.id,
                    tenant_id=tenant_id,
                    codigo_rejeicao="FAILED",
                    descricao=res.get("descricao") or "Emission failed during provider transmission",
                    raw_response=res.get("raw")
                )
                await self.repo.create_rejection(rejection)
                await dispatch_invoice_event(self.repo.db, invoice, "failed", {"error": res.get("descricao")})

        except Exception as e:
            invoice.status = "failed"
            await self.repo.update_invoice(invoice)
            
            rejection = InvoiceRejection(
                invoice_id=invoice.id,
                tenant_id=tenant_id,
                codigo_rejeicao="EXCEPTION",
                descricao=f"Emission failed with exception: {str(e)}",
                raw_response={"exception": str(e)}
            )
            await self.repo.create_rejection(rejection)
            await dispatch_invoice_event(self.repo.db, invoice, "failed", {"exception": str(e)})

        return invoice

    async def cancel_invoice(self, invoice_id: uuid.UUID, tenant_id: uuid.UUID, reason: str, provider: NfseProvider) -> Invoice:
        invoice = await self.get_invoice(invoice_id, tenant_id)

        if invoice.status != "issued":
            raise ValueError(f"Cannot cancel invoice from status: {invoice.status}")

        invoice.status = "cancel_requested"
        await self.repo.update_invoice(invoice)
        await dispatch_invoice_event(self.repo.db, invoice, "cancel_requested", {"reason": reason})

        # Call provider cancel
        try:
            res = await provider.cancel(invoice.provider_protocol, reason)
            
            if res.get("status") == "cancelled":
                invoice.status = "cancelled"
                invoice.cancelled_at = datetime.now(timezone.utc)
                await self.repo.update_invoice(invoice)
                await dispatch_invoice_event(self.repo.db, invoice, "cancelled")
            else:
                # If cancel failed, return to issued status but record failure event
                invoice.status = "issued"
                await self.repo.update_invoice(invoice)
                await dispatch_invoice_event(self.repo.db, invoice, "cancel_failed", {"error": "Provider rejected cancellation"})
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Provider rejected cancellation request."
                )

        except Exception as e:
            invoice.status = "issued"
            await self.repo.update_invoice(invoice)
            await dispatch_invoice_event(self.repo.db, invoice, "cancel_failed", {"exception": str(e)})
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cancellation failed with error: {str(e)}"
            )

        return invoice

    async def get_pdf_signed_url(self, invoice_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
        invoice = await self.get_invoice(invoice_id, tenant_id)
        if invoice.status != "issued" or not invoice.pdf_storage_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PDF not available for this invoice."
            )
        return await get_signed_url("invoices", invoice.pdf_storage_path, ttl=300)

    async def get_xml_signed_url(self, invoice_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
        invoice = await self.get_invoice(invoice_id, tenant_id)
        if invoice.status != "issued" or not invoice.xml_storage_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="XML not available for this invoice."
            )
        return await get_signed_url("invoices", invoice.xml_storage_path, ttl=300)
