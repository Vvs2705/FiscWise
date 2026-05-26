import pytest
import uuid
from decimal import Decimal
from fastapi import HTTPException

from app.domain.invoices.repository import InvoiceRepository
from app.domain.invoices.service import InvoiceService
from app.domain.invoices.schemas import InvoiceIssuerCreate, InvoiceCreate

pytestmark = pytest.mark.unit

@pytest.mark.asyncio
async def test_invoice_cross_tenant_isolation(test_db):
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()

    repo = InvoiceRepository(test_db)
    service = InvoiceService(repo)

    # 1. Tenant A registers an issuer
    payload_a = InvoiceIssuerCreate(
        cnpj="09134865000180",
        regime_tributario="simples",
        municipio_ibge="3550308",
    )
    issuer_a = await service.create_issuer(payload_a, tenant_a)

    # 2. Tenant B lists issuers -> should NOT see Tenant A's issuer
    issuers_b = await service.list_issuers(tenant_b)
    assert len(issuers_b) == 0

    # 3. Tenant B attempts to fetch Tenant A's issuer -> should return None (404 in service/routes)
    issuer_check_b = await repo.get_issuer_by_id(issuer_a.id, tenant_b)
    assert issuer_check_b is None

    # 4. Tenant A creates an invoice
    invoice_payload = InvoiceCreate(
        issuer_id=issuer_a.id,
        competencia=date.today(),
        valor_servico=Decimal("1500.00"),
        descricao_servico="Serviços TI",
    )
    from datetime import date
    invoice_a = await service.create_invoice(invoice_payload, tenant_a)

    # 5. Tenant B tries to fetch Tenant A's invoice -> should raise 404
    with pytest.raises(HTTPException) as exc:
        await service.get_invoice(invoice_a.id, tenant_b)
    assert exc.value.status_code == 404

    # 6. Tenant B tries to queue emission of Tenant A's invoice -> should raise 404
    with pytest.raises(HTTPException) as exc:
        await service.queue_emission(invoice_a.id, tenant_b)
    assert exc.value.status_code == 404
