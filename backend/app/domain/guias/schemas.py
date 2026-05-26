import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class TaxGuideCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    client_id: uuid.UUID
    tipo: str = Field(..., min_length=2, max_length=20)  # DAS, DARF, GPS, ISS, outro
    competencia: date
    valor: Decimal = Field(..., gt=0)
    vencimento: date


class TaxGuideUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    tipo: Optional[str] = Field(None, min_length=2, max_length=20)
    competencia: Optional[date] = None
    valor: Optional[Decimal] = Field(None, gt=0)
    vencimento: Optional[date] = None
    status: Optional[str] = Field(None, max_length=20)  # pendente | enviada | paga | atrasada


class TaxGuideResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    client_id: Optional[uuid.UUID]
    tipo: str
    competencia: date
    valor: Decimal
    vencimento: date
    status: str
    pdf_storage_path: Optional[str]
    comprovante_storage_path: Optional[str]
    enviada_em: Optional[datetime]
    paga_em: Optional[datetime]
    created_at: datetime
