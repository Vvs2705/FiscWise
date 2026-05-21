"""Pydantic schemas for FiscWise operational MVP endpoints."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


ClientStatus = Literal["active", "inactive", "onboarding"]
EntityType = Literal["pj", "pf"]
DeadlineStatus = Literal["pending", "completed", "overdue", "cancelled"]
DeadlinePriority = Literal["low", "medium", "high"]
DocumentStatus = Literal["available", "missing", "expired", "review"]
CertificateStatus = Literal["valid", "expiring", "expired", "revoked"]
ReceivableStatus = Literal["pending", "paid", "overdue", "cancelled"]


class AccountingClientCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    document: Optional[str] = Field(None, max_length=32)
    entity_type: EntityType = "pj"
    tax_regime: Optional[str] = Field(None, max_length=80)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=40)
    municipal_registration: Optional[str] = Field(None, max_length=80)
    state_registration: Optional[str] = Field(None, max_length=80)
    status: ClientStatus = "active"
    notes: Optional[str] = None


class AccountingClientUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    document: Optional[str] = Field(None, max_length=32)
    entity_type: Optional[EntityType] = None
    tax_regime: Optional[str] = Field(None, max_length=80)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=40)
    municipal_registration: Optional[str] = Field(None, max_length=80)
    state_registration: Optional[str] = Field(None, max_length=80)
    status: Optional[ClientStatus] = None
    notes: Optional[str] = None


class AccountingClientResponse(AccountingClientCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


class DeadlineCreate(BaseModel):
    client_id: UUID
    title: str = Field(..., min_length=2, max_length=255)
    category: str = Field(default="fiscal", max_length=80)
    due_date: date
    status: DeadlineStatus = "pending"
    priority: DeadlinePriority = "medium"
    description: Optional[str] = None


class DeadlineUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    category: Optional[str] = Field(None, max_length=80)
    due_date: Optional[date] = None
    status: Optional[DeadlineStatus] = None
    priority: Optional[DeadlinePriority] = None
    description: Optional[str] = None
    completed_at: Optional[datetime] = None


class DeadlineResponse(DeadlineCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class DocumentCreate(BaseModel):
    client_id: UUID
    name: str = Field(..., min_length=2, max_length=255)
    document_type: str = Field(default="other", max_length=80)
    status: DocumentStatus = "available"
    file_url: Optional[str] = Field(None, max_length=1024)
    issued_at: Optional[date] = None
    expires_at: Optional[date] = None
    notes: Optional[str] = None


class DocumentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    document_type: Optional[str] = Field(None, max_length=80)
    status: Optional[DocumentStatus] = None
    file_url: Optional[str] = Field(None, max_length=1024)
    issued_at: Optional[date] = None
    expires_at: Optional[date] = None
    notes: Optional[str] = None


class DocumentResponse(DocumentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


class CertificateCreate(BaseModel):
    client_id: UUID
    label: str = Field(..., min_length=2, max_length=255)
    certificate_type: str = Field(default="a1", max_length=16)
    valid_from: Optional[date] = None
    valid_until: date
    status: CertificateStatus = "valid"
    notes: Optional[str] = None


class CertificateUpdate(BaseModel):
    label: Optional[str] = Field(None, min_length=2, max_length=255)
    certificate_type: Optional[str] = Field(None, max_length=16)
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    status: Optional[CertificateStatus] = None
    notes: Optional[str] = None


class CertificateResponse(CertificateCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


class ReceivableCreate(BaseModel):
    client_id: UUID
    description: str = Field(..., min_length=2, max_length=255)
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    due_date: date
    status: ReceivableStatus = "pending"
    paid_at: Optional[datetime] = None
    notes: Optional[str] = None


class ReceivableUpdate(BaseModel):
    description: Optional[str] = Field(None, min_length=2, max_length=255)
    amount: Optional[Decimal] = Field(None, gt=0, max_digits=12, decimal_places=2)
    due_date: Optional[date] = None
    status: Optional[ReceivableStatus] = None
    paid_at: Optional[datetime] = None
    notes: Optional[str] = None


class ReceivableResponse(ReceivableCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


class MonthlyData(BaseModel):
    """Receita agrupada por mes (para grafico de tendencia)."""

    mes: str       # "Jan", "Fev", etc.
    valor: Decimal


class DailyData(BaseModel):
    """Receita agrupada por dia da semana (ultimos 7 dias)."""

    dia: str       # "Seg", "Ter", etc.
    receita: Decimal


class ReceivableWithClient(BaseModel):
    """Recebivel enriquecido com nome do cliente (para tabela de transacoes)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    client_name: str
    description: str
    amount: Decimal
    due_date: date
    status: ReceivableStatus
    paid_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class DashboardOverview(BaseModel):
    active_clients: int
    pending_deadlines: int
    overdue_deadlines: int
    certificates_expiring_30d: int
    open_receivables: int
    overdue_receivables: int
    receivables_amount_open: Decimal
    receivables_amount_overdue: Decimal
    upcoming_deadlines: list[DeadlineResponse]
    # Dados financeiros reais
    total_received_month: Decimal
    monthly_received: list[MonthlyData]
    weekly_received: list[DailyData]
    recent_receivables: list[ReceivableWithClient]

