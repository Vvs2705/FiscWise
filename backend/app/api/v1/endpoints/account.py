"""Account management endpoints for FiscWise (LGPD compliance)

Provides data export and deletion request capabilities as required by
Brazil's Lei Geral de Proteção de Dados (LGPD, Law 13.709/2018).

Art. 18 rights implemented:
  - Right to access: GET /account/export
  - Right to erasure: POST /account/delete (generates ticket, not immediate)
"""

import enum
import logging
import re
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.tenant import Tenant
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/account", tags=["Account / LGPD"])


# Colunas que nunca saem na exportação (credenciais, hashes, conteúdo cifrado).
_COLUNAS_SENSIVEIS = re.compile(r"(hash|token|secret|senha|password|pfx|encrypted|cipher|private_key)", re.I)


def _valor_json(v):
    if v is None or isinstance(v, (str, int, float, bool, list, dict)):
        return v
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, (uuid.UUID, Decimal)):
        return str(v)
    if isinstance(v, enum.Enum):
        return v.value
    if isinstance(v, (bytes, bytearray, memoryview)):
        return None  # binário (ex.: arquivo de certificado) não vai no JSON
    return str(v)


def _linha(obj) -> dict:
    return {
        col.key: _valor_json(getattr(obj, col.key, None))
        for col in obj.__mapper__.column_attrs
        if not _COLUNAS_SENSIVEIS.search(col.key)
    }


def _modelos_exportados():
    """Dados do escritório, por tabela (o nome vira a chave no JSON)."""
    from app.models.calculator import CalculatorSimulation, FiscalAssistantMessage, TaxScenario
    from app.models.fiscal_monitor import FiscalNFe
    from app.models.obligation import ClientObligationProfile, DocumentChecklistItem, ObligationInstance
    from app.models.operations import (
        AccountingClient, AccountReceivable, ClientDocument, CompanyDocument,
        CompanyPartner, DasPayment, DeadlineItem, DigitalCertificate,
    )

    return [
        ("clientes", AccountingClient),
        ("socios", CompanyPartner),
        ("documentos_clientes", ClientDocument),
        ("documentos_empresa", CompanyDocument),
        ("certificados_digitais", DigitalCertificate),
        ("contas_a_receber", AccountReceivable),
        ("guias_das", DasPayment),
        ("prazos", DeadlineItem),
        ("perfis_de_obrigacoes", ClientObligationProfile),
        ("obrigacoes", ObligationInstance),
        ("checklist_documentos", DocumentChecklistItem),
        ("notas_fiscais", FiscalNFe),
        ("simulacoes_calculadora", CalculatorSimulation),
        ("cenarios_tributarios", TaxScenario),
        ("mensagens_assistente", FiscalAssistantMessage),
    ]


@router.get("/export")
async def export_my_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Exporta os dados do usuário e, para o dono, todos os dados do escritório
    (LGPD Art. 18, I, II e V: acesso e portabilidade).

    Sai em JSON, uma lista por tabela (clientes, documentos, contas a receber,
    obrigações, notas etc.). Credenciais, hashes e binários ficam de fora. Os
    arquivos em si continuam baixáveis pelas telas (o `file_url` de cada
    documento vai na exportação). Funciona também com a conta só leitura.
    """
    from sqlalchemy import func
    from app.models.operations import AccountingClient, ClientDocument, AccountReceivable

    # User data
    user_data = {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "phone": current_user.phone,
        "role": current_user.role.value,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat() if hasattr(current_user, 'created_at') and current_user.created_at else None,
    }

    # Tenant data (only if owner)
    tenant_data = None
    record_counts = {}
    dados: dict[str, list] = {}

    if current_user.role.value == "owner":
        tenant_result = await db.execute(
            select(Tenant).where(Tenant.id == current_user.tenant_id)
        )
        tenant = tenant_result.scalar_one_or_none()
        if tenant:
            tenant_data = {
                "id": str(tenant.id),
                "name": tenant.name,
                "document": tenant.document,
                "subscription_status": tenant.subscription_status.value,
                "terms_accepted_at": tenant.terms_accepted_at.isoformat() if tenant.terms_accepted_at else None,
                "terms_version": tenant.terms_version,
                "created_at": tenant.created_at.isoformat(),
            }

        # Record counts (mantidos para quem já lia este formato)
        for model, label in [
            (AccountingClient, "clients"),
            (ClientDocument, "documents"),
            (AccountReceivable, "receivables"),
        ]:
            try:
                count_result = await db.execute(
                    select(func.count()).select_from(model).where(
                        model.tenant_id == current_user.tenant_id
                    )
                )
                record_counts[label] = int(count_result.scalar_one() or 0)
            except Exception:
                record_counts[label] = None

        for chave, model in _modelos_exportados():
            try:
                linhas = (
                    await db.execute(select(model).where(model.tenant_id == current_user.tenant_id))
                ).scalars().all()
                dados[chave] = [_linha(obj) for obj in linhas]
            except Exception:
                logger.warning("export_tabela_falhou tabela=%s", chave, exc_info=True)
                await db.rollback()
                dados[chave] = None

    return {
        "export_generated_at": datetime.now(timezone.utc).isoformat(),
        "lgpd_basis": "Lei Geral de Proteção de Dados (LGPD) — Art. 18, Inciso I e IV",
        "user": user_data,
        "tenant": tenant_data,
        "record_counts": record_counts,
        "dados": dados,
    }


@router.post("/delete", status_code=status.HTTP_202_ACCEPTED)
async def request_account_deletion(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Request deletion of all personal data (LGPD Art. 18, Inciso VI).

    This does NOT immediately delete the account. Instead:
    1. Records the deletion request timestamp on the tenant.
    2. The FiscWise team processes the request within 15 business days.
    3. An email confirmation is sent (when email provider is configured).

    NOTE: Immediate deletion is intentionally deferred because:
    - Fiscal records must be retained for 5 years (Brazilian tax law)
    - Some data may be needed for ongoing client obligations
    - Admin review ensures the request is from an authorized party
    """
    # Only owners can request tenant deletion
    # Members and clients can request their user deletion separately (future)
    if current_user.role.value != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o proprietário da conta pode solicitar a exclusão dos dados do escritório. "
                   "Para remover seu usuário, entre em contato com o proprietário.",
        )

    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant não encontrado")

    if tenant.deletion_requested_at:
        return {
            "status": "already_requested",
            "requested_at": tenant.deletion_requested_at.isoformat(),
            "message": "Sua solicitação de exclusão já foi registrada. Nossa equipe entrará em contato.",
        }

    now_utc = datetime.now(timezone.utc)
    tenant.deletion_requested_at = now_utc
    await db.commit()

    logger.info(
        "Data deletion request submitted: tenant=%s by user=%s",
        tenant.id, current_user.email
    )

    from app.services.email_service import send_email, render_lgpd_deletion_email
    await send_email(
        to=current_user.email,
        subject="Recebemos sua solicitação de exclusão de dados — FiscWise",
        html=render_lgpd_deletion_email(),
    )

    return {
        "status": "request_received",
        "requested_at": now_utc.isoformat(),
        "message": (
            "Sua solicitação de exclusão de dados foi registrada com sucesso. "
            "Nossa equipe processará o pedido em até 15 dias úteis, conforme a LGPD. "
            "Você receberá uma confirmação por e-mail."
        ),
        "lgpd_basis": "LGPD — Art. 18, Inciso VI",
        "note": (
            "Documentos fiscais podem ser retidos por até 5 anos conforme "
            "exigência da Receita Federal (legislação tributária brasileira)."
        ),
    }
