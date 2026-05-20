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
  1. Validate that no invalid or NULL values exist before touching the schema
  2. Add new VARCHAR columns alongside the enum columns
  3. Copy data converted to lowercase
  4. Validate zero NULLs after copy before making column NOT NULL
  5. Drop old enum columns
  6. Rename new columns to original names
  7. Drop the old enum types (now unused)
  8. Re-create enum types with lowercase values using CREATE TYPE ... AS ENUM
  9. Cast VARCHAR columns back to the new enum types

Safety guarantees:
  - All SELECTs run inside the same transaction, so a failure aborts everything
  - Invalid source values raise an error *before* any DDL runs (fail-fast)
  - NULL check after LOWER() copy ensures NOT NULL constraint never sees a NULL
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert_no_invalid_values(
    conn,
    table: str,
    column: str,
    valid_uppercase_values: tuple,
) -> None:
    """Raise RuntimeError if *column* contains values outside *valid_uppercase_values*.

    Why this exists: LOWER() silently converts any string, so garbage data
    would be lowercased and then fail the final ENUM cast with a cryptic
    Postgres error.  Detecting bad values up front makes the failure message
    actionable.
    """
    placeholders = ", ".join(f"'{v}'" for v in valid_uppercase_values)
    result = conn.execute(
        sa.text(
            f"SELECT COUNT(*) FROM {table} "
            f"WHERE {column}::text NOT IN ({placeholders})"
        )
    )
    bad_count = result.scalar()
    if bad_count:
        raise RuntimeError(
            f"Migration aborted: {table}.{column} contains {bad_count} row(s) "
            f"with values outside the expected set {valid_uppercase_values}. "
            f"Inspect and fix the data before re-running this migration."
        )


def _assert_no_nulls(conn, table: str, column: str) -> None:
    """Raise RuntimeError if *column* contains any NULL.

    Why this exists: alter_column(..., nullable=False) issues a NOT NULL
    constraint at the Postgres level.  If any row has NULL, Postgres raises
    an error that aborts the whole transaction, leaving the schema in a
    partially-altered state.  Catching this early gives a clear error message
    and keeps the transaction clean.
    """
    result = conn.execute(
        sa.text(f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL")
    )
    null_count = result.scalar()
    if null_count:
        raise RuntimeError(
            f"Migration aborted: {table}.{column} still has {null_count} NULL "
            f"row(s) after the UPDATE step.  This should never happen unless "
            f"the source column itself had NULLs before conversion.  "
            f"Run: UPDATE {table} SET {column} = '<default>' WHERE {column} IS NULL; "
            f"and re-run the migration."
        )


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    conn = op.get_bind()

    # ------------------------------------------------------------------ #
    # 1. subscription_status_enum  (tenants table)                        #
    # ------------------------------------------------------------------ #

    # Guard: reject rows whose current value is not in the original ENUM.
    # Without this check, LOWER() would silently transform garbage data and
    # the subsequent ::subscription_status_enum cast would fail with a less
    # obvious error message.
    _assert_no_invalid_values(
        conn,
        table="tenants",
        column="subscription_status",
        valid_uppercase_values=("TRIAL", "ACTIVE", "SUSPENDED", "CANCELLED", "EXPIRED"),
    )

    # Add a temporary text column to hold lowercased values during the swap.
    op.add_column("tenants", sa.Column("_sub_status_tmp", sa.Text(), nullable=True))

    # Convert to lowercase into the temporary column.
    op.execute(
        "UPDATE tenants SET _sub_status_tmp = LOWER(subscription_status::text)"
    )

    # Guard: ensure the UPDATE did not leave any NULL in the temp column.
    # This would happen only if subscription_status was already NULL before
    # the migration, which the constraint should have prevented — but we
    # check explicitly to avoid a confusing NOT NULL failure later.
    _assert_no_nulls(conn, table="tenants", column="_sub_status_tmp")

    # Drop the old enum column (removes the FK to the old type as well).
    op.drop_column("tenants", "subscription_status")

    # Drop the old enum type (no longer referenced by any column).
    op.execute("DROP TYPE IF EXISTS subscription_status_enum")

    # Re-create enum type with lowercase values.
    op.execute(
        "CREATE TYPE subscription_status_enum AS ENUM "
        "('trial', 'active', 'suspended', 'cancelled', 'expired')"
    )

    # Add new column with the correct type; nullable=True while we fill it.
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

    # Copy data from temp column, casting text → new enum.
    op.execute(
        "UPDATE tenants SET subscription_status = _sub_status_tmp::subscription_status_enum"
    )

    # Guard: confirm zero NULLs in the final column before marking NOT NULL.
    # COALESCE is intentionally NOT used here: if a row ends up NULL at this
    # point it means either the source was NULL or the cast failed silently,
    # and silently injecting a default would hide a data integrity problem.
    _assert_no_nulls(conn, table="tenants", column="subscription_status")

    # Now safe to enforce NOT NULL.
    op.alter_column("tenants", "subscription_status", nullable=False)

    # Restore the index that the original migration created.
    op.create_index(
        op.f("ix_tenants_subscription_status"),
        "tenants",
        ["subscription_status"],
        unique=False,
    )

    # Drop the temporary column — no longer needed.
    op.drop_column("tenants", "_sub_status_tmp")

    # ------------------------------------------------------------------ #
    # 2. user_role_enum  (users table)                                    #
    # ------------------------------------------------------------------ #

    # Guard: reject rows with unexpected values before touching the schema.
    _assert_no_invalid_values(
        conn,
        table="users",
        column="role",
        valid_uppercase_values=("OWNER", "ADMIN", "MEMBER"),
    )

    # Add a temporary text column.
    op.add_column("users", sa.Column("_role_tmp", sa.Text(), nullable=True))

    # Convert to lowercase.
    op.execute("UPDATE users SET _role_tmp = LOWER(role::text)")

    # Guard: ensure no NULLs after UPDATE.
    _assert_no_nulls(conn, table="users", column="_role_tmp")

    # Drop the old enum column.
    op.drop_column("users", "role")

    # Drop the old enum type.
    op.execute("DROP TYPE IF EXISTS user_role_enum")

    # Re-create with lowercase values.
    op.execute(
        "CREATE TYPE user_role_enum AS ENUM ('owner', 'admin', 'member')"
    )

    # Add new column with correct type.
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

    # Copy from temp column.
    op.execute("UPDATE users SET role = _role_tmp::user_role_enum")

    # Guard: confirm zero NULLs before enforcing NOT NULL.
    _assert_no_nulls(conn, table="users", column="role")

    # Enforce NOT NULL.
    op.alter_column("users", "role", nullable=False)

    # Restore index.
    op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)

    # Drop the temporary column.
    op.drop_column("users", "_role_tmp")


# ---------------------------------------------------------------------------
# downgrade
# ---------------------------------------------------------------------------

def downgrade() -> None:
    """Revert: lowercase enum values → uppercase.

    The same three safety checks (invalid values, NULL after copy, NULL before
    NOT NULL) are applied symmetrically so the downgrade is equally safe.
    """
    conn = op.get_bind()

    # --- users.role ---

    _assert_no_invalid_values(
        conn,
        table="users",
        column="role",
        valid_uppercase_values=("owner", "admin", "member"),
    )

    op.add_column("users", sa.Column("_role_tmp", sa.Text(), nullable=True))
    op.execute("UPDATE users SET _role_tmp = UPPER(role::text)")
    _assert_no_nulls(conn, table="users", column="_role_tmp")

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
    _assert_no_nulls(conn, table="users", column="role")
    op.alter_column("users", "role", nullable=False)
    op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)
    op.drop_column("users", "_role_tmp")

    # --- tenants.subscription_status ---

    _assert_no_invalid_values(
        conn,
        table="tenants",
        column="subscription_status",
        valid_uppercase_values=("trial", "active", "suspended", "cancelled", "expired"),
    )

    op.add_column("tenants", sa.Column("_sub_status_tmp", sa.Text(), nullable=True))
    op.execute("UPDATE tenants SET _sub_status_tmp = UPPER(subscription_status::text)")
    _assert_no_nulls(conn, table="tenants", column="_sub_status_tmp")

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
    _assert_no_nulls(conn, table="tenants", column="subscription_status")
    op.alter_column("tenants", "subscription_status", nullable=False)
    op.create_index(
        op.f("ix_tenants_subscription_status"),
        "tenants",
        ["subscription_status"],
        unique=False,
    )
    op.drop_column("tenants", "_sub_status_tmp")
