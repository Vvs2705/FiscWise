"""Mock e-CAC provider for tests and development."""


class MockEcacProvider:
    async def get_tax_status(self, subject) -> dict:
        return {
            "regularized": True,
            "pending_count": 0,
            "details": "Mock: sem pendências",
        }

    async def get_pgdas(self, subject, period: str) -> dict:
        return {"period": period, "status": "transmitted", "document": "MOCK_PGDAS"}

    async def generate_das(self, subject, period: str) -> dict:
        return {"period": period, "barcode": "12345678901234567890123456789012345678901234567", "amount": 150.00}

    async def get_dctfweb(self, subject, period: str) -> dict:
        return {"period": period, "status": "transmitted"}

    async def get_mailbox_messages(self, subject) -> list[dict]:
        return [
            {
                "external_id": "MOCK-001",
                "sender": "Receita Federal",
                "title": "Aviso de vencimento — simulação",
                "received_at": "2026-05-01T08:00:00Z",
                "risk_level": "low",
            }
        ]

    async def get_certidao_status(self, subject) -> dict:
        return {"status": "negativa", "valid_until": "2026-06-01"}

    async def get_procuracoes(self, subject) -> list[dict]:
        return [
            {
                "attorney_document": subject.document,
                "services": ["SIMPLES", "PGDAS"],
                "valid_from": "2026-01-01",
                "valid_until": "2026-12-31",
                "status": "active",
            }
        ]
