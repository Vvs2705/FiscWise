---
name: feedback_asyncpg_enum_type_cache
description: asyncpg caches PostgreSQL enum OIDs at connection level; use psycopg3 sync for any preflight DDL that recreates enum types
metadata:
  type: feedback
---

Never use asyncpg (or SQLAlchemy async) for scripts that run DDL touching PostgreSQL enum types before the enum values are already correct.

**Why:** asyncpg caches type OIDs at the connection level. If the DB has uppercase enum values (OWNER, TRIAL) but Python models define lowercase (owner, trial), asyncpg fetches OIDs on first connection and tries to compare them as integers. This causes `'<' not supported between instances of 'str' and 'int'` on any query that touches the enum column — including Alembic migration queries — making the migration impossible to run via asyncpg.

`statement_cache_size=0` prevents statement caching but does NOT prevent type OID caching. The bug persists.

**How to apply:** Use `psycopg[binary]` (v3 sync) for all preflight enum fix scripts:
- `psycopg.connect(dsn, autocommit=True)` — each DDL statement is its own transaction
- Convert URL: `postgres://` → `postgresql://`, `?ssl=require` → `?sslmode=require`
- Check table existence and enum values before running DDL (skip on first deploy)
- Run psycopg fix BEFORE asyncpg/Alembic opens any connection
- The fix script is `backend/fix_enums_startup.py`; called from `backend/run_migrations.py`

Related: [[feedback_pydantic_v2_startup_crash]]
