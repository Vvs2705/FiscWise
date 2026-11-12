"""Regras comuns para integrações externas simuladas (mock).

Um provider "mock" só é aceito fora de produção/staging. Em produção ele
nunca grava dados como se fossem reais: o endpoint responde 503 com uma
mensagem honesta do que falta configurar.
"""

from app.core.config import settings

PRODUCTION_LIKE_ENVIRONMENTS = {"production", "prod", "staging"}


def is_production_like() -> bool:
    return (settings.ENVIRONMENT or "").strip().lower() in PRODUCTION_LIKE_ENVIRONMENTS


def normalize_provider(name: str | None, default: str = "mock") -> str:
    return (name or default).strip().lower()


def is_mock_provider(name: str | None) -> bool:
    return normalize_provider(name) == "mock"


def mock_blocked(name: str | None) -> bool:
    """True quando o provider configurado é mock e o ambiente é produção/staging."""
    return is_mock_provider(name) and is_production_like()
