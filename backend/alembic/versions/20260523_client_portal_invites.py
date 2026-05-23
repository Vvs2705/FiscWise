"""add client portal invites table

Revision ID: 20260523
Revises: 20260522
Create Date: 2026-05-22 00:00:00.000000

Adds support for CLIENT role and client portal invitation system.
Allows accounting office staff to invite clients to access their own data portal.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260523"
down_revision = "20260523_fiscal_calculator"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add CLIENT role to user_role_enum
    # First, we need to alter the enum by recreating it
    op.execute("ALTER TYPE user_role_enum ADD VALUE 'client' AFTER 'member'")

    # Create invite_status_enum
    op.execute(
        "CREATE TYPE invite_status_enum AS ENUM ('pending', 'accepted', 'rejected', 'expired')"
    )

    # Create client_portal_invites table
    op.create_table(
        'client_portal_invites',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('status', postgresql.ENUM('pending', 'accepted', 'rejected', 'expired', name='invite_status_enum', create_type=False), nullable=False),
        sa.Column('invited_by', sa.UUID(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['client_id'], ['accounting_clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invited_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_client_portal_invites_tenant_id', 'client_portal_invites', ['tenant_id'])
    op.create_index('ix_client_portal_invites_client_id', 'client_portal_invites', ['client_id'])
    op.create_index('ix_client_portal_invites_email', 'client_portal_invites', ['email'])
    op.create_index('ix_client_portal_invites_status', 'client_portal_invites', ['status'])
    op.create_index('ix_client_portal_invites_expires_at', 'client_portal_invites', ['expires_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_client_portal_invites_expires_at', table_name='client_portal_invites')
    op.drop_index('ix_client_portal_invites_status', table_name='client_portal_invites')
    op.drop_index('ix_client_portal_invites_email', table_name='client_portal_invites')
    op.drop_index('ix_client_portal_invites_client_id', table_name='client_portal_invites')
    op.drop_index('ix_client_portal_invites_tenant_id', table_name='client_portal_invites')

    # Drop table
    op.drop_table('client_portal_invites')

    # Drop enum
    op.execute('DROP TYPE IF EXISTS invite_status_enum CASCADE')

    # Remove CLIENT role (note: cannot remove enum values in PostgreSQL, so we leave it)
