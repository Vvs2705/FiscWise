"""Colunas faltantes (schema drift), índices nas FKs e remoção de índices duplicados (A1).

1. Colunas de auditoria que os modelos (TenantBase) têm e as migrations nunca
   criaram. Sem elas qualquer SELECT do ORM nessas tabelas dá 500 em produção
   ("column tax_guides.updated_at does not exist"):
     tax_guides.updated_at, ecac_proxies.updated_at,
     ecac_fiscal_situations.created_at / updated_at,
     fiscal_nfes.updated_at, invoice_events.updated_at,
     invoice_rejections.updated_at, whatsapp_messages.updated_at
   Todas NOT NULL DEFAULT now(), como nos modelos. Idempotente: ambientes
   criados por create_all já têm as colunas.
2. Índices nas 14 chaves estrangeiras sem índice apontadas pelo advisor do
   Supabase (CREATE INDEX CONCURRENTLY IF NOT EXISTS, sem travar escrita).
3. Remoção de 4 índices únicos ix_* que duplicam a constraint uq_* da mesma
   coluna (a unicidade continua garantida pela constraint).

Revision ID: o1a7bc49gk6
Revises: n9h6ab38fj5
Create Date: 2026-11-12
"""

from alembic import context, op
import sqlalchemy as sa

revision = "o1a7bc49gk6"
down_revision = "n9h6ab38fj5"
branch_labels = None
depends_on = None


# (tabela, coluna) — colunas que faltam em relação aos modelos.
MISSING_COLUMNS = [
    ("tax_guides", "updated_at"),
    ("ecac_proxies", "updated_at"),
    ("ecac_fiscal_situations", "created_at"),
    ("ecac_fiscal_situations", "updated_at"),
    ("fiscal_nfes", "updated_at"),
    ("invoice_events", "updated_at"),
    ("invoice_rejections", "updated_at"),
    ("whatsapp_messages", "updated_at"),
]

# (nome do índice, tabela, coluna) — nomes iguais aos que index=True gera no modelo.
FK_INDEXES = [
    ("ix_client_portal_invites_invited_by", "client_portal_invites", "invited_by"),
    ("ix_deadline_items_recurrence_parent_id", "deadline_items", "recurrence_parent_id"),
    ("ix_document_checklist_items_obligation_id", "document_checklist_items", "obligation_id"),
    ("ix_fiscal_monitor_summaries_client_id", "fiscal_monitor_summaries", "client_id"),
    ("ix_fiscal_monitor_summaries_last_cnd_document_id", "fiscal_monitor_summaries", "last_cnd_document_id"),
    ("ix_fiscal_nfes_client_id", "fiscal_nfes", "client_id"),
    ("ix_notification_messages_client_id", "notification_messages", "client_id"),
    ("ix_notification_messages_template_id", "notification_messages", "template_id"),
    ("ix_obligation_instances_assigned_to", "obligation_instances", "assigned_to"),
    ("ix_obligation_instances_rule_id", "obligation_instances", "rule_id"),
    ("ix_portal_magic_tokens_tenant_id", "portal_magic_tokens", "tenant_id"),
    ("ix_tenant_subscriptions_plan_id", "tenant_subscriptions", "plan_id"),
    ("ix_whatsapp_inboxes_client_id", "whatsapp_inboxes", "client_id"),
    ("ix_whatsapp_messages_tenant_id", "whatsapp_messages", "tenant_id"),
]

# (índice duplicado, tabela, coluna, constraint que continua garantindo a unicidade)
DUPLICATE_INDEXES = [
    ("ix_client_obligation_profiles_client_id", "client_obligation_profiles", "client_id",
     "uq_client_obligation_profiles_client_id"),
    ("ix_obligation_rules_code", "obligation_rules", "code", "uq_obligation_rules_code"),
    ("ix_plans_slug", "plans", "slug", "uq_plans_slug"),
    ("ix_portal_magic_tokens_token_hash", "portal_magic_tokens", "token_hash", "uq_portal_magic_tokens_hash"),
]


def _is_postgres() -> bool:
    return op.get_context().dialect.name == "postgresql"


def _offline() -> bool:
    return context.is_offline_mode()


def _existing_columns(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def _existing_indexes(table: str) -> set[str]:
    return {i["name"] for i in sa.inspect(op.get_bind()).get_indexes(table)}


def _unique_constraint_exists(table: str, name: str) -> bool:
    if _offline():
        return True  # SQL gerado para revisão: o dono confere as constraints
    return name in {u["name"] for u in sa.inspect(op.get_bind()).get_unique_constraints(table)}


def upgrade() -> None:
    # 1. Colunas faltantes ---------------------------------------------------
    if _is_postgres():
        op.execute("SET LOCAL lock_timeout = '5s'")
        for table, column in MISSING_COLUMNS:
            op.execute(
                f'ALTER TABLE "{table}" ADD COLUMN IF NOT EXISTS "{column}" '
                "TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()"
            )
    else:
        for table, column in MISSING_COLUMNS:
            if column not in _existing_columns(table):
                op.add_column(
                    table,
                    sa.Column(column, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
                )

    # 2 e 3. Índices -----------------------------------------------------------
    if _is_postgres():
        # CONCURRENTLY não roda dentro de transação.
        with op.get_context().autocommit_block():
            for name, table, column in FK_INDEXES:
                op.execute(f'CREATE INDEX CONCURRENTLY IF NOT EXISTS "{name}" ON "{table}" ("{column}")')
            for name, table, _column, constraint in DUPLICATE_INDEXES:
                if _unique_constraint_exists(table, constraint):
                    op.execute(f'DROP INDEX CONCURRENTLY IF EXISTS "{name}"')
    else:
        for name, table, column in FK_INDEXES:
            if name not in _existing_indexes(table):
                op.create_index(name, table, [column])
        for name, table, _column, constraint in DUPLICATE_INDEXES:
            if name in _existing_indexes(table) and _unique_constraint_exists(table, constraint):
                op.drop_index(name, table_name=table)


def downgrade() -> None:
    if _is_postgres():
        with op.get_context().autocommit_block():
            for name, table, column, _constraint in DUPLICATE_INDEXES:
                op.execute(f'CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS "{name}" ON "{table}" ("{column}")')
            for name, _table, _column in reversed(FK_INDEXES):
                op.execute(f'DROP INDEX CONCURRENTLY IF EXISTS "{name}"')
        op.execute("SET LOCAL lock_timeout = '5s'")
        for table, column in reversed(MISSING_COLUMNS):
            op.execute(f'ALTER TABLE "{table}" DROP COLUMN IF EXISTS "{column}"')
    else:
        for name, table, column, _constraint in DUPLICATE_INDEXES:
            if name not in _existing_indexes(table):
                op.create_index(name, table, [column], unique=True)
        for name, table, _column in reversed(FK_INDEXES):
            if name in _existing_indexes(table):
                op.drop_index(name, table_name=table)
        for table, column in reversed(MISSING_COLUMNS):
            if column in _existing_columns(table):
                with op.batch_alter_table(table) as batch:
                    batch.drop_column(column)
