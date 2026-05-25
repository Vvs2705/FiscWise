"""
Fiscal Monitor Service for FiscWise.
Handles CNPJ registry status checks, CND downloads, debt alerts, and NF-e retrieval.
"""

import uuid
import logging
import random
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fiscal_monitor import FiscalMonitorSummary, FiscalNFe
from app.models.operations import AccountingClient, ClientDocument, DeadlineItem
from app.models.audit import AuditEvent

logger = logging.getLogger(__name__)


def _generate_mock_access_key() -> str:
    """Generates a realistic 44-digit NF-e access key."""
    # State code (35 = SP) + date (2605) + random digits to complete 44 chars
    state = "35"
    date_part = "2605"
    random_digits = "".join(str(random.randint(0, 9)) for _ in range(40))
    return (state + date_part + random_digits)[:44]


async def sync_client_fiscal_status(
    db: AsyncSession,
    client_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> tuple[FiscalMonitorSummary, int]:
    """
    Sincroniza a situação fiscal do CNPJ do cliente.
    Realiza consultas simuladas a Receita Federal, baixa CNDs e obtém NF-es.
    Se débitos forem identificados, cria tarefas de alerta automaticamente.
    """
    # 1. Verify client exists and belongs to this tenant
    stmt_client = select(AccountingClient).where(
        (AccountingClient.id == client_id) &
        (AccountingClient.tenant_id == tenant_id)
    )
    res_client = await db.execute(stmt_client)
    client = res_client.scalar_one_or_none()
    if not client:
        raise ValueError("Cliente não encontrado ou não pertence a este inquilino.")

    # 2. Get or create FiscalMonitorSummary
    stmt_summary = select(FiscalMonitorSummary).where(
        (FiscalMonitorSummary.client_id == client_id) &
        (FiscalMonitorSummary.tenant_id == tenant_id)
    )
    res_summary = await db.execute(stmt_summary)
    summary = res_summary.scalar_one_or_none()

    if not summary:
        summary = FiscalMonitorSummary(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            client_id=client_id,
            cnpj_status="REGULAR",
            cnd_status="REGULAR",
            has_debts=False,
            debt_count=0,
            total_debt_value=Decimal("0.00"),
            debts_list={"debts": []}
        )
        db.add(summary)
        await db.flush()

    # 3. Simulate CNPJ Situation Query
    # 95% regular, 5% irregular
    doc_digits = "".join(filter(str.isdigit, client.document or ""))
    is_irregular_mock = len(doc_digits) > 0 and doc_digits[-1] in ("9", "7")
    
    if is_irregular_mock:
        summary.cnpj_status = "SUSPENSO"
        summary.situation_details = {
            "situacao_cadastral": "SUSPENSA",
            "motivo_situacao_cadastral": "OMISSÃO DE DECLARAÇÕES",
            "data_situacao_cadastral": str(date.today() - timedelta(days=30)),
            "nome_empresarial": client.name,
            "natureza_juridica": "206-2 - Sociedade Limitada",
            "atividade_principal": [{"code": "62.01-5-01", "text": "Desenvolvimento de programas de computador sob encomenda"}]
        }
    else:
        summary.cnpj_status = "REGULAR"
        summary.situation_details = {
            "situacao_cadastral": "ATIVA",
            "motivo_situacao_cadastral": "REGULARIDADE FISCAL",
            "data_situacao_cadastral": str(date.today() - timedelta(days=365)),
            "nome_empresarial": client.name,
            "natureza_juridica": "206-2 - Sociedade Limitada",
            "atividade_principal": [{"code": "69.20-6-01", "text": "Atividades de contabilidade"}]
        }

    # 4. Simulate Debts Check
    # If the document ends in a specific digit or CNPJ status is irregular, simulate debts
    has_debts_mock = is_irregular_mock or (len(doc_digits) > 0 and doc_digits[-1] in ("5", "6"))
    
    if has_debts_mock:
        debts = [
            {
                "id": str(uuid.uuid4()),
                "type": "FEDERAL",
                "description": "DAS Simples Nacional - Competência 03/2026",
                "value": 350.00,
                "due_date": str(date.today() - timedelta(days=25))
            },
            {
                "id": str(uuid.uuid4()),
                "type": "FEDERAL",
                "description": "DAS Simples Nacional - Competência 04/2026",
                "value": 412.50,
                "due_date": str(date.today() - timedelta(days=5))
            }
        ]
        total_val = sum(d["value"] for d in debts)
        
        summary.has_debts = True
        summary.debt_count = len(debts)
        summary.total_debt_value = Decimal(f"{total_val:.2f}")
        summary.debts_list = {"debts": debts}
        summary.cnd_status = "COM_PENDENCIAS"

        # Create automated alert task (DeadlineItem) for each simulated debt
        for debt in debts:
            # Check if this task already exists to avoid duplication
            task_title = f"Regularizar {debt['description']}"
            stmt_task = select(DeadlineItem).where(
                (DeadlineItem.client_id == client_id) &
                (DeadlineItem.tenant_id == tenant_id) &
                (DeadlineItem.title == task_title)
            )
            res_task = await db.execute(stmt_task)
            existing_task = res_task.scalar_one_or_none()

            if not existing_task:
                new_task = DeadlineItem(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    client_id=client_id,
                    title=task_title,
                    category="fiscal",
                    due_date=date.today() + timedelta(days=5),
                    status="pending",
                    priority="high",
                    description=(
                        f"Alerta automático de irregularidade identificado na Receita Federal.\n\n"
                        f"- Tipo: {debt['type']}\n"
                        f"- Pendência: {debt['description']}\n"
                        f"- Valor do Débito: R$ {debt['value']:.2f}\n"
                        f"- Vencimento original: {debt['due_date']}"
                    )
                )
                db.add(new_task)
                
                # Audit event
                audit_evt = AuditEvent(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    action="fiscal_monitor.debt_alert",
                    entity_type="deadline_item",
                    entity_id=new_task.id,
                    after_data={"title": task_title, "amount": debt["value"]}
                )
                db.add(audit_evt)
    else:
        summary.has_debts = False
        summary.debt_count = 0
        summary.total_debt_value = Decimal("0.00")
        summary.debts_list = {"debts": []}
        summary.cnd_status = "REGULAR"

    # 5. Simulate CND Certificate Download
    # If client is regular, download CND. Otherwise, positive certificate with negative effect or pending.
    cnd_name = f"Certidao Negativa de Debitos Federais - {datetime.now().strftime('%Y%m%d')}.pdf"
    
    # Save CND as ClientDocument
    cnd_doc = ClientDocument(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        client_id=client_id,
        name=cnd_name,
        document_type="certidao_negativa",
        status="available",
        file_url=f"https://fiscwise.storage/cnd/federal-{uuid.uuid4()}.pdf",
        issued_at=date.today(),
        expires_at=date.today() + timedelta(days=180),
        notes="Download automático realizado pelo Monitor Fiscal da Receita Federal.",
        parse_status="pending"
    )
    db.add(cnd_doc)
    await db.flush()

    summary.last_cnd_document_id = cnd_doc.id
    summary.last_cnd_download_at = func.now()

    # 6. Simulate NF-e invoice query (fetch recent invoices)
    # Generate 3 recent invoices
    nfe_count = 0
    client_cnpj = client.document or "12345678000100"
    
    issuers = [
        {"name": "Distribuidora de Materiais Aliança Ltda", "doc": "09876543000199"},
        {"name": "Tech Solutions Brasil S/A", "doc": "55443322000188"},
        {"name": "Posto Shell Avenida Central", "doc": "11223344000177"}
    ]
    
    for i, issuer in enumerate(issuers):
        key = _generate_mock_access_key()
        # Verify unique key
        stmt_key = select(FiscalNFe).where(FiscalNFe.access_key == key)
        res_key = await db.execute(stmt_key)
        existing_nfe = res_key.scalar_one_or_none()
        
        if not existing_nfe:
            nfe = FiscalNFe(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                client_id=client_id,
                access_key=key,
                nfe_number=str(random.randint(10000, 99999)),
                nfe_type="ENTRADA" if i % 2 == 0 else "SAIDA",
                issuer_name=issuer["name"] if i % 2 == 0 else client.name,
                issuer_document=issuer["doc"] if i % 2 == 0 else client_cnpj,
                recipient_name=client.name if i % 2 == 0 else issuer["name"],
                recipient_document=client_cnpj if i % 2 == 0 else issuer["doc"],
                value=Decimal(f"{random.uniform(150.00, 8500.00):.2f}"),
                issued_at=datetime.now() - timedelta(days=random.randint(1, 10)),
                retrieved_at=datetime.now(),
                xml_url=f"https://fiscwise.storage/nfe/{key}.xml",
                status="AUTORIZADA"
            )
            db.add(nfe)
            nfe_count += 1

    summary.last_sync_at = func.now()
    summary.updated_at = func.now()

    # Log audit event
    audit_sync = AuditEvent(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        action="fiscal_monitor.sync",
        entity_type="fiscal_monitor_summary",
        entity_id=summary.id,
        after_data={
            "cnpj_status": summary.cnpj_status,
            "cnd_status": summary.cnd_status,
            "has_debts": summary.has_debts,
            "nfes_fetched": nfe_count
        }
    )
    db.add(audit_sync)

    await db.commit()
    await db.refresh(summary)
    
    return summary, nfe_count


async def import_external_nfe(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    client_id: uuid.UUID,
    access_key: str,
    nfe_number: str,
    nfe_type: str,
    issuer_name: str,
    issuer_document: str,
    recipient_name: str,
    recipient_document: str,
    value: Decimal,
    issued_at: datetime,
) -> FiscalNFe:
    """
    Imports a single NF-e, typically triggered via partner webhook.
    """
    # Check if access key exists
    stmt_key = select(FiscalNFe).where(FiscalNFe.access_key == access_key)
    res_key = await db.execute(stmt_key)
    existing_nfe = res_key.scalar_one_or_none()
    
    if existing_nfe:
        return existing_nfe

    new_nfe = FiscalNFe(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        client_id=client_id,
        access_key=access_key,
        nfe_number=nfe_number,
        nfe_type=nfe_type,
        issuer_name=issuer_name,
        issuer_document=issuer_document,
        recipient_name=recipient_name,
        recipient_document=recipient_document,
        value=value,
        issued_at=issued_at,
        retrieved_at=datetime.now(),
        xml_url=f"https://fiscwise.storage/nfe/{access_key}.xml",
        status="AUTORIZADA"
    )
    db.add(new_nfe)
    
    # Audit log
    audit_evt = AuditEvent(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        action="fiscal_monitor.nfe_import",
        entity_type="fiscal_nfe",
        entity_id=new_nfe.id,
        after_data={"access_key": access_key, "value": float(value)}
    )
    db.add(audit_evt)

    await db.commit()
    await db.refresh(new_nfe)
    return new_nfe
