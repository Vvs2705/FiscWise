import pytest
from pydantic import ValidationError
from app.core.validators import validate_cpf, validate_cnpj, validate_cpf_or_cnpj
from app.schemas.operations import AccountingClientCreate, AccountingClientUpdate


def test_cpf_validation_logic():
    # Valid CPFs
    assert validate_cpf("11111111111") is False  # all equal
    assert validate_cpf("06877715608") is True   # valid generated CPF
    assert validate_cpf("66520376370") is True   # valid generated CPF
    # Invalid CPFs
    assert validate_cpf("12345678901") is False  # mathematically invalid
    assert validate_cpf("06877715607") is False
    assert validate_cpf("66520376371") is False
    assert validate_cpf("123") is False


def test_cnpj_validation_logic():
    # Valid CNPJs
    assert validate_cnpj("11111111111111") is False  # all equal
    assert validate_cnpj("76069336914468") is True    # valid CNPJ
    assert validate_cnpj("09134865420327") is True    # valid CNPJ
    # Invalid CNPJs
    assert validate_cnpj("76069336914467") is False
    assert validate_cnpj("09134865420326") is False
    assert validate_cnpj("123") is False


def test_cpf_or_cnpj_utility():
    assert validate_cpf_or_cnpj("06877715608") is True
    assert validate_cpf_or_cnpj("76069336914468") is True
    assert validate_cpf_or_cnpj("12345") is False


def test_accounting_client_validation_success():
    # Valid CPF and CNPJ
    payload = {
        "name": "Acme Inc.",
        "document": "76.069.336/9144-68",
        "entity_type": "pj",
        "email": "contact@acme.com",
        "status": "active",
        "responsible_name": "John Doe",
        "responsible_cpf": "068.777.156-08",
    }
    client = AccountingClientCreate(**payload)
    assert client.name == "Acme Inc."
    assert client.document == "76.069.336/9144-68"
    assert client.responsible_cpf == "068.777.156-08"


def test_accounting_client_validation_invalid_document():
    # Invalid CNPJ
    payload = {
        "name": "Acme Inc.",
        "document": "76.069.336/9144-67",
        "entity_type": "pj",
    }
    with pytest.raises(ValidationError) as exc_info:
        AccountingClientCreate(**payload)
    assert "Invalid CPF or CNPJ document" in str(exc_info.value)


def test_accounting_client_validation_invalid_responsible_cpf():
    # Invalid responsible CPF
    payload = {
        "name": "Acme Inc.",
        "document": "76.069.336/9144-68",
        "entity_type": "pj",
        "responsible_cpf": "068.777.156-07",
    }
    with pytest.raises(ValidationError) as exc_info:
        AccountingClientCreate(**payload)
    assert "Invalid CPF for responsible person" in str(exc_info.value)
