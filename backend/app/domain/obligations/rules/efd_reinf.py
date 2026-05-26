from typing import List
from app.models.obligation import ObligationRule

def evaluate(client_profile: dict) -> List[ObligationRule]:
    """EFD-Reinf — prestadores de servico com retencao na fonte"""
    regime = client_profile.get("regime_tributario")
    if regime and regime != "mei":
        return [
            ObligationRule(
                code="EFD-REINF",
                name="EFD-Reinf — Escrituração Fiscal Digital de Retenções e Outras Informações Fiscais",
                description="Escrituração para prestadores/tomadores de serviço com retenções na fonte",
                jurisdiction="federal",
                recurrence="monthly",
                due_day=15,
                active=True
            )
        ]
    return []
