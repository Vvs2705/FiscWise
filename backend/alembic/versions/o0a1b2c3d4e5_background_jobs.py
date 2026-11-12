"""background_jobs: fila de trabalho em segundo plano no Postgres (A2).

Substitui o BackgroundTasks do FastAPI (morre quando o Cloud Run desliga a
instância) por uma fila durável processada após a requisição e pelo tick
horário do Cloud Scheduler. Sem Redis, sem worker fixo.

RLS: linhas de escritório seguem o padrão `tenant_isolation`
(tenant_id = current_app_tenant_id()). O processamento interno liga
`app.job_worker=on` na transação (set_config local) e então enxerga todas as
linhas, inclusive as globais (tenant_id NULL). Sem a flag, uma requisição sem
contexto não vê nada.

Revision ID: o0a1b2c3d4e5
Revises: o1a7bc49gk6
Create Date: 2026-11-12
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "o0a1b2c3d4e5"
down_revision = "o1a7bc49gk6"
branch_labels = None
depends_on = None

POLICY_NAME = "tenant_isolation"


def upgrade() -> None:
    op.create_table(
        "background_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("kind", sa.String(80), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("run_after", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(120), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("idempotency_key", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('queued','running','done','failed','cancelled')",
            name="ck_background_jobs_status",
        ),
        sa.UniqueConstraint("idempotency_key", name="uq_background_jobs_idempotency_key"),
    )

    # Regra da missão: índice com CONCURRENTLY, fora de transação. A tabela
    # acabou de nascer vazia, então é instantâneo de qualquer forma.
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_background_jobs_status_run_after",
            "background_jobs",
            ["status", "run_after"],
            postgresql_concurrently=True,
            if_not_exists=True,
        )
        op.create_index(
            "ix_background_jobs_tenant_created",
            "background_jobs",
            ["tenant_id", "created_at"],
            postgresql_concurrently=True,
            if_not_exists=True,
        )

    op.execute('ALTER TABLE "background_jobs" ENABLE ROW LEVEL SECURITY')
    op.execute(f'DROP POLICY IF EXISTS {POLICY_NAME} ON "background_jobs"')
    op.execute(
        f"""
        CREATE POLICY {POLICY_NAME} ON "background_jobs"
          USING (
            tenant_id = current_app_tenant_id()
            OR current_setting('app.job_worker', true) = 'on'
          )
          WITH CHECK (
            tenant_id = current_app_tenant_id()
            OR current_setting('app.job_worker', true) = 'on'
          )
        """
    )


def downgrade() -> None:
    op.execute(f'DROP POLICY IF EXISTS {POLICY_NAME} ON "background_jobs"')
    op.execute('ALTER TABLE "background_jobs" DISABLE ROW LEVEL SECURITY')
    with op.get_context().autocommit_block():
        op.drop_index(
            "ix_background_jobs_tenant_created",
            table_name="background_jobs",
            postgresql_concurrently=True,
            if_exists=True,
        )
        op.drop_index(
            "ix_background_jobs_status_run_after",
            table_name="background_jobs",
            postgresql_concurrently=True,
            if_exists=True,
        )
    op.drop_table("background_jobs")
