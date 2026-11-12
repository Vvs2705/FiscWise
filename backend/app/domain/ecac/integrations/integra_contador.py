from app.domain.ecac.integrations.base import EcacIntegrationProvider


class IntegraContadorProvider(EcacIntegrationProvider):
    """Ainda não implementado: depende de contrato SERPRO Integra Contador
    (consumer key/secret) e de procuração eletrônica do contribuinte."""

    async def fetch_fiscal_situation(self, cpf_cnpj: str) -> dict:
        raise NotImplementedError(
            "Integração e-CAC via SERPRO Integra Contador não implementada: exige contrato "
            "SERPRO e procuração eletrônica. Use ECAC_PROVIDER=mock apenas em desenvolvimento."
        )
