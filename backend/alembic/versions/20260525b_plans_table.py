"""Add plans table with limits and seed default plans

Revision ID: 20260525b
Revises: 20260525
Create Date: 2026-05-25 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260525b'
down_revision = '20260525'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # plans — subscription plan definitions and feature limits
    # ------------------------------------------------------------------
    op.create_table(
        'plans',
        sa.Column('id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('slug', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price_monthly', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('max_clients', sa.Integer(), nullable=True),           # NULL = unlimited
        sa.Column('max_users', sa.Integer(), nullable=True),             # NULL = unlimited
        sa.Column('max_ai_calls_month', sa.Integer(), nullable=True),    # NULL = unlimited
        sa.Column('max_documents_per_client', sa.Integer(), nullable=True),
        sa.Column('features', postgresql.JSONB(), nullable=True),
        sa.Column('active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug', name='uq_plans_slug'),
    )
    op.create_index('ix_plans_slug', 'plans', ['slug'], unique=True)
    op.create_index('ix_plans_active', 'plans', ['active'], unique=False)

    # ------------------------------------------------------------------
    # Seed default plans
    # ------------------------------------------------------------------
    op.execute("""
        INSERT INTO plans (id, slug, name, description, price_monthly,
            max_clients, max_users, max_ai_calls_month, max_documents_per_client, features)
        VALUES
            (
                gen_random_uuid(),
                'free',
                'Gratuito',
                'Plano gratuito para experimentação. Recursos básicos com limites reduzidos.',
                0.00,
                10,
                2,
                0,
                20,
                '{"calculator": true, "ai_chat": false, "pdf_export": false, "portal_cliente": false, "obrigacoes": false}'::jsonb
            ),
            (
                gen_random_uuid(),
                'intermediario',
                'Intermediário',
                'Para escritórios em crescimento. IA fiscal, portal do cliente e motor de obrigações.',
                149.00,
                80,
                5,
                20,
                100,
                '{"calculator": true, "ai_chat": true, "pdf_export": false, "portal_cliente": true, "obrigacoes": true}'::jsonb
            ),
            (
                gen_random_uuid(),
                'premium',
                'Premium',
                'Sem limites. Todas as funcionalidades, IA ilimitada e suporte prioritário.',
                299.00,
                NULL,
                NULL,
                NULL,
                NULL,
                '{"calculator": true, "ai_chat": true, "pdf_export": true, "portal_cliente": true, "obrigacoes": true}'::jsonb
            )
        ON CONFLICT (slug) DO NOTHING;
    """)


def downgrade() -> None:
    op.drop_index('ix_plans_active', table_name='plans')
    op.drop_index('ix_plans_slug', table_name='plans')
    op.drop_table('plans')
