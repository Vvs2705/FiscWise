"""Guarda de ownership entre escritórios para IDs vindos do payload."""

import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def ensure_client_in_tenant(
    db: AsyncSession, tenant_id: uuid.UUID, client_id: Optional[uuid.UUID]
) -> None:
    """404 se o client_id do payload não for um cliente deste escritório.

    Sem isso, criar guia/nota/procuração/obrigação com o UUID de um cliente de
    outro escritório gravava a referência cruzada.
    """
    if client_id is None:
        return
    from app.models.operations import AccountingClient

    found = await db.scalar(
        select(AccountingClient.id).where(
            AccountingClient.id == client_id, AccountingClient.tenant_id == tenant_id
        )
    )
    if found is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Client not found"
        )
