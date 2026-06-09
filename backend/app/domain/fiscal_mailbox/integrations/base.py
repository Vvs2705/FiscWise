from abc import ABC, abstractmethod
from typing import List, Dict, Any


class FiscalMailboxProvider(ABC):
    """Provider that fetches fiscal mailbox (e-CAC / DTE) messages for a tenant.

    Implementations return a list of raw message dicts. Each dict should carry
    at least an ``external_id`` so the service can ingest idempotently.
    """

    @abstractmethod
    async def fetch_messages(self, tenant_id: str) -> List[Dict[str, Any]]:
        ...
