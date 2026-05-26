from typing import List
from app.models.obligation import ObligationRule

def evaluate(client_profile: dict) -> List[ObligationRule]:
    """ISS municipal — baseado em municipio_ibge do client"""
    municipio = client_profile.get("municipio_ibge")
    if municipio:
        return [
            ObligationRule(
                code=f"ISS_{municipio}",
                name=f"ISS Municipal — IBGE {municipio}",
                description=f"Apuração do Imposto Sobre Serviços para o município {municipio}",
                jurisdiction="municipal",
                state=client_profile.get("uf"),
                recurrence="monthly",
                due_day=20,
                active=True
            )
        ]
    return []
