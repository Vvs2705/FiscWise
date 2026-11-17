"""Cofre de certificados A1 e configuração da emissão de NFS-e por emissor.

- certificados_a1: .pfx e senha CIFRADOS (AES-256-GCM, app/domain/certificados/
  cofre.py) + metadados lidos do certificado. Escopo 'escritorio' (procurador)
  ou 'cliente' (empresa emissora).
- invoice_issuers: modo_certificado ('proprio'|'procuracao'), certificado_id,
  procuracao_confirmada_em, o resultado do último teste de emissão e
  ultimo_numero_dps (sequência da DPS do emissor).
- invoices: numero_dps + serie_dps reservados antes de transmitir (únicos por
  emissor + série).

RLS com FORCE (a API conecta como dono das tabelas; ver u7w8forcerls): só o
próprio escritório; sem contexto (rotinas do sistema) vê tudo.

Revision ID: x0a1certificados
Revises: w9y0exclusao
Create Date: 2026-11-17
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "x0a1certificados"
down_revision = "w9y0exclusao"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "certificados_a1",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("escopo", sa.String(20), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("accounting_clients.id", ondelete="CASCADE"), nullable=True),
        sa.Column("titular_nome", sa.String(255), nullable=False),
        sa.Column("documento", sa.String(14), nullable=True),
        sa.Column("tipo_documento", sa.String(4), nullable=True),
        sa.Column("emissor", sa.String(255), nullable=False),
        sa.Column("numero_serie", sa.String(80), nullable=False),
        sa.Column("thumbprint_sha256", sa.String(64), nullable=False),
        sa.Column("valido_de", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valido_ate", sa.DateTime(timezone=True), nullable=False),
        sa.Column("pfx_cifrado", sa.LargeBinary(), nullable=False),
        sa.Column("senha_cifrada", sa.LargeBinary(), nullable=False),
        sa.Column("chave_versao", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="valido"),
        sa.Column("motivo_bloqueio", sa.String(255), nullable=True),
        sa.Column("ultimo_uso", sa.DateTime(timezone=True), nullable=True),
        sa.Column("criado_por_user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("escopo IN ('escritorio','cliente')", name="ck_cert_a1_escopo"),
        sa.CheckConstraint("status IN ('valido','bloqueado','revogado')", name="ck_cert_a1_status"),
        sa.CheckConstraint(
            "(escopo = 'cliente' AND client_id IS NOT NULL) OR (escopo = 'escritorio' AND client_id IS NULL)",
            name="ck_cert_a1_escopo_cliente",
        ),
    )
    op.create_index("ix_certificados_a1_tenant_id", "certificados_a1", ["tenant_id"])
    op.create_index("ix_certificados_a1_client_id", "certificados_a1", ["client_id"])
    op.create_index("ix_certificados_a1_valido_ate", "certificados_a1", ["valido_ate"])
    op.create_index(
        "uq_cert_a1_tenant_thumbprint", "certificados_a1", ["tenant_id", "thumbprint_sha256"], unique=True
    )

    op.execute("ALTER TABLE certificados_a1 ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE certificados_a1 FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON certificados_a1
            USING ((tenant_id = current_app_tenant_id()) OR (current_app_tenant_id() IS NULL))
            WITH CHECK ((tenant_id = current_app_tenant_id()) OR (current_app_tenant_id() IS NULL))
        """
    )

    op.add_column("invoice_issuers", sa.Column("modo_certificado", sa.String(20), nullable=True))
    op.add_column(
        "invoice_issuers",
        sa.Column("certificado_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("certificados_a1.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column("invoice_issuers", sa.Column("procuracao_confirmada_em", sa.DateTime(timezone=True), nullable=True))
    op.add_column("invoice_issuers", sa.Column("ultimo_teste_em", sa.DateTime(timezone=True), nullable=True))
    op.add_column("invoice_issuers", sa.Column("ultimo_teste_ok", sa.Boolean(), nullable=True))
    op.add_column("invoice_issuers", sa.Column("ultimo_teste_mensagem", sa.Text(), nullable=True))
    op.add_column(
        "invoice_issuers",
        sa.Column("ultimo_numero_dps", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("invoices", sa.Column("numero_dps", sa.Integer(), nullable=True))
    op.add_column("invoices", sa.Column("serie_dps", sa.String(5), nullable=True))
    op.create_index(
        "uq_invoices_issuer_serie_numero_dps",
        "invoices",
        ["issuer_id", "serie_dps", "numero_dps"],
        unique=True,
        postgresql_where=sa.text("numero_dps IS NOT NULL"),
    )
    op.create_check_constraint(
        "ck_invoice_issuers_modo_certificado",
        "invoice_issuers",
        "modo_certificado IS NULL OR modo_certificado IN ('proprio','procuracao')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_invoice_issuers_modo_certificado", "invoice_issuers", type_="check")
    op.execute("DROP INDEX IF EXISTS uq_invoices_issuer_serie_numero_dps")
    op.execute("ALTER TABLE invoices DROP COLUMN IF EXISTS serie_dps")
    op.execute("ALTER TABLE invoices DROP COLUMN IF EXISTS numero_dps")
    op.execute("ALTER TABLE invoice_issuers DROP COLUMN IF EXISTS ultimo_numero_dps")
    op.drop_column("invoice_issuers", "ultimo_teste_mensagem")
    op.drop_column("invoice_issuers", "ultimo_teste_ok")
    op.drop_column("invoice_issuers", "ultimo_teste_em")
    op.drop_column("invoice_issuers", "procuracao_confirmada_em")
    op.drop_column("invoice_issuers", "certificado_id")
    op.drop_column("invoice_issuers", "modo_certificado")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON certificados_a1")
    op.drop_index("uq_cert_a1_tenant_thumbprint", table_name="certificados_a1")
    op.drop_index("ix_certificados_a1_valido_ate", table_name="certificados_a1")
    op.drop_index("ix_certificados_a1_client_id", table_name="certificados_a1")
    op.drop_index("ix_certificados_a1_tenant_id", table_name="certificados_a1")
    op.drop_table("certificados_a1")
