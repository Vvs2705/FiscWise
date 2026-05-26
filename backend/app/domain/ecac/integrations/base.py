from abc import ABC, abstractmethod

class EcacIntegrationProvider(ABC):
    @abstractmethod
    async def fetch_fiscal_situation(self, cpf_cnpj: str) -> dict:
        """Fetch general fiscal situation, including pendencias and debitos."""
        pass
