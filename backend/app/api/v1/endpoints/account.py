"""Account management endpoints for FiscWise (LGPD compliance)

Provides data export and deletion request capabilities as required by
Brazil's Lei Geral de Proteção de Dados (LGPD, Law 13.709/2018).

Art. 18 rights implemented:
  - Right to access: GET /account/export
  - Right to erasure: POST /account/delete (generates ticket, not immediate)
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.tenant import Tenant
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/account", tags=["Account / LGPD"])


@router.get("/export")
async def export_my_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Export all personal data for the authenticated user and their tenant (LGPD Art. 18).

    Returns a structured JSON with:
    - User profile data
    - Tenant data (if owner)
    - Summary of records count (clients, documents, etc.)

    NOTE: For large exports in production, this should be an async job that
    emails the result. Current implementation returns inline for MVP.
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

        # Record counts
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

    return {
        "export_generated_at": datetime.now(timezone.utc).isoformat(),
        "lgpd_basis": "Lei Geral de Proteção de Dados (LGPD) — Art. 18, Inciso I e IV",
        "user": user_data,
        "tenant": tenant_data,
        "record_counts": record_counts,
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
