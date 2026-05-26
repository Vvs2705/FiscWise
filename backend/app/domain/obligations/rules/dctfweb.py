from typing import List
from app.models.obligation import ObligationRule

def evaluate(client_profile: dict) -> List[ObligationRule]:
    """DCTFWeb — empresas com retencoes ou funcionarios"""
    if client_profile.get("tem_funcionarios") or client_profile.get("has_employees"):
        return [
            ObligationRule(
                code="DCTFWEB",
                name="DCTFWeb — Declaração de Débitos e Créditos Tributários Federais Web",
                description="Declaração mensal de contribuições previdenciárias e FGTS",
                jurisdiction="federal",
                recurrence="monthly",
                due_day=15,
                active=True,
                requires_employees=True
            ),
            ObligationRule(
                code="ESOCIAL",
                name="eSocial — Sistema de Escrituração Digital das Obrigações Fiscais, Previdenciárias e Trabalhistas",
                description="Envio de eventos de folha e trabalhadores",
                jurisdiction="federal",
                recurrence="monthly",
                due_day=15,
                active=True,
                requires_employees=True
            )
        ]
    return []
