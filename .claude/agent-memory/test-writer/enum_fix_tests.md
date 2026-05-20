---
name: enum-fix-tests-complete
description: Comprehensive test suite for PostgreSQL enum case normalization (fix_enums_startup.py)
metadata:
  type: project
---

## Enum Fix Test Suite — Complete

**File:** `backend/tests/unit/test_enum_fix.py`

**Coverage:** 5 main test suites + integration tests = 35+ test methods

### Test Suites

#### 1. TestBuildDsn (7 tests)
- postgres:// → postgresql:// conversion
- postgresql:// unchanged
- asyncpg style ?ssl=require → libpq style ?sslmode=require
- ?ssl=true, ?ssl=1 → ?sslmode=require
- Complex query strings preserved
- Combined scheme + ssl normalization

#### 2. TestExec (6 tests)
- Successful statement execution
- Benign errors: "already exists"
- Benign errors: "does not exist"
- Benign errors: "undefined column"
- Fatal errors return False
- Syntax error handling

#### 3. TestCheckTables (5 tests)
- Both users and tenants exist
- Only users table exists
- Only tenants table exists
- Neither table exists
- Correct information_schema query used

#### 4. TestEnumHasUppercase (5 tests)
- Detects UPPERCASE in enum values
- All lowercase returns False
- Non-existent enum returns False
- subscription_status_enum uppercase detection
- Uses pg_enum system tables correctly

#### 5. TestFixEnums (6 tests)
- psycopg module not installed
- No-op when tables absent (first deploy)
- No-op when enums already lowercase
- Connection failure handling
- user_role_enum fix execution
- subscription_status_enum fix execution

#### 6. TestFixEnumsCLI (2 tests)
- Empty DATABASE_URL handling
- Missing DATABASE_URL env var respect

#### 7. TestFixEnumsIntegration (2 tests)
- Full workflow both enums need fix
- DSN transformation verification

### Key Testing Patterns

**Mocking Strategy:**
- Mocks psycopg3 connection/cursor to avoid real DB dependency
- Uses MagicMock for context manager simulation
- Side effects for cursor stacking (multiple sequential cursor calls)

**Error Handling:**
- All 5 benign error patterns tested
- Fatal errors verified to fail appropriately
- Connection failures handled gracefully

**Edge Cases:**
- First deployment (no tables)
- Enums already fixed (no-op)
- Mixed case (some UPPERCASE, some lowercase)
- Complex URL parameters (ssl, statement_cache_size, application_name)

### Running Tests

```bash
# All enum fix tests
pytest backend/tests/unit/test_enum_fix.py -v

# Specific test class
pytest backend/tests/unit/test_enum_fix.py::TestBuildDsn -v

# With coverage
pytest backend/tests/unit/test_enum_fix.py --cov=fix_enums_startup --cov-report=term-missing
```

### Status

✅ **Complete** — Suite covers all required scenarios:
1. DSN normalization with asyncpg → libpq conversion
2. Connection + table existence detection
3. Enum uppercase detection (critical for determining fix necessity)
4. Graceful no-op on first deploy
5. Graceful no-op when no DATABASE_URL
6. Both user_role_enum and subscription_status_enum fix paths
7. Full error handling (benign + fatal)

No real database required — all tests use mocks.
