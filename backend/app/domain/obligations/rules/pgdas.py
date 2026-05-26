from typing import List
from app.models.obligation import ObligationRule

def evaluate(client_profile: dict) -> List[ObligationRule]:
    """PGDAS-D — apuracao mensal Simples Nacional"""
    regime = client_profile.get("regime_tributario")
    if regime in ("simples", "simples_nacional"):
        return [
            ObligationRule(
                code="PGDAS-D",
                name="PGDAS-D — Programa Gerador do Documento de Arrecadação do Simples Nacional - Declaratório",
                description="Apuração mensal do Simples Nacional",
                jurisdiction="federal",
                recurrence="monthly",
                due_day=20,
                active=True,
                applies_to_regimes=["simples", "simples_nacional"]
            )
        ]
    return []
