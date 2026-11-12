"""Escolhe o provider de NFS-e por NFSE_PROVIDER (mock | nacional).

Regra G2: a nota só fica ``issued`` quando um provider real confirmar. Em
produção/staging o mock é recusado (503) e a nota continua como está.
"""

from app.core.config import settings
from app.core.integration_mode import is_production_like, normalize_provider
from app.domain.invoices.providers.base import NfseProvider
from app.domain.invoices.providers.mock import MockNfseProvider
from app.domain.invoices.providers.nfse_nacional import NfseNacionalProvider

NFSE_NOT_CONFIGURED = (
    "Emissão de NFS-e não configurada (exige certificado A1 e homologação)"
)


class NfseProviderNotConfiguredError(RuntimeError):
    """Provider de NFS-e indisponível neste ambiente."""


def build_nfse_provider() -> NfseProvider:
    name = normalize_provider(settings.NFSE_PROVIDER)
    if name == "mock":
        if is_production_like():
            raise NfseProviderNotConfiguredError(NFSE_NOT_CONFIGURED)
        return MockNfseProvider()
    if name == "nacional":
        return NfseNacionalProvider()
    raise NfseProviderNotConfiguredError(f"NFSE_PROVIDER desconhecido: {name}")
