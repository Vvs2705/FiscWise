"""Job: Fiscal Sync — sincroniza dados do e-CAC para um sujeito fiscal."""
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def run(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Trigger an e-CAC data sync for a given fiscal subject.

    Expected payload:
        subject_id: str (UUID)
        tenant_id: str (UUID)
        sync_type: str  — "full" | "incremental"
    """
    subject_id = payload.get("subject_id")
    tenant_id = payload.get("tenant_id")
    sync_type = payload.get("sync_type", "incremental")

    logger.info(
        "fiscal_sync.start",
        extra={"subject_id": subject_id, "tenant_id": tenant_id, "sync_type": sync_type},
    )

    # TODO: instantiate EcacService with provider and execute sync
    # from app.domain.ecac.service import EcacService
    # await EcacService(...).sync(subject_id)

    logger.info("fiscal_sync.done", extra={"subject_id": subject_id})
    return {"status": "ok", "subject_id": subject_id, "sync_type": sync_type}
