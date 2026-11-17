"""Cofre de certificados A1 (ICP-Brasil) para emissão de NFS-e.

O escritório envia o .pfx/.p12 e a senha; guardamos os dois CIFRADOS
(AES-256-GCM, cofre.py) e só os metadados lidos do próprio certificado ficam
em claro. Escopo:
- 'escritorio': certificado do escritório, usado como procurador (procuração
  eletrônica da Receita) para emitir em nome dos clientes;
- 'cliente': certificado da própria empresa emissora (client_id obrigatório).

O status 'vencido' é calculado na leitura (`status_efetivo`); no banco ficam
'valido' | 'bloqueado' | 'revogado'.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    UUID as SQLUUID,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantBase

ESCOPO_ESCRITORIO = "escritorio"
ESCOPO_CLIENTE = "cliente"
ESCOPOS = (ESCOPO_ESCRITORIO, ESCOPO_CLIENTE)

STATUS_VALIDO = "valido"
STATUS_VENCIDO = "vencido"
STATUS_BLOQUEADO = "bloqueado"
STATUS_REVOGADO = "revogado"


class CertificadoA1(Base, TenantBase):
    __tablename__ = "certificados_a1"
    __table_args__ = (
        CheckConstraint("escopo IN ('escritorio','cliente')", name="ck_cert_a1_escopo"),
        CheckConstraint("status IN ('valido','bloqueado','revogado')", name="ck_cert_a1_status"),
        CheckConstraint(
            "(escopo = 'cliente' AND client_id IS NOT NULL) OR (escopo = 'escritorio' AND client_id IS NULL)",
            name="ck_cert_a1_escopo_cliente",
        ),
        Index("uq_cert_a1_tenant_thumbprint", "tenant_id", "thumbprint_sha256", unique=True),
    )

    escopo: Mapped[str] = mapped_column(String(20), nullable=False)
    client_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("accounting_clients.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    titular_nome: Mapped[str] = mapped_column(String(255), nullable=False)
    documento: Mapped[Optional[str]] = mapped_column(String(14), nullable=True)
    tipo_documento: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)  # cnpj | cpf
    emissor: Mapped[str] = mapped_column(String(255), nullable=False)
    numero_serie: Mapped[str] = mapped_column(String(80), nullable=False)
    thumbprint_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    valido_de: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valido_ate: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    # Conteúdo sensível: nunca sai em API, log ou exportação (o regex de
    # exportação LGPD exclui colunas com "pfx", "senha", "cifr"...).
    pfx_cifrado: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    senha_cifrada: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    chave_versao: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=STATUS_VALIDO,
                                        server_default=STATUS_VALIDO)
    motivo_bloqueio: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ultimo_uso: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    criado_por_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    def status_efetivo(self, agora: datetime) -> str:
        if self.status != STATUS_VALIDO:
            return self.status
        fim = self.valido_ate
        if fim.tzinfo is None:  # SQLite devolve sem fuso
            from datetime import timezone

            fim = fim.replace(tzinfo=timezone.utc)
        return STATUS_VENCIDO if fim <= agora else STATUS_VALIDO
