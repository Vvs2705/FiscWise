"""Job: Invoice Status Sync — atualiza status de NFS-e junto ao provedor."""
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def run(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Poll the invoice provider and update the local invoice status.

    Expected payload:
        invoice_id: str (UUID)
        tenant_id: str (UUID)
    """
    invoice_id = payload.get("invoice_id")
    tenant_id = payload.get("tenant_id")

    logger.info(
        "invoice_status_sync.start",
        extra={"invoice_id": invoice_id, "tenant_id": tenant_id},
    )

    # TODO: instantiate InvoiceService with provider and poll status
    # from app.domain.invoices.service import InvoiceService
    # await InvoiceService(...).refresh_status(invoice_id)

    logger.info("invoice_status_sync.done", extra={"invoice_id": invoice_id})
    return {"status": "ok", "invoice_id": invoice_id}
