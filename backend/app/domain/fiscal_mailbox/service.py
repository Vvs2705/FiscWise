import uuid
import logging
from datetime import datetime
from typing import List, Optional

from app.domain.fiscal_mailbox.models import FiscalMailboxMessage
from app.domain.fiscal_mailbox.repository import FiscalMailboxRepository
from app.domain.fiscal_mailbox.integrations.base import FiscalMailboxProvider
from app.core.audit import audit_log

logger = logging.getLogger(__name__)

_VALID_RISK = {"critical", "high", "medium", "low", "none"}
_VALID_STATUS = {"unread", "read", "in_progress", "resolved", "archived"}


def _parse_dt(value) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


class FiscalMailboxService:
    def __init__(self, repo: FiscalMailboxRepository):
        self.repo = repo

    async def list_messages(
        self,
        tenant_id: uuid.UUID,
        *,
        client_id: Optional[uuid.UUID] = None,
        risk: Optional[str] = None,
        status: Optional[str] = None,
        organ: Optional[str] = None,
    ) -> List[FiscalMailboxMessage]:
        return await self.repo.list_messages(
            tenant_id,
            client_id=client_id,
            risk=None if risk in (None, "all") else risk,
            status=None if status in (None, "all") else status,
            organ=None if organ in (None, "all") else organ,
        )

    async def get_message(self, message_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[FiscalMailboxMessage]:
        """Fetch a single message; mark it as read on first open (unread -> read)."""
        message = await self.repo.get_by_id(message_id, tenant_id)
        if message and message.status == "unread":
            message.status = "read"
            message = await self.repo.save(message)
        return message

    async def set_status(
        self, message_id: uuid.UUID, tenant_id: uuid.UUID, new_status: str
    ) -> Optional[FiscalMailboxMessage]:
        if new_status not in _VALID_STATUS:
            raise ValueError(f"Invalid status: {new_status}")
        message = await self.repo.get_by_id(message_id, tenant_id)
        if not message:
            return None
        message.status = new_status
        saved = await self.repo.save(message)
        await audit_log(
            action="fiscal_mailbox.status_changed",
            tenant_id=str(tenant_id),
            details={"message_id": str(message_id), "status": new_status},
        )
        return saved

    async def sync_messages(
        self, tenant_id: uuid.UUID, provider: FiscalMailboxProvider
    ) -> dict:
        """Pull messages from the provider and ingest new ones idempotently."""
        raw_messages = await provider.fetch_messages(str(tenant_id))
        created = 0
        skipped = 0

        for raw in raw_messages:
            external_id = raw.get("external_id")
            if external_id:
                existing = await self.repo.get_by_external_id(external_id, tenant_id)
                if existing:
                    skipped += 1
                    continue

            risk = raw.get("risk") or "none"
            if risk not in _VALID_RISK:
                risk = "none"

            message = FiscalMailboxMessage(
                tenant_id=tenant_id,
                external_id=external_id,
                client_name=raw.get("client_name"),
                client_cnpj=raw.get("client_cnpj"),
                subject=raw.get("subject") or "(sem assunto)",
                summary=raw.get("summary"),
                body=raw.get("body"),
                organ=raw.get("organ"),
                received_at=_parse_dt(raw.get("received_at")),
                deadline=_parse_dt(raw.get("deadline")),
                risk=risk,
                status="unread",
                task_created=False,
                obligation_linked=raw.get("obligation_linked"),
                tags=raw.get("tags") or [],
            )
            await self.repo.add(message)
            created += 1

        await audit_log(
            action="fiscal_mailbox.synced",
            tenant_id=str(tenant_id),
            details={"synced": len(raw_messages), "created": created, "skipped": skipped},
        )
        return {"synced": len(raw_messages), "created": created, "skipped": skipped}
