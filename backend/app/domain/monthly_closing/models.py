import uuid
from datetime import datetime
from typing import Optional, Any, List

from sqlalchemy import DateTime, ForeignKey, Integer, String, UUID as SQLUUID, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantBase


class MonthlyClosing(Base, TenantBase):
    """Monthly closing pipeline for one client in one competence (YYYY-MM).

    The checklist is stored as a JSONB list of items
    (``{id, label, status, notes, completed_at}``) because items are a fixed
    template per closing and are always read/written as a whole.
    """

    __tablename__ = "monthly_closings"

    __table_args__ = (
        UniqueConstraint("tenant_id", "client_id", "competence", name="uq_monthly_closing_client_competence"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("accounting_clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    competence: Mapped[str] = mapped_column(String(7), nullable=False, index=True)  # YYYY-MM

    status: Mapped[str] = mapped_column(String(20), default="not_started", server_default="not_started", nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)

    blockers: Mapped[Optional[List[Any]]] = mapped_column(JSONB, nullable=True, default=list)
    checklist: Mapped[Optional[List[Any]]] = mapped_column(JSONB, nullable=True, default=list)

    invoices_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    invoices_pending: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    guides_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    guides_paid: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    obligations_total: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    obligations_done: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    ecac_pendencies: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    documents_total: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    documents_received: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)

    dossier_generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    client = relationship("AccountingClient", lazy="joined")
