"""Builds the fiscal mailbox provider selected by FISCAL_MAILBOX_PROVIDER.

``mock`` (default) keeps the deterministic provider; ``serpro`` wires the
Integra Contador client with the tenant's active accounting clients as
contribuintes. Fail-closed: an unknown or under-configured provider raises
``ProviderNotConfiguredError`` so the API can answer 503 instead of silently
syncing fake data in production.
"""

import uuid

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.operations import AccountingClient
from app.domain.fiscal_mailbox.integrations.base import (
    FiscalMailboxProvider,
    ProviderNotConfiguredError,
)
from app.domain.fiscal_mailbox.integrations.mock import MockFiscalMailboxProvider
from app.domain.fiscal_mailbox.integrations.serpro import SerproIntegraContadorProvider


async def build_fiscal_mailbox_provider(
    db: AsyncSession, tenant_id: uuid.UUID
) -> FiscalMailboxProvider:
    name = (settings.FISCAL_MAILBOX_PROVIDER or "mock").strip().lower()

    if name == "mock":
        return MockFiscalMailboxProvider()

    if name == "serpro":
        if not settings.SERPRO_CONSUMER_KEY or not settings.SERPRO_CONSUMER_SECRET:
            raise ProviderNotConfiguredError(
                "FISCAL_MAILBOX_PROVIDER=serpro requires SERPRO_CONSUMER_KEY and "
                "SERPRO_CONSUMER_SECRET secrets"
            )
        if not settings.SERPRO_CONTRATANTE_CNPJ or not settings.SERPRO_AUTOR_PEDIDO_CNPJ:
            raise ProviderNotConfiguredError(
                "FISCAL_MAILBOX_PROVIDER=serpro requires SERPRO_CONTRATANTE_CNPJ and "
                "SERPRO_AUTOR_PEDIDO_CNPJ"
            )

        result = await db.execute(
            select(AccountingClient).where(
                and_(
                    AccountingClient.tenant_id == tenant_id,
                    AccountingClient.status == "active",
                )
            )
        )
        contribuintes = [
            {"cnpj": client.document, "name": client.name}
            for client in result.scalars().all()
            if client.document
        ]

        cert = None
        if settings.SERPRO_CERT_PATH:
            cert = (
                (settings.SERPRO_CERT_PATH, settings.SERPRO_CERT_KEY_PATH)
                if settings.SERPRO_CERT_KEY_PATH
                else settings.SERPRO_CERT_PATH
            )

        return SerproIntegraContadorProvider(
            contribuintes,
            consumer_key=settings.SERPRO_CONSUMER_KEY,
            consumer_secret=settings.SERPRO_CONSUMER_SECRET,
            auth_url=settings.SERPRO_AUTH_URL,
            base_url=settings.SERPRO_INTEGRA_BASE_URL,
            contratante_cnpj=settings.SERPRO_CONTRATANTE_CNPJ,
            autor_pedido_cnpj=settings.SERPRO_AUTOR_PEDIDO_CNPJ,
            cert=cert,
            timeout=settings.SERPRO_TIMEOUT_SECONDS,
        )

    raise ProviderNotConfiguredError(f"Unknown FISCAL_MAILBOX_PROVIDER: {name}")
