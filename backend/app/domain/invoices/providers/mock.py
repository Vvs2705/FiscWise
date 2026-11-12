import uuid
from app.domain.invoices.providers.base import NfseProvider

class MockNfseProvider(NfseProvider):
    """Somente dev/test: simula a prefeitura. Bloqueado em produção pela factory."""
    async def emit(self, invoice_data: dict) -> dict:
        # Simulate validation error if requested
        if "fail_validation" in invoice_data.get("descricao_servico", "").lower():
            return {
                "protocol": None,
                "status": "rejected",
                "codigo_rejeicao": "E001",
                "descricao": "Simulated validation failure",
                "raw": {"provider": "mock", "error": "Validation error"}
            }
        
        # Simulate processing failure
        if "fail_processing" in invoice_data.get("descricao_servico", "").lower():
            return {
                "protocol": f"MOCK-{uuid.uuid4()}",
                "status": "failed",
                "descricao": "Simulated internal provider error",
                "raw": {"provider": "mock", "error": "Internal error"}
            }

        return {
            "protocol": f"MOCK-{uuid.uuid4()}",
            "status": "issued",
            "numero": str(int(invoice_data.get("numero", "0")) + 1) if invoice_data.get("numero") else "000001",
            "xml": f"<xml><invoice><id>{uuid.uuid4()}</id><valor>{invoice_data.get('valor_servico')}</valor></invoice></xml>",
            "raw": {"provider": "mock", "mock": True, "success": True}
        }

    async def cancel(self, protocol: str, reason: str) -> dict:
        return {
            "status": "cancelled",
            "protocol": protocol,
            "raw": {"provider": "mock", "cancelled": True, "reason": reason}
        }

    async def query_status(self, protocol: str) -> dict:
        return {
            "status": "issued",
            "protocol": protocol,
            "raw": {"queried": True}
        }
