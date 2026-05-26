from app.domain.invoices.providers.base import NfseProvider

class NfseNacionalProvider(NfseProvider):
    """Real implementation client for government NFS-e portal API."""
    async def emit(self, invoice_data: dict) -> dict:
        # TODO: Implement real integration using gov.br restrita/producao API endpoints
        # For now, it delegates to mock-like behavior or raises not implemented
        return {
            "protocol": None,
            "status": "failed",
            "descricao": "Integration with Portal Nacional NFS-e not yet active. Using Mock provider instead.",
            "raw": {}
        }

    async def cancel(self, protocol: str, reason: str) -> dict:
        return {
            "status": "failed",
            "raw": {}
        }

    async def query_status(self, protocol: str) -> dict:
        return {
            "status": "failed",
            "raw": {}
        }
