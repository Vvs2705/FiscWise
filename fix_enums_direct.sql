-- Direct SQL fix for enum case mismatch
-- This converts UPPERCASE enums to lowercase WITHOUT using Alembic
-- Safe to run - uses temp columns and validates at each step

-- =====================================================
-- 1. Fix user_role_enum (UPPERCASE to lowercase)
-- =====================================================

-- Step 1: Add temp column
ALTER TABLE users ADD COLUMN _role_tmp VARCHAR(50);

-- Step 2: Convert values
UPDATE users SET _role_tmp = LOWER(role::text);

-- Step 3: Validate no NULLs
ALTER TABLE users ALTER COLUMN _role_tmp SET NOT NULL;

-- Step 4: Drop old column
ALTER TABLE users DROP COLUMN role;

-- Step 5: Drop old enum type
DROP TYPE user_role_enum;

-- Step 6: Create new enum with lowercase
CREATE TYPE user_role_enum AS ENUM ('owner', 'admin', 'member');

-- Step 7: Add new column with new type
ALTER TABLE users ADD COLUMN role user_role_enum NOT NULL DEFAULT 'member'::user_role_enum;

-- Step 8: Copy data from temp
UPDATE users SET role = _role_tmp::user_role_enum;

-- Step 9: Drop temp column
ALTER TABLE users DROP COLUMN _role_tmp;

-- Step 10: Recreate index
CREATE INDEX ix_users_role ON users(role);

-- =====================================================
-- 2. Fix subscription_status_enum (UPPERCASE to lowercase)
-- =====================================================

-- Step 1: Add temp column
ALTER TABLE tenants ADD COLUMN _sub_tmp VARCHAR(50);

-- Step 2: Convert values
UPDATE tenants SET _sub_tmp = LOWER(subscription_status::text);

-- Step 3: Validate no NULLs
ALTER TABLE tenants ALTER COLUMN _sub_tmp SET NOT NULL;

-- Step 4: Drop old column
ALTER TABLE tenants DROP COLUMN subscription_status;

-- Step 5: Drop old enum type
DROP TYPE subscription_status_enum;

-- Step 6: Create new enum with lowercase
CREATE TYPE subscription_status_enum AS ENUM ('trial', 'active', 'suspended', 'cancelled', 'expired');

-- Step 7: Add new column with new type
ALTER TABLE tenants ADD COLUMN subscription_status subscription_status_enum NOT NULL DEFAULT 'trial'::subscription_status_enum;

-- Step 8: Copy data from temp
UPDATE tenants SET subscription_status = _sub_tmp::subscription_status_enum;

-- Step 9: Drop temp column
ALTER TABLE tenants DROP COLUMN _sub_tmp;

-- Step 10: Recreate index
CREATE INDEX ix_tenants_subscription_status ON tenants(subscription_status);

-- =====================================================
-- Verification
-- =====================================================
SELECT 'user_role_enum' as enum_name, enumlabel as value
FROM pg_enum
WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'user_role_enum')
ORDER BY enumsortorder;

SELECT 'subscription_status_enum' as enum_name, enumlabel as value
FROM pg_enum
WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'subscription_status_enum')
ORDER BY enumsortorder;
