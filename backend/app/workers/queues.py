"""Worker queue definitions for FiscWise background jobs."""
from enum import Enum


class Queue(str, Enum):
    """Named queues with priority levels."""
    HIGH = "high"        # Time-critical: guide payment checks, overdue transitions
    DEFAULT = "default"  # Standard: e-CAC sync, invoice status
    LOW = "low"          # Bulk: monthly closing generation, document scan, mailbox sync


# Queue routing table for job types
JOB_QUEUE_MAP: dict[str, Queue] = {
    "fiscal_sync": Queue.DEFAULT,
    "invoice_status_sync": Queue.DEFAULT,
    "guide_payment_check": Queue.HIGH,
    "mailbox_sync": Queue.LOW,
    "monthly_closing_generation": Queue.LOW,
    "document_scan": Queue.LOW,
}
