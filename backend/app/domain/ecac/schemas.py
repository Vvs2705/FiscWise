import uuid
from datetime import date, datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, ConfigDict, Field

class EcacProxyCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    client_id: Optional[uuid.UUID] = None
    outorgante_cpf_cnpj: str = Field(..., min_length=11, max_length=14)
    outorgante_nome: Optional[str] = Field(None, max_length=255)
    procurador_cpf: str = Field(..., min_length=11, max_length=11)
    tipo: Optional[str] = Field("e-CAC", max_length=50)
    servicos_autorizados: Optional[List[str]] = []
    data_inicio: Optional[date] = None
    data_validade: Optional[date] = None


class EcacProxyUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    outorgante_cpf_cnpj: Optional[str] = Field(None, min_length=11, max_length=14)
    outorgante_nome: Optional[str] = Field(None, max_length=255)
    procurador_cpf: Optional[str] = Field(None, min_length=11, max_length=11)
    tipo: Optional[str] = Field(None, max_length=50)
    servicos_autorizados: Optional[List[str]] = None
    data_inicio: Optional[date] = None
    data_validade: Optional[date] = None
    status: Optional[str] = Field(None, max_length=20)


class EcacProxyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    client_id: Optional[uuid.UUID]
    outorgante_cpf_cnpj: str
    outorgante_nome: Optional[str]
    procurador_cpf: str
    tipo: Optional[str]
    servicos_autorizados: Optional[List[str]]
    data_inicio: Optional[date]
    data_validade: Optional[date]
    status: str
    ultima_verificacao: Optional[datetime]
    created_at: datetime


class EcacFiscalSituationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    client_id: Optional[uuid.UUID]
    cpf_cnpj: str
    status_geral: Optional[str]
    pendencias: Optional[List[Any]]
    debitos: Optional[List[Any]]
    certidao_status: Optional[str]
    certidao_validade: Optional[date]
    consultado_em: datetime
