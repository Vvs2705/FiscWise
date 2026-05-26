"""Job: Monthly Closing Generation — gera itens de fechamento mensal automaticamente."""
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def run(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Auto-generate monthly closing items for a given client/competence.

    Expected payload:
        closing_id:  str (UUID)
        tenant_id:   str (UUID)
        client_id:   str (UUID)
        competence:  str  — "YYYY-MM"
    """
    closing_id = payload.get("closing_id")
    tenant_id = payload.get("tenant_id")
    client_id = payload.get("client_id")
    competence = payload.get("competence")

    logger.info(
        "monthly_closing_generation.start",
        extra={
            "closing_id": closing_id,
            "tenant_id": tenant_id,
            "client_id": client_id,
            "competence": competence,
        },
    )

    # TODO: query invoices, fiscal guides, obligations for the competence
    #   → create MonthlyClosingItem rows for each pending document

    logger.info("monthly_closing_generation.done", extra={"closing_id": closing_id})
    return {"status": "ok", "closing_id": closing_id}
