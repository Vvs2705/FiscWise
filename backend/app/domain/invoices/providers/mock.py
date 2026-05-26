"""Mock NFS-e provider for tests and development."""
import uuid
from datetime import datetime, timezone


class MockInvoiceProvider:
    """Simulates NFS-e issuance without calling any external API."""

    async def validate_issuer(self, issuer) -> dict:
        return {"valid": True, "message": "Mock: issuer valid"}

    async def issue_nfse(self, invoice) -> dict:
        return {
            "provider_invoice_id": f"MOCK-{uuid.uuid4().hex[:8].upper()}",
            "provider_protocol": f"PROT-{uuid.uuid4().hex[:6].upper()}",
            "verification_code": f"VER-{uuid.uuid4().hex[:8].upper()}",
            "number": str(uuid.uuid4().int % 100000).zfill(5),
            "series": "A",
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "status": "issued",
        }

    async def get_status(self, invoice) -> dict:
        return {"status": "issued", "provider_invoice_id": invoice.provider_invoice_id}

    async def cancel_nfse(self, invoice, reason: str) -> dict:
        return {"status": "cancelled", "cancelled_at": datetime.now(timezone.utc).isoformat()}

    async def fetch_xml(self, invoice) -> bytes:
        return b'<?xml version="1.0"?><NFS-e>MOCK</NFS-e>'

    async def fetch_pdf(self, invoice) -> bytes:
        return b"%PDF-1.4 MOCK"
