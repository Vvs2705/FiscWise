"""Job: Mailbox Sync — busca novas mensagens na caixa postal fiscal."""
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def run(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Fetch new messages from fiscal mailbox (e-CAC DTE, Simples Nacional, etc.).

    Expected payload:
        subject_id: str (UUID)
        tenant_id:  str (UUID)
        provider:   str  — e.g. "ecac", "simples_nacional"
    """
    subject_id = payload.get("subject_id")
    tenant_id = payload.get("tenant_id")
    provider = payload.get("provider", "ecac")

    logger.info(
        "mailbox_sync.start",
        extra={"subject_id": subject_id, "tenant_id": tenant_id, "provider": provider},
    )

    # TODO: use EcacProvider to fetch DTE messages and upsert FiscalMailboxMessage rows

    logger.info("mailbox_sync.done", extra={"subject_id": subject_id})
    return {"status": "ok", "subject_id": subject_id, "provider": provider}
