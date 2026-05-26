"""Shared enums across all fiscal domains."""
from enum import Enum


class TaxRegime(str, Enum):
    SIMPLES_NACIONAL = "simples_nacional"
    LUCRO_PRESUMIDO = "lucro_presumido"
    LUCRO_REAL = "lucro_real"
    MEI = "mei"
    ISENTO = "isento"


class SubjectType(str, Enum):
    ACCOUNTANT = "accountant"
    CLIENT = "client"


class ProviderSlug(str, Enum):
    SERPRO_INTEGRA_CONTADOR = "serpro_integra_contador"
    NFSE_NACIONAL = "nfse_nacional"
    ASAAS_NFSE = "asaas_nfse"
    MUNICIPAL_GENERIC = "municipal_generic"
    MOCK = "mock"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
