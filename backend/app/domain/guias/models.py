import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, UUID as SQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantBase

class TaxGuide(Base, TenantBase):
    """Record of a tax guide (guia de impostos) for a client."""
    __tablename__ = "tax_guides"

    client_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("accounting_clients.id", ondelete="SET NULL"),
        nullable=True,
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)  # 'DAS' | 'DARF' | 'GPS' | 'ISS' | 'outro'
    competencia: Mapped[date] = mapped_column(Date, nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    vencimento: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pendente", server_default="pendente")
    
    pdf_storage_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    comprovante_storage_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    enviada_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    paga_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    client = relationship("AccountingClient", lazy="joined")
