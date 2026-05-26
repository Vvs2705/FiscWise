import uuid
from datetime import date, timedelta
from app.domain.ecac.integrations.base import EcacIntegrationProvider

class MockEcacIntegrationProvider(EcacIntegrationProvider):
    async def fetch_fiscal_situation(self, cpf_cnpj: str) -> dict:
        # Simulate regular or pending based on CPF/CNPJ suffix for testability
        is_pending = cpf_cnpj.endswith("99") or cpf_cnpj == "11111111111"
        return {
            "status_geral": "pendente" if is_pending else "regular",
            "pendencias": [
                {"codigo": "PEND-001", "descricao": "Ausência de PGDAS-D de 03/2026"}
            ] if is_pending else [],
            "debitos": [
                {"origem": "Receita Federal", "valor": 550.00, "vencimento": "2026-04-20"}
            ] if is_pending else [],
            "certidao_status": "irregular" if is_pending else "regular",
            "certidao_validade": (date.today() + timedelta(days=120)).isoformat(),
            "raw": {"provider": "mock", "authenticated": True}
        }
