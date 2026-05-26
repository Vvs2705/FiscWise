import logging
from typing import Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.invoices.models import Invoice, InvoiceEvent
from app.core.audit import audit_log

logger = logging.getLogger(__name__)

async def dispatch_invoice_event(
    db: AsyncSession,
    invoice: Invoice,
    event_type: str,
    payload: Dict[str, Any] = None,
) -> InvoiceEvent:
    """Create and persist an invoice event and perform side-effects."""
    logger.info("Invoice event dispatched: id=%s, type=%s", invoice.id, event_type)
    
    # Store event in db
    event = InvoiceEvent(
        invoice_id=invoice.id,
        tenant_id=invoice.tenant_id,
        event_type=event_type,
        payload=payload or {}
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    # Side-effect: audit logging
    await audit_log(
        action=f"invoice.{event_type}",
        tenant_id=str(invoice.tenant_id),
        details={"invoice_id": str(invoice.id), "payload": payload}
    )

    return event
