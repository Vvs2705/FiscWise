"""Worker entry point — FiscWise background job dispatcher."""
import asyncio
import logging
from typing import Any, Callable, Coroutine

from app.workers.jobs import (
    fiscal_sync,
    invoice_status_sync,
    guide_payment_check,
    mailbox_sync,
    monthly_closing_generation,
    document_scan,
)
from app.workers.queues import Queue, JOB_QUEUE_MAP

logger = logging.getLogger(__name__)

# Registry mapping job type name → async run function
JOB_REGISTRY: dict[str, Callable[..., Coroutine[Any, Any, dict]]] = {
    "fiscal_sync": fiscal_sync.run,
    "invoice_status_sync": invoice_status_sync.run,
    "guide_payment_check": guide_payment_check.run,
    "mailbox_sync": mailbox_sync.run,
    "monthly_closing_generation": monthly_closing_generation.run,
    "document_scan": document_scan.run,
}


async def dispatch(job_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Dispatch a job by type. Raises ValueError for unknown job types."""
    handler = JOB_REGISTRY.get(job_type)
    if not handler:
        raise ValueError(f"Unknown job type: {job_type!r}")

    queue = JOB_QUEUE_MAP.get(job_type, Queue.DEFAULT)
    logger.info("worker.dispatch", extra={"job_type": job_type, "queue": queue.value})
    return await handler(payload)


if __name__ == "__main__":
    # Manual test: python -m app.workers.main
    async def _smoke() -> None:
        result = await dispatch("guide_payment_check", {})
        print(result)

    asyncio.run(_smoke())
