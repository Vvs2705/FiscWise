from typing import List
from app.models.obligation import ObligationRule

def evaluate(client_profile: dict) -> List[ObligationRule]:
    """DAS — todo Simples Nacional ate dia 20 do mes seguinte"""
    regime = client_profile.get("regime_tributario")
    if regime in ("simples", "simples_nacional", "mei"):
        return [
            ObligationRule(
                code="DAS",
                name="DAS — Documento de Arrecadação do Simples Nacional",
                description="Guia unificada mensal do Simples Nacional",
                jurisdiction="federal",
                recurrence="monthly",
                due_day=20,
                active=True,
                applies_to_regimes=["simples", "simples_nacional", "mei"]
            )
        ]
    return []
