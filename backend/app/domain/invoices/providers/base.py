from abc import ABC, abstractmethod

class NfseProvider(ABC):
    @abstractmethod
    async def emit(self, invoice_data: dict) -> dict:
        """Envia NFS-e. Retorna {'protocol': str, 'status': str, 'numero': str, 'raw': dict}"""
        pass

    @abstractmethod
    async def cancel(self, protocol: str, reason: str) -> dict:
        """Cancela NFS-e por protocolo."""
        pass

    @abstractmethod
    async def query_status(self, protocol: str) -> dict:
        """Consulta status de protocolo no provedor."""
        pass
