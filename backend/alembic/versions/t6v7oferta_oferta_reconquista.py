"""Oferta de reconquista pós-teste e descadastro de e-mails de oferta.

- retention_offers: uma oferta por escritório (15% no 1º mês do mensal ou 25%
  no anual), enviada 5 dias depois de o teste vencer e válida por 7 dias.
- users.marketing_opt_out_at: quem clicou em "não quero mais receber ofertas".

RLS igual à de tenant_subscriptions: a rotina diária roda sem contexto de
escritório (current_app_tenant_id() IS NULL); as rotas, com contexto.

Revision ID: t6v7oferta
Revises: s5u6limiteia
Create Date: 2026-11-13
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "t6v7oferta"
down_revision = "s5u6limiteia"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "retention_offers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="criada"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_cycle", sa.String(20), nullable=True),
        sa.Column("accepted_plan_slug", sa.String(50), nullable=True),
        sa.Column("preapproval_id", sa.String(200), nullable=True),
        sa.Column("promo_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("full_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("promo_charged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("price_bumped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", name="uq_retention_offers_tenant"),
    )
    op.create_index("ix_retention_offers_tenant_id", "retention_offers", ["tenant_id"])
    op.create_index("ix_retention_offers_preapproval_id", "retention_offers", ["preapproval_id"])

    op.execute("ALTER TABLE retention_offers ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON retention_offers
            USING (tenant_id = current_app_tenant_id() OR current_app_tenant_id() IS NULL)
            WITH CHECK (tenant_id = current_app_tenant_id() OR current_app_tenant_id() IS NULL)
        """
    )

    op.add_column("users", sa.Column("marketing_opt_out_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "marketing_opt_out_at")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON retention_offers")
    op.drop_index("ix_retention_offers_preapproval_id", table_name="retention_offers")
    op.drop_index("ix_retention_offers_tenant_id", table_name="retention_offers")
    op.drop_table("retention_offers")
