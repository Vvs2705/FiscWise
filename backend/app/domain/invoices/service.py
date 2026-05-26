"""Invoice domain service — business logic for NFS-e lifecycle."""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.invoices.models import Invoice, InvoiceIssuer, InvoiceEvent, InvoiceStatus
from app.domain.invoices.schemas import InvoiceCreate, InvoicePatch
from app.domain.invoices.repository import get_invoice, get_issuer
from app.domain.fiscal_core.events import (
    INVOICE_DRAFT_CREATED, INVOICE_ISSUE_REQUESTED, INVOICE_ISSUED,
    INVOICE_REJECTED, INVOICE_CANCEL_REQUESTED, INVOICE_CANCELLED,
)
from app.services.audit import log_audit_event

logger = logging.getLogger(__name__)


def _get_provider(provider_slug: str):
    """Resolve provider slug to provider instance."""
    from app.domain.invoices.providers.mock import MockInvoiceProvider
    # Future: map real providers from env/credentials
    providers = {"mock": MockInvoiceProvider()}
    prov = providers.get(provider_slug)
    if not prov:
        raise HTTPException(status_code=400, detail=f"Provider '{provider_slug}' not configured.")
    return prov


async def _record_invoice_event(
    db: AsyncSession,
    invoice: Invoice,
    event_type: str,
    actor_user_id: Optional[uuid.UUID] = None,
    payload: Optional[dict] = None,
):
    event = InvoiceEvent(
        id=uuid.uuid4(),
        tenant_id=invoice.tenant_id,
        invoice_id=invoice.id,
        event_type=event_type,
        actor_user_id=actor_user_id,
        payload=payload,
    )
    db.add(event)
    await db.flush()
    return event


async def create_draft(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    data: InvoiceCreate,
    actor_user_id: uuid.UUID,
) -> Invoice:
    issuer = await get_issuer(db, data.issuer_id, tenant_id)
    if not issuer:
        raise HTTPException(status_code=404, detail="Issuer not found or does not belong to this tenant.")
    if not issuer.active:
        raise HTTPException(status_code=422, detail="Issuer is inactive.")

    invoice = Invoice(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        issuer_id=data.issuer_id,
        customer_client_id=data.customer_client_id,
        receivable_id=data.receivable_id,
        status=InvoiceStatus.DRAFT.value,
        invoice_type=data.invoice_type,
        competence=data.competence,
        service_profile_id=data.service_profile_id,
        service_description=data.service_description,
        service_code=data.service_code,
        amount=data.amount,
        deductions=data.deductions,
        iss_rate=data.iss_rate,
        retained_taxes=data.retained_taxes,
        provider=data.provider,
        created_by=actor_user_id,
    )
    db.add(invoice)
    await db.flush()
    await _record_invoice_event(db, invoice, INVOICE_DRAFT_CREATED, actor_user_id)
    await log_audit_event(
        db=db,
        tenant_id=tenant_id,
        action=INVOICE_DRAFT_CREATED,
        entity_type="invoice",
        actor_user_id=actor_user_id,
        entity_id=invoice.id,
    )
    await db.commit()
    await db.refresh(invoice)
    return invoice


async def issue_invoice(
    db: AsyncSession,
    invoice_id: uuid.UUID,
    tenant_id: uuid.UUID,
    actor_user_id: uuid.UUID,
) -> Invoice:
    invoice = await get_invoice(db, invoice_id, tenant_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    if invoice.status not in (InvoiceStatus.DRAFT.value, InvoiceStatus.READY_TO_ISSUE.value):
        raise HTTPException(status_code=422, detail=f"Cannot issue invoice in status '{invoice.status}'.")

    invoice.status = InvoiceStatus.ISSUING.value
    await _record_invoice_event(db, invoice, INVOICE_ISSUE_REQUESTED, actor_user_id)
    await db.flush()

    provider = _get_provider(invoice.provider)
    try:
        result = await provider.issue_nfse(invoice)
        invoice.status = InvoiceStatus.ISSUED.value
        invoice.provider_invoice_id = result.get("provider_invoice_id")
        invoice.provider_protocol = result.get("provider_protocol")
        invoice.verification_code = result.get("verification_code")
        invoice.number = result.get("number")
        invoice.series = result.get("series")
        invoice.issued_at = datetime.now(timezone.utc)
        await _record_invoice_event(db, invoice, INVOICE_ISSUED, actor_user_id, result)
    except Exception as exc:
        invoice.status = InvoiceStatus.REJECTED.value
        invoice.rejection_reason = str(exc)
        await _record_invoice_event(db, invoice, INVOICE_REJECTED, actor_user_id, {"error": str(exc)})
        logger.error("NFS-e issuance failed: invoice=%s error=%s", invoice_id, exc)

    await log_audit_event(
        db=db, tenant_id=tenant_id,
        action=INVOICE_ISSUED if invoice.status == InvoiceStatus.ISSUED.value else INVOICE_REJECTED,
        entity_type="invoice", actor_user_id=actor_user_id, entity_id=invoice.id,
    )
    await db.commit()
    await db.refresh(invoice)
    return invoice


async def cancel_invoice(
    db: AsyncSession,
    invoice_id: uuid.UUID,
    tenant_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    reason: str,
) -> Invoice:
    invoice = await get_invoice(db, invoice_id, tenant_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    if invoice.status not in (
        InvoiceStatus.DRAFT.value,
        InvoiceStatus.READY_TO_ISSUE.value,
        InvoiceStatus.ISSUED.value,
    ):
        raise HTTPException(
            status_code=422,
            detail=f"Cannot cancel invoice in status '{invoice.status}'.",
        )

    if invoice.status == InvoiceStatus.DRAFT.value:
        # Draft cancellation: no provider call needed
        invoice.status = InvoiceStatus.CANCELLED.value
        invoice.cancelled_at = datetime.now(timezone.utc)
        await _record_invoice_event(db, invoice, INVOICE_CANCELLED, actor_user_id, {"reason": reason})
    else:
        invoice.status = InvoiceStatus.CANCEL_REQUESTED.value
        await _record_invoice_event(db, invoice, INVOICE_CANCEL_REQUESTED, actor_user_id, {"reason": reason})
        await db.flush()

        provider = _get_provider(invoice.provider)
        try:
            await provider.cancel_nfse(invoice, reason)
            invoice.status = InvoiceStatus.CANCELLED.value
            invoice.cancelled_at = datetime.now(timezone.utc)
            await _record_invoice_event(db, invoice, INVOICE_CANCELLED, actor_user_id)
        except Exception as exc:
            invoice.status = InvoiceStatus.ISSUED.value  # rollback status
            raise HTTPException(status_code=502, detail=f"Cancellation failed: {exc}")

    await log_audit_event(
        db=db, tenant_id=tenant_id, action=INVOICE_CANCELLED,
        entity_type="invoice", actor_user_id=actor_user_id, entity_id=invoice.id,
    )
    await db.commit()
    await db.refresh(invoice)
    return invoice
