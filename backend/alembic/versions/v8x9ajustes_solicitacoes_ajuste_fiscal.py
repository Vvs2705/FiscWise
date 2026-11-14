"""Solicitações de ajuste fiscal, ajustes do calendário, arquivos na base de conhecimento.

- fiscal_adjustment_requests: o escritório pede um ajuste (feriado, prazo, nova
  obrigação, outro). Feriado e prazo valem na hora só para ele; tudo entra na
  fila da equipe FiscWise.
- fiscal_calendar_adjustments: feriados e prazos que o motor aplica.
  tenant_id NULL = regra geral, sempre limitada à UF/município da regra.
- rag_documents: arquivo original (file_path, file_name, file_mime, file_size).
- users.equipe_fiscwise: quem analisa as solicitações de todos os escritórios.

RLS com FORCE (a API conecta como dono das tabelas; ver u7w8forcerls):
- requests: só o próprio escritório; sem contexto (rotinas e equipe) vê tudo.
- calendar_adjustments: o escritório lê os seus e os gerais; grava só os seus
  (regra geral só sem contexto, pela equipe).

Revision ID: v8x9ajustes
Revises: u7w8forcerls
Create Date: 2026-11-14
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "v8x9ajustes"
down_revision = "u7w8forcerls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fiscal_adjustment_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("uf", sa.String(2), nullable=False),
        sa.Column("municipio_ibge", sa.String(7), nullable=True),
        sa.Column("municipio_nome", sa.String(120), nullable=True),
        sa.Column("data", sa.Date(), nullable=True),
        sa.Column("recorrente_anual", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("obrigacao_code", sa.String(50), nullable=True),
        sa.Column("due_day", sa.Integer(), nullable=True),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("fonte", sa.Text(), nullable=True),
        sa.Column("knowledge_doc_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("rag_documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("resposta_equipe", sa.Text(), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "tipo IN ('feriado','prazo','nova_obrigacao','outro')", name="ck_fiscal_adj_req_tipo"
        ),
        sa.CheckConstraint(
            "status IN ('aplicada_no_escritorio','em_analise','regra_geral','recusada')",
            name="ck_fiscal_adj_req_status",
        ),
    )
    op.create_index("ix_fiscal_adj_req_tenant_id", "fiscal_adjustment_requests", ["tenant_id"])
    op.create_index("ix_fiscal_adj_req_status", "fiscal_adjustment_requests", ["status"])
    op.create_index("ix_fiscal_adj_req_uf", "fiscal_adjustment_requests", ["uf"])

    op.create_table(
        "fiscal_calendar_adjustments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("uf", sa.String(2), nullable=False),
        sa.Column("municipio_ibge", sa.String(7), nullable=True),
        sa.Column("mes", sa.Integer(), nullable=True),
        sa.Column("dia", sa.Integer(), nullable=True),
        sa.Column("ano", sa.Integer(), nullable=True),
        sa.Column("nome", sa.String(200), nullable=True),
        sa.Column("obrigacao_code", sa.String(50), nullable=True),
        sa.Column("due_day", sa.Integer(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("origem_request_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("fiscal_adjustment_requests.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("tipo IN ('feriado','prazo')", name="ck_fiscal_cal_adj_tipo"),
    )
    op.create_index("ix_fiscal_cal_adj_tenant_id", "fiscal_calendar_adjustments", ["tenant_id"])
    op.create_index("ix_fiscal_cal_adj_uf", "fiscal_calendar_adjustments", ["uf"])

    op.execute("ALTER TABLE fiscal_adjustment_requests ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE fiscal_adjustment_requests FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON fiscal_adjustment_requests
            USING ((tenant_id = current_app_tenant_id()) OR (current_app_tenant_id() IS NULL))
            WITH CHECK ((tenant_id = current_app_tenant_id()) OR (current_app_tenant_id() IS NULL))
        """
    )
    op.execute("ALTER TABLE fiscal_calendar_adjustments ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE fiscal_calendar_adjustments FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON fiscal_calendar_adjustments
            USING ((tenant_id = current_app_tenant_id()) OR (tenant_id IS NULL)
                   OR (current_app_tenant_id() IS NULL))
            WITH CHECK ((tenant_id = current_app_tenant_id()) OR (current_app_tenant_id() IS NULL))
        """
    )

    op.add_column("rag_documents", sa.Column("file_path", sa.String(1024), nullable=True))
    op.add_column("rag_documents", sa.Column("file_name", sa.String(255), nullable=True))
    op.add_column("rag_documents", sa.Column("file_mime", sa.String(120), nullable=True))
    op.add_column("rag_documents", sa.Column("file_size", sa.Integer(), nullable=True))

    op.add_column(
        "users",
        sa.Column("equipe_fiscwise", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("users", "equipe_fiscwise")
    for col in ("file_size", "file_mime", "file_name", "file_path"):
        op.drop_column("rag_documents", col)
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON fiscal_calendar_adjustments")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON fiscal_adjustment_requests")
    op.drop_index("ix_fiscal_cal_adj_uf", table_name="fiscal_calendar_adjustments")
    op.drop_index("ix_fiscal_cal_adj_tenant_id", table_name="fiscal_calendar_adjustments")
    op.drop_table("fiscal_calendar_adjustments")
    op.drop_index("ix_fiscal_adj_req_uf", table_name="fiscal_adjustment_requests")
    op.drop_index("ix_fiscal_adj_req_status", table_name="fiscal_adjustment_requests")
    op.drop_index("ix_fiscal_adj_req_tenant_id", table_name="fiscal_adjustment_requests")
    op.drop_table("fiscal_adjustment_requests")
