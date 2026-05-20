"""fix enum case: uppercase to lowercase values

Revision ID: 20260520_fix_enum_case
Revises: 20260520_operational_mvp
Create Date: 2026-05-20 01:00:00.000000

The initial migration created PostgreSQL enum types with UPPERCASE values
(TRIAL, ACTIVE, OWNER, etc.) but the Python models define lowercase values
(trial, active, owner, etc.). This causes asyncpg to fail with a type error
when inserting rows because the driver sends lowercase strings that PostgreSQL
rejects as invalid enum members.

Strategy:
  1. Add new VARCHAR columns alongside the enum columns
  2. Copy data converted to lowercase
  3. Drop old enum columns
  4. Rename new columns to original names
  5. Drop the old enum types (now unused)
  6. Re-create enum types with lowercase values using CREATE TYPE ... AS ENUM
  7. Cast VARCHAR columns back to the new enum types
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "20260520_fix_enum_case"
down_revision: Union[str, None] = "20260520_operational_mvp"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # 1. subscription_status_enum  (tenants table)                        #
    # ------------------------------------------------------------------ #

    # Add a temporary text column
    op.add_column("tenants", sa.Column("_sub_status_tmp", sa.Text(), nullable=True))

    # Copy existing data, converting to lowercase
    op.execute(
        "UPDATE tenants SET _sub_status_tmp = LOWER(subscription_status::text)"
    )

    # Drop the old enum column
    op.drop_column("tenants", "subscription_status")

    # Drop the old enum type (no longer referenced)
    op.execute("DROP TYPE IF EXISTS subscription_status_enum")

    # Re-create enum type with lowercase values
    op.execute(
        "CREATE TYPE subscription_status_enum AS ENUM "
        "('trial', 'active', 'suspended', 'cancelled', 'expired')"
    )

    # Add new column with correct type, using the migrated data
    op.add_column(
        "tenants",
        sa.Column(
            "subscription_status",
            postgresql.ENUM(
                "trial", "active", "suspended", "cancelled", "expired",
                name="subscription_status_enum",
                create_type=False,   # type already created above
            ),
            nullable=True,
        ),
    )

    op.execute(
        "UPDATE tenants SET subscription_status = _sub_status_tmp::subscription_status_enum"
    )

    # Make it non-nullable now that all rows have a value
    op.alter_column("tenants", "subscription_status", nullable=False)

    # Restore the index that the original migration created
    op.create_index(
        op.f("ix_tenants_subscription_status"),
        "tenants",
        ["subscription_status"],
        unique=False,
    )

    # Drop the temporary column
    op.drop_column("tenants", "_sub_status_tmp")

    # ------------------------------------------------------------------ #
    # 2. user_role_enum  (users table)                                    #
    # ------------------------------------------------------------------ #

    # Add a temporary text column
    op.add_column("users", sa.Column("_role_tmp", sa.Text(), nullable=True))

    # Copy existing data, converting to lowercase
    op.execute("UPDATE users SET _role_tmp = LOWER(role::text)")

    # Drop the old enum column
    op.drop_column("users", "role")

    # Drop the old enum type
    op.execute("DROP TYPE IF EXISTS user_role_enum")

    # Re-create with lowercase values
    op.execute(
        "CREATE TYPE user_role_enum AS ENUM ('owner', 'admin', 'member')"
    )

    # Add new column with correct type
    op.add_column(
        "users",
        sa.Column(
            "role",
            postgresql.ENUM(
                "owner", "admin", "member",
                name="user_role_enum",
                create_type=False,
            ),
            nullable=True,
        ),
    )

    op.execute("UPDATE users SET role = _role_tmp::user_role_enum")

    op.alter_column("users", "role", nullable=False)

    # Restore index
    op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)

    # Drop the temporary column
    op.drop_column("users", "_role_tmp")


def downgrade() -> None:
    # ------------------------------------------------------------------ #
    # Revert: lowercase → uppercase                                        #
    # ------------------------------------------------------------------ #

    # --- users.role ---
    op.add_column("users", sa.Column("_role_tmp", sa.Text(), nullable=True))
    op.execute("UPDATE users SET _role_tmp = UPPER(role::text)")
    op.drop_index(op.f("ix_users_role"), table_name="users")
    op.drop_column("users", "role")
    op.execute("DROP TYPE IF EXISTS user_role_enum")
    op.execute("CREATE TYPE user_role_enum AS ENUM ('OWNER', 'ADMIN', 'MEMBER')")
    op.add_column(
        "users",
        sa.Column(
            "role",
            postgresql.ENUM("OWNER", "ADMIN", "MEMBER", name="user_role_enum", create_type=False),
            nullable=True,
        ),
    )
    op.execute("UPDATE users SET role = _role_tmp::user_role_enum")
    op.alter_column("users", "role", nullable=False)
    op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)
    op.drop_column("users", "_role_tmp")

    # --- tenants.subscription_status ---
    op.add_column("tenants", sa.Column("_sub_status_tmp", sa.Text(), nullable=True))
    op.execute("UPDATE tenants SET _sub_status_tmp = UPPER(subscription_status::text)")
    op.drop_index(op.f("ix_tenants_subscription_status"), table_name="tenants")
    op.drop_column("tenants", "subscription_status")
    op.execute("DROP TYPE IF EXISTS subscription_status_enum")
    op.execute(
        "CREATE TYPE subscription_status_enum AS ENUM "
        "('TRIAL', 'ACTIVE', 'SUSPENDED', 'CANCELLED', 'EXPIRED')"
    )
    op.add_column(
        "tenants",
        sa.Column(
            "subscription_status",
            postgresql.ENUM(
                "TRIAL", "ACTIVE", "SUSPENDED", "CANCELLED", "EXPIRED",
                name="subscription_status_enum",
                create_type=False,
            ),
            nullable=True,
        ),
    )
    op.execute(
        "UPDATE tenants SET subscription_status = _sub_status_tmp::subscription_status_enum"
    )
    op.alter_column("tenants", "subscription_status", nullable=False)
    op.create_index(
        op.f("ix_tenants_subscription_status"),
        "tenants",
        ["subscription_status"],
        unique=False,
    )
    op.drop_column("tenants", "_sub_status_tmp")
