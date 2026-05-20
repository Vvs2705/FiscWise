#!/bin/bash
# Direct enum case fix using psql (no Python/asyncpg type issues)
# Run this as: bash fix_enums.sh "$DATABASE_URL"

set -e  # Exit on any error

DATABASE_URL="$1"

if [ -z "$DATABASE_URL" ]; then
    echo "❌ Usage: bash fix_enums.sh \$DATABASE_URL"
    exit 1
fi

# Extract PostgreSQL connection parameters from DATABASE_URL
# Format: postgresql://user:pass@host:port/dbname?options
PGPASSWORD=$(echo "$DATABASE_URL" | sed -n 's/.*:\([^@]*\)@.*/\1/p')
export PGPASSWORD

PG_USER=$(echo "$DATABASE_URL" | sed -n 's/.*\/\/\([^:]*\):.*/\1/p')
PG_HOST=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
PG_PORT=$(echo "$DATABASE_URL" | sed -n 's/.*@[^:]*:\([^/]*\).*/\1/p' || echo "5432")
PG_DB=$(echo "$DATABASE_URL" | sed -n 's/.*\/\([^?]*\).*/\1/p')

echo "🔧 Connecting to PostgreSQL at $PG_HOST:$PG_PORT/$PG_DB as $PG_USER..."

# Run the enum fix SQL
psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" << 'EOF'
-- Fix user_role_enum (UPPERCASE to lowercase)
ALTER TABLE users ADD COLUMN IF NOT EXISTS _role_tmp VARCHAR(50);
UPDATE users SET _role_tmp = LOWER(role::text) WHERE _role_tmp IS NULL;
ALTER TABLE users DROP CONSTRAINT IF EXISTS uq_users_tenant_email;
ALTER TABLE users DROP COLUMN IF EXISTS role;
DROP TYPE IF EXISTS user_role_enum CASCADE;
CREATE TYPE user_role_enum AS ENUM ('owner', 'admin', 'member');
ALTER TABLE users ADD COLUMN role user_role_enum NOT NULL DEFAULT 'member'::user_role_enum;
UPDATE users SET role = _role_tmp::user_role_enum;
ALTER TABLE users DROP COLUMN IF EXISTS _role_tmp;
CREATE INDEX IF NOT EXISTS ix_users_role ON users(role);
ALTER TABLE users ADD CONSTRAINT uq_users_tenant_email UNIQUE (tenant_id, email);

-- Fix subscription_status_enum (UPPERCASE to lowercase)
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS _sub_tmp VARCHAR(50);
UPDATE tenants SET _sub_tmp = LOWER(subscription_status::text) WHERE _sub_tmp IS NULL;
ALTER TABLE tenants DROP COLUMN IF EXISTS subscription_status;
DROP TYPE IF EXISTS subscription_status_enum CASCADE;
CREATE TYPE subscription_status_enum AS ENUM ('trial', 'active', 'suspended', 'cancelled', 'expired');
ALTER TABLE tenants ADD COLUMN subscription_status subscription_status_enum NOT NULL DEFAULT 'trial'::subscription_status_enum;
UPDATE tenants SET subscription_status = _sub_tmp::subscription_status_enum;
ALTER TABLE tenants DROP COLUMN IF EXISTS _sub_tmp;
CREATE INDEX IF NOT EXISTS ix_tenants_subscription_status ON tenants(subscription_status);
EOF

if [ $? -eq 0 ]; then
    echo "✅ Enum case fix completed successfully!"
    exit 0
else
    echo "❌ Enum case fix failed!"
    exit 1
fi
