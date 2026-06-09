from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

from app.domain.fiscal_mailbox.integrations.base import FiscalMailboxProvider


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


class MockFiscalMailboxProvider(FiscalMailboxProvider):
    """Deterministic mock provider used until a real e-CAC/DTE integration exists.

    Mirrors the shape of a real provider response so the service and the
    frontend can be wired against a stable contract. Replace with a real
    integration (Integra Contador / e-CAC scraping) without touching the
    service or the API layer.
    """

    async def fetch_messages(self, tenant_id: str) -> List[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        return [
            {
                "external_id": "mock-msg-001",
                "client_name": "Tech Solutions Ltda",
                "client_cnpj": "12.345.678/0001-90",
                "subject": "Intimação — Malha Fina IRPJ 2023",
                "summary": "Divergência na declaração de IRPJ. Prazo de 30 dias para resposta.",
                "body": "Identificamos divergências na Declaração de IRPJ do exercício 2023. "
                        "Apresente documentação comprobatória ou retifique a declaração em até 30 dias.",
                "organ": "Receita Federal",
                "received_at": _iso(now - timedelta(days=2)),
                "deadline": _iso(now + timedelta(days=28)),
                "risk": "critical",
                "tags": ["IRPJ", "malha-fina", "intimação"],
            },
            {
                "external_id": "mock-msg-002",
                "client_name": "Comércio São Paulo ME",
                "client_cnpj": "98.765.432/0001-11",
                "subject": "Débito Automático — DAS Maio/2026",
                "summary": "Confirmação de débito automático do DAS Simples Nacional (05/2026).",
                "body": "DAS Simples Nacional — Competência 05/2026. Valor: R$ 1.240,00. "
                        "Situação: agendado para débito automático.",
                "organ": "PGFN",
                "received_at": _iso(now - timedelta(days=1)),
                "deadline": _iso(now + timedelta(days=10)),
                "risk": "low",
                "tags": ["DAS", "Simples Nacional"],
            },
            {
                "external_id": "mock-msg-003",
                "client_name": "Construtora Horizonte SA",
                "client_cnpj": "11.222.333/0001-44",
                "subject": "Notificação — Parcelamento REFIS pendente",
                "summary": "Parcela do REFIS vencida. Risco de exclusão do programa.",
                "body": "Sua parcela do parcelamento REFIS venceu. A não regularização em 15 dias "
                        "resultará na exclusão do programa e inscrição em dívida ativa.",
                "organ": "PGFN",
                "received_at": _iso(now - timedelta(days=5)),
                "deadline": _iso(now + timedelta(days=3)),
                "risk": "high",
                "tags": ["REFIS", "parcelamento", "PGFN"],
            },
        ]
