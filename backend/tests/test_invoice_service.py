import pytest
import uuid
from datetime import date, timedelta
from decimal import Decimal
from fastapi import HTTPException
from pydantic import ValidationError

from app.domain.invoices.models import Invoice, InvoiceIssuer
from app.domain.invoices.repository import InvoiceRepository
from app.domain.invoices.service import InvoiceService
from app.domain.invoices.schemas import InvoiceIssuerCreate, InvoiceCreate
from app.domain.invoices.providers.mock import MockNfseProvider

# Mark all tests in this file as unit tests
pytestmark = pytest.mark.unit

@pytest.mark.asyncio
async def test_validate_cpf_cnpj():
    from app.domain.invoices.validators import validate_cpf_cnpj
    # Test valid generated values
    assert validate_cpf_cnpj("10000000019") is True  # Valid CPF
    assert validate_cpf_cnpj("10000000000145") is True # Valid CNPJ
    # Test invalid check digits
    assert validate_cpf_cnpj("11111111111") is False # Invalid CPF
    assert validate_cpf_cnpj("11111111111111") is False # Invalid CNPJ
    assert validate_cpf_cnpj("123") is False

@pytest.mark.asyncio
async def test_create_issuer_success(test_db):
    tenant_id = uuid.uuid4()
    repo = InvoiceRepository(test_db)
    service = InvoiceService(repo)

    payload = InvoiceIssuerCreate(
        cnpj="10000000000145",
        inscricao_municipal="12345",
        regime_tributario="simples",
        municipio_ibge="3550308",
        cod_servico_lc116="01.01",
        aliquota_iss=Decimal("0.02"),
        retencao_iss=False
    )

    issuer = await service.create_issuer(payload, tenant_id)
    assert issuer.id is not None
    assert issuer.tenant_id == tenant_id
    assert issuer.cnpj == "10000000000145"

@pytest.mark.asyncio
async def test_create_issuer_duplicate_error(test_db):
    tenant_id = uuid.uuid4()
    repo = InvoiceRepository(test_db)
    service = InvoiceService(repo)

    payload = InvoiceIssuerCreate(
        cnpj="10000000000145",
        regime_tributario="simples",
        municipio_ibge="3550308",
    )

    await service.create_issuer(payload, tenant_id)
    
    with pytest.raises(HTTPException) as exc:
        await service.create_issuer(payload, tenant_id)
    assert exc.value.status_code == 400

@pytest.mark.asyncio
async def test_create_invoice_validation(test_db):
    tenant_id = uuid.uuid4()
    repo = InvoiceRepository(test_db)
    service = InvoiceService(repo)

    # First, create issuer
    issuer = await service.create_issuer(
        InvoiceIssuerCreate(cnpj="10000000000145", regime_tributario="simples", municipio_ibge="3550308"),
        tenant_id
    )

    # 1. Invalid length triggers Pydantic validation error
    with pytest.raises(ValidationError):
        InvoiceCreate(
            issuer_id=issuer.id,
            competencia=date.today(),
            valor_servico=Decimal("150.00"),
            descricao_servico="Serviço de teste",
            tomador_cpf_cnpj="12345",  # Too short
        )

    # 2. Mathematically invalid check digits but correct length triggers HTTPException
    payload = InvoiceCreate(
        issuer_id=issuer.id,
        competencia=date.today(),
        valor_servico=Decimal("150.00"),
        descricao_servico="Serviço de teste",
        tomador_cpf_cnpj="11111111111",  # Correct length, invalid digits
    )
    with pytest.raises(HTTPException) as exc:
        await service.create_invoice(payload, tenant_id)
    assert "Invalid CPF or CNPJ" in exc.value.detail

    # 3. Valor <= 0 triggers Pydantic validation error
    with pytest.raises(ValidationError):
        InvoiceCreate(
            issuer_id=issuer.id,
            competencia=date.today(),
            valor_servico=Decimal("-50.00"),
            descricao_servico="Serviço de teste",
        )

    # 4. Future competency
    future_date = date.today() + timedelta(days=40)
    payload = InvoiceCreate(
        issuer_id=issuer.id,
        competencia=future_date,
        valor_servico=Decimal("100.00"),
        descricao_servico="Serviço de teste",
    )
    with pytest.raises(HTTPException) as exc:
        await service.create_invoice(payload, tenant_id)
    assert "cannot be a future month" in exc.value.detail

@pytest.mark.asyncio
async def test_invoice_emission_state_machine_and_provider(test_db):
    tenant_id = uuid.uuid4()
    repo = InvoiceRepository(test_db)
    service = InvoiceService(repo)
    provider = MockNfseProvider()

    # 1. Create issuer and invoice
    issuer = await service.create_issuer(
        InvoiceIssuerCreate(cnpj="10000000000145", regime_tributario="simples", municipio_ibge="3550308"),
        tenant_id
    )
    payload = InvoiceCreate(
        issuer_id=issuer.id,
        competencia=date.today(),
        valor_servico=Decimal("500.00"),
        descricao_servico="Consultoria Tributária",
        tomador_cpf_cnpj="10000000019", # Valid CPF
    )
    invoice = await service.create_invoice(payload, tenant_id)
    assert invoice.status == "draft"

    # 2. Queue emission
    invoice = await service.queue_emission(invoice.id, tenant_id)
    assert invoice.status == "queued"

    # 3. Process emission
    invoice = await service.process_emission_sync(invoice.id, tenant_id, provider)
    assert invoice.status == "issued"
    assert invoice.numero == "1"
    assert invoice.provider_protocol is not None
    assert invoice.xml_content is not None
    assert invoice.pdf_storage_path is not None

    # 4. Cancel invoice
    invoice = await service.cancel_invoice(invoice.id, tenant_id, "Erro no preenchimento", provider)
    assert invoice.status == "cancelled"
    assert invoice.cancelled_at is not None

@pytest.mark.asyncio
async def test_invoice_emission_rejected(test_db):
    tenant_id = uuid.uuid4()
    repo = InvoiceRepository(test_db)
    service = InvoiceService(repo)
    provider = MockNfseProvider()

    issuer = await service.create_issuer(
        InvoiceIssuerCreate(cnpj="10000000000145", regime_tributario="simples", municipio_ibge="3550308"),
        tenant_id
    )
    payload = InvoiceCreate(
        issuer_id=issuer.id,
        competencia=date.today(),
        valor_servico=Decimal("500.00"),
        descricao_servico="Consultoria fail_validation",  # Will trigger mock validation fail
    )
    invoice = await service.create_invoice(payload, tenant_id)
    invoice = await service.queue_emission(invoice.id, tenant_id)
    invoice = await service.process_emission_sync(invoice.id, tenant_id, provider)

    assert invoice.status == "rejected"
    rejections = await repo.list_rejections(invoice.id, tenant_id)
    assert len(rejections) == 1
    assert rejections[0].codigo_rejeicao == "E001"
