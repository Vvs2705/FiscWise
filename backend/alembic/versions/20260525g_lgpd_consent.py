"""Add LGPD consent fields to tenants and users

Revision ID: 20260525g
Revises: 20260525f
Create Date: 2026-05-25 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '20260525g'
down_revision = '20260525f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tenant: when they accepted the terms of service
    op.add_column(
        'tenants',
        sa.Column(
            'terms_accepted_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Timestamp when the owner accepted FiscWise Terms of Service (LGPD compliance)',
        ),
    )
    # Tenant: version of terms accepted (for future re-acceptance on updates)
    op.add_column(
        'tenants',
        sa.Column(
            'terms_version',
            sa.String(20),
            nullable=True,
            comment='Version of Terms of Service accepted (e.g. "v1.0")',
        ),
    )
    # Tenant: deletion request tracking
    op.add_column(
        'tenants',
        sa.Column(
            'deletion_requested_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='When a data deletion request was submitted (LGPD Art. 18)',
        ),
    )


def downgrade() -> None:
    op.drop_column('tenants', 'deletion_requested_at')
    op.drop_column('tenants', 'terms_version')
    op.drop_column('tenants', 'terms_accepted_at')
