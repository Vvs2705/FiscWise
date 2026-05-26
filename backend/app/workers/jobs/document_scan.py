"""Job: Document Scan — valida MIME e metadados de documentos armazenados."""
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def run(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Scan a stored document: validate MIME type, extract metadata, flag anomalies.

    Expected payload:
        storage_key: str  — full path in storage (with tenant prefix)
        bucket:      str
        tenant_id:   str (UUID)
        entity_type: str  — e.g. "certificate", "invoice", "dossier"
        entity_id:   str (UUID)
    """
    storage_key = payload.get("storage_key")
    bucket = payload.get("bucket")
    tenant_id = payload.get("tenant_id")
    entity_type = payload.get("entity_type")
    entity_id = payload.get("entity_id")

    logger.info(
        "document_scan.start",
        extra={
            "storage_key": storage_key,
            "bucket": bucket,
            "tenant_id": tenant_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
        },
    )

    # TODO: download from storage, run python-magic MIME check,
    #   update entity record with scan results, flag if unexpected MIME

    logger.info("document_scan.done", extra={"storage_key": storage_key})
    return {"status": "ok", "storage_key": storage_key}
