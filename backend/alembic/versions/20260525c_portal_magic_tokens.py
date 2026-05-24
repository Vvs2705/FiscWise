"""Add portal magic link tokens table

Revision ID: 20260525c
Revises: 20260525b
Create Date: 2026-05-25 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260525c'
down_revision = '20260525b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # portal_magic_tokens — one-time login tokens for client portal
    # ------------------------------------------------------------------
    op.create_table(
        'portal_magic_tokens',
        sa.Column('id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('token_hash', sa.String(length=128), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('used', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash', name='uq_portal_magic_tokens_hash'),
    )
    op.create_index('ix_portal_magic_tokens_token_hash', 'portal_magic_tokens', ['token_hash'], unique=True)
    op.create_index('ix_portal_magic_tokens_user_id', 'portal_magic_tokens', ['user_id'], unique=False)
    op.create_index('ix_portal_magic_tokens_expires_at', 'portal_magic_tokens', ['expires_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_portal_magic_tokens_expires_at', table_name='portal_magic_tokens')
    op.drop_index('ix_portal_magic_tokens_user_id', table_name='portal_magic_tokens')
    op.drop_index('ix_portal_magic_tokens_token_hash', table_name='portal_magic_tokens')
    op.drop_table('portal_magic_tokens')
