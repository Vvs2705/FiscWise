"""Escolhe o provider do e-CAC por ECAC_PROVIDER (mock | integra_contador).

Fail-closed: em produção/staging o mock é recusado e um provider desconhecido
também, para a API responder 503 em vez de gravar situação fiscal inventada.
"""

from app.core.config import settings
from app.core.integration_mode import is_production_like, normalize_provider
from app.domain.ecac.integrations.base import EcacIntegrationProvider
from app.domain.ecac.integrations.integra_contador import IntegraContadorProvider
from app.domain.ecac.integrations.mock import MockEcacIntegrationProvider


class EcacProviderNotConfiguredError(RuntimeError):
    """Provider do e-CAC indisponível neste ambiente."""


def build_ecac_provider() -> EcacIntegrationProvider:
    name = normalize_provider(settings.ECAC_PROVIDER)
    if name == "mock":
        if is_production_like():
            raise EcacProviderNotConfiguredError(
                "Consulta ao e-CAC exige integração SERPRO Integra Contador (não configurada)."
            )
        return MockEcacIntegrationProvider()
    if name == "integra_contador":
        return IntegraContadorProvider()
    raise EcacProviderNotConfiguredError(f"ECAC_PROVIDER desconhecido: {name}")
