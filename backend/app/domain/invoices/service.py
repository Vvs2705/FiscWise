import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.tenant_guard import ensure_client_in_tenant
from app.domain.invoices.models import Invoice, InvoiceIssuer, InvoiceEvent, InvoiceRejection
from app.domain.invoices.repository import InvoiceRepository
from app.domain.invoices.schemas import InvoiceIssuerCreate, InvoiceCreate
from app.domain.invoices.validators import validate_cpf_cnpj
from app.domain.invoices.events import dispatch_invoice_event
from app.domain.invoices.providers.base import NfseProvider, TransientEmissionError
from app.core.audit import audit_log


def emissao_exige_certificado() -> bool:
    """Provider real (não mock): a emissão exige emissor liberado e certificado."""
    from app.core.config import settings
    from app.core.integration_mode import normalize_provider

    return normalize_provider(settings.NFSE_PROVIDER) != "mock"


async def _material_do_emissor(db, issuer, finalidade: str):
    """Certificado configurado para o emissor (None quando o provider é mock)."""
    if not emissao_exige_certificado():
        return None
    from app.domain.certificados.cofre import CertificadoIndisponivel, obter_material

    if issuer.certificado_id is None:
        raise CertificadoIndisponivel(
            "Emissor sem certificado configurado. Configure a emissão deste cliente."
        )
    return await obter_material(db, issuer.certificado_id, finalidade=finalidade)


def _dados_da_nota(invoice: "Invoice") -> dict:
    issuer = invoice.issuer
    return {
        "invoice_id": str(invoice.id),
        "valor_servico": float(invoice.valor_servico),
        "valor_deducoes": float(invoice.valor_deducoes or 0),
        "valor_iss": float(invoice.valor_iss) if invoice.valor_iss is not None else None,
        "descricao_servico": invoice.descricao_servico,
        "numero": invoice.numero or "000000",
        "serie": invoice.serie,
        "competencia": invoice.competencia.isoformat() if invoice.competencia else None,
        "cnpj_emissor": issuer.cnpj,
        "inscricao_municipal": issuer.inscricao_municipal,
        "regime_tributario": issuer.regime_tributario,
        "municipio_ibge": issuer.municipio_ibge,
        "cod_servico_lc116": issuer.cod_servico_lc116,
        "aliquota_iss": float(issuer.aliquota_iss) if issuer.aliquota_iss is not None else None,
        "retencao_iss": bool(issuer.retencao_iss),
        "modo_certificado": issuer.modo_certificado,
        "tomador_nome": invoice.tomador_nome,
        "tomador_cpf_cnpj": invoice.tomador_cpf_cnpj,
        "tomador_email": invoice.tomador_email,
        "tomador_municipio_ibge": invoice.tomador_municipio_ibge,
    }

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

        await ensure_client_in_tenant(self.repo.db, tenant_id, payload.client_id)

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

        if emissao_exige_certificado():
            # Emissão real só com o emissor liberado (modo + certificado válido
            # + dados mínimos + teste aprovado): app/domain/certificados/servico.py.
            from app.domain.certificados.servico import estado_emissao

            estado = await estado_emissao(self.repo.db, invoice.issuer)
            if not estado["emissao_liberada"]:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Emissão não liberada para esta empresa: " + " ".join(estado["pendencias"]),
                )

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

        try:
            material = await _material_do_emissor(self.repo.db, invoice.issuer, "emissao")
            if material is None:
                res = await provider.emit(_dados_da_nota(invoice))
            else:
                # Padrão nacional: DPS com número próprio, reservado e gravado
                # ANTES de transmitir (retentativa reaproveita o mesmo número).
                from app.domain.nfse_nacional.dps import montar_invoice_data

                invoice = await self._reservar_numero_dps(invoice)
                invoice_data = montar_invoice_data(
                    invoice, invoice.issuer, numero_dps=invoice.numero_dps, serie_dps=invoice.serie_dps
                )
                res = await provider.emit(invoice_data, material)
            status_res = res.get("status")

            if status_res == "issued":
                # Success
                invoice.status = "issued"
                invoice.numero = res.get("numero")
                invoice.provider_protocol = res.get("protocol")
                raw = res.get("raw")
                if res.get("id_dps") or res.get("avisos"):
                    raw = {**(raw if isinstance(raw, dict) else {"raw": raw}),
                           "id_dps": res.get("id_dps"), "avisos": res.get("avisos")}
                invoice.provider_response = raw
                invoice.xml_content = res.get("xml")
                # Nada é enviado ao storage: o XML fica em xml_content e o PDF
                # (DANFSe) é gerado sob demanda. Não gravar caminhos de arquivos
                # inexistentes.
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
                
                rejeicoes = res.get("rejeicoes") or [
                    {"codigo": res.get("codigo_rejeicao"), "descricao": res.get("descricao")}
                ]
                for item in rejeicoes:
                    descricao = item.get("descricao") or "Rejected by municipal server"
                    if item.get("complemento"):
                        descricao = f"{descricao} ({item['complemento']})"
                    await self.repo.create_rejection(
                        InvoiceRejection(
                            invoice_id=invoice.id,
                            tenant_id=tenant_id,
                            codigo_rejeicao=item.get("codigo"),
                            descricao=descricao,
                            raw_response=res.get("raw"),
                        )
                    )
                
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

        except TransientEmissionError as e:
            # Pedido não chegou ao provedor: nada foi emitido. A nota volta para a
            # fila (a fila de trabalho agenda nova tentativa); sem rejeição.
            invoice.status = "queued"
            await self.repo.update_invoice(invoice)
            await dispatch_invoice_event(self.repo.db, invoice, "emit_retry", {"error": str(e)})
            raise

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

    async def _reservar_numero_dps(self, invoice: Invoice) -> Invoice:
        """Reserva o próximo número de DPS do emissor (atômico) e grava na nota.

        Idempotente: nota que já tem número (retentativa) reaproveita o mesmo.
        """
        if invoice.numero_dps is not None:
            return invoice
        from sqlalchemy import update

        from app.core.config import settings

        numero = (
            await self.repo.db.execute(
                update(InvoiceIssuer)
                .where(InvoiceIssuer.id == invoice.issuer_id)
                .values(ultimo_numero_dps=InvoiceIssuer.ultimo_numero_dps + 1)
                .returning(InvoiceIssuer.ultimo_numero_dps)
            )
        ).scalar_one()
        invoice.numero_dps = int(numero)
        invoice.serie_dps = (getattr(settings, "NFSE_SERIE_DPS", "1") or "1")[:5]
        return await self.repo.update_invoice(invoice)

    async def cancel_invoice(self, invoice_id: uuid.UUID, tenant_id: uuid.UUID, reason: str, provider: NfseProvider) -> Invoice:
        invoice = await self.get_invoice(invoice_id, tenant_id)

        if invoice.status != "issued":
            raise ValueError(f"Cannot cancel invoice from status: {invoice.status}")

        invoice.status = "cancel_requested"
        await self.repo.update_invoice(invoice)
        await dispatch_invoice_event(self.repo.db, invoice, "cancel_requested", {"reason": reason})

        # Call provider cancel
        try:
            material = await _material_do_emissor(self.repo.db, invoice.issuer, "cancelamento")
            if material is None:
                res = await provider.cancel(invoice.provider_protocol, reason)
            else:
                res = await provider.cancel(
                    invoice.provider_protocol,
                    reason,
                    material,
                    codigo_motivo="1",
                    documento_autor=invoice.issuer.cnpj,
                )
            
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

    async def get_xml_content(self, invoice_id: uuid.UUID, tenant_id: uuid.UUID) -> tuple[str, str]:
        """XML da nota guardado no banco (xml_content) e o nome do arquivo."""
        invoice = await self.get_invoice(invoice_id, tenant_id)
        if not invoice.xml_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="XML ainda não disponível para esta nota.",
            )
        return invoice.xml_content, f"nfse-{invoice.numero or invoice.id}.xml"

    async def get_pdf_bytes(self, invoice_id: uuid.UUID, tenant_id: uuid.UUID) -> tuple[bytes, str]:
        """DANFSe simplificado gerado a partir dos dados da nota (só após emissão)."""
        from app.domain.invoices.danfse_pdf import render_danfse_pdf

        invoice = await self.get_invoice(invoice_id, tenant_id)
        if invoice.status not in ("issued", "cancelled", "cancel_requested") or not invoice.numero:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PDF ainda não gerado: a nota não foi emitida.",
            )
        return render_danfse_pdf(invoice), f"nfse-{invoice.numero}.pdf"

    async def record_background_failure(
        self, invoice_id: uuid.UUID, tenant_id: uuid.UUID, error: str
    ) -> None:
        """Registra rejeição + evento quando o processamento em segundo plano quebra
        antes de chegar ao provider. Nunca marca a nota como emitida."""
        invoice = await self.repo.get_by_id(invoice_id, tenant_id)
        if not invoice:
            return
        if invoice.status in ("queued", "processing", "validating"):
            invoice.status = "failed"
            await self.repo.update_invoice(invoice)
        await self.repo.create_rejection(
            InvoiceRejection(
                invoice_id=invoice.id,
                tenant_id=tenant_id,
                codigo_rejeicao="BACKGROUND",
                descricao=f"Falha no processamento da emissão: {error}",
                raw_response={"exception": error},
            )
        )
        await dispatch_invoice_event(self.repo.db, invoice, "failed", {"exception": error})
