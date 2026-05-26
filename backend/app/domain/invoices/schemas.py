import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field, EmailStr

class InvoiceIssuerCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    client_id: Optional[uuid.UUID] = None
    cnpj: str = Field(..., min_length=14, max_length=14, pattern=r"^\d{14}$")
    inscricao_municipal: Optional[str] = Field(None, max_length=50)
    regime_tributario: str = Field(..., max_length=20)  # simples | lucro_presumido | lucro_real
    municipio_ibge: str = Field(..., min_length=7, max_length=7, pattern=r"^\d{7}$")
    cod_servico_lc116: Optional[str] = Field(None, max_length=10)
    aliquota_iss: Optional[Decimal] = Field(None, ge=0, le=1)
    retencao_iss: bool = False


class InvoiceIssuerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    client_id: Optional[uuid.UUID]
    cnpj: str
    inscricao_municipal: Optional[str]
    regime_tributario: str
    municipio_ibge: str
    cod_servico_lc116: Optional[str]
    aliquota_iss: Optional[Decimal]
    retencao_iss: bool
    created_at: datetime
    updated_at: datetime


class InvoiceCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    issuer_id: uuid.UUID
    client_id: Optional[uuid.UUID] = None
    competencia: date
    valor_servico: Decimal = Field(..., gt=0)
    valor_deducoes: Decimal = Field(default=Decimal("0.00"), ge=0)
    valor_iss: Optional[Decimal] = Field(None, ge=0)
    descricao_servico: str = Field(..., min_length=5)
    tomador_nome: Optional[str] = Field(None, max_length=255)
    tomador_cpf_cnpj: Optional[str] = Field(None, min_length=11, max_length=14)
    tomador_email: Optional[EmailStr] = None
    tomador_municipio_ibge: Optional[str] = Field(None, min_length=7, max_length=7, pattern=r"^\d{7}$")
    billing_charge_id: Optional[uuid.UUID] = None


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    issuer_id: uuid.UUID
    client_id: Optional[uuid.UUID]
    status: str
    numero: Optional[str]
    serie: Optional[str]
    competencia: date
    valor_servico: Decimal
    valor_deducoes: Decimal
    valor_iss: Optional[Decimal]
    descricao_servico: str
    tomador_nome: Optional[str]
    tomador_cpf_cnpj: Optional[str]
    tomador_email: Optional[str]
    tomador_municipio_ibge: Optional[str]
    provider_protocol: Optional[str]
    provider_response: Optional[Dict[str, Any]]
    xml_content: Optional[str]
    pdf_storage_path: Optional[str]
    xml_storage_path: Optional[str]
    billing_charge_id: Optional[uuid.UUID]
    issued_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class InvoiceEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invoice_id: uuid.UUID
    tenant_id: uuid.UUID
    event_type: str
    payload: Optional[Dict[str, Any]]
    created_at: datetime


class InvoiceRejectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invoice_id: uuid.UUID
    tenant_id: uuid.UUID
    codigo_rejeicao: Optional[str]
    descricao: str
    raw_response: Optional[Dict[str, Any]]
    created_at: datetime


class InvoiceEmitRequest(BaseModel):
    pass


class InvoiceCancelRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    reason: str = Field(..., min_length=5, max_length=255)
