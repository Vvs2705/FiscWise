"""Job: Guide Payment Check — verifica pagamento e transiciona guias vencidas."""
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def run(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Check payment status for fiscal guides and transition overdue ones.

    Expected payload:
        tenant_id: str (UUID) — optional; if omitted, runs for all tenants
        guide_id:  str (UUID) — optional; if omitted, processes all due guides
    """
    tenant_id = payload.get("tenant_id")
    guide_id = payload.get("guide_id")

    logger.info(
        "guide_payment_check.start",
        extra={"tenant_id": tenant_id, "guide_id": guide_id},
    )

    # TODO: query fiscal_guides WHERE status IN ('awaiting_payment', 'sent_to_customer')
    #   AND due_date < today() → transition to 'overdue'
    #   OR confirm payment via provider → transition to 'paid'

    logger.info("guide_payment_check.done")
    return {"status": "ok"}
