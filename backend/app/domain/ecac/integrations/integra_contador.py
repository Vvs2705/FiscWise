from app.domain.ecac.integrations.base import EcacIntegrationProvider

class IntegraContadorProvider(EcacIntegrationProvider):
    async def fetch_fiscal_situation(self, cpf_cnpj: str) -> dict:
        # TODO: Implement Serpro/Integra Contador real API integration
        raise NotImplementedError("Integra Contador integration is a stub. Use MockEcacIntegrationProvider in development and tests.")
