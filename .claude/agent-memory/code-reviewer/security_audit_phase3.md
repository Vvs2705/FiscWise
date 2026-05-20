---
name: security_audit_phase3_critical_findings
description: Audit findings for auth, middleware, admin endpoints - CRITICAL SQL injection + unprotected admin endpoint
metadata:
  type: project
---

# Security Audit - Phase 3 (May 20, 2026)

## CRITICAL FINDINGS (must fix before next deploy)

### 1. SQL Injection in Admin Emergency Endpoint ⚠️ CRITICAL
**File:** `backend/app/api/v1/endpoints/admin.py` (lines 22-90)
**Risk:** Remote Code Execution via SQL injection in raw SQL execution

**Issue:**
The `/fix-enum-case-raw` endpoint executes raw SQL statements without parameterization. While the current code uses hardcoded strings, this pattern is dangerous:
- Line 72: `await raw_conn.execute(stmt)` where `stmt` is a string
- If future changes add user input, this becomes exploitable

**Current Risk Level:** MEDIUM (hardcoded strings today, but bad pattern)
**Example Attack:** If this endpoint ever accepts user input, attacker could inject `DROP TABLE users`

**Fix Required:**
```python
# NEVER do this:
await raw_conn.execute(f"UPDATE users SET role = '{user_input}'")

# Use parameterized queries or prepared statements instead
# For asyncpg: await raw_conn.execute("UPDATE users SET role = $1", user_input)
```

### 2. Admin Token Hardcoded + No Rate Limiting ⚠️ CRITICAL
**File:** `backend/app/api/v1/endpoints/admin.py` (line 14)
**Risk:** Authentication bypass, exposure in git history, no brute force protection

**Issues:**
```python
ADMIN_TOKEN = "emergency-enum-fix-token-change-in-production"  # Line 14 - HARDCODED
```

Problems:
- Hardcoded in source code (visible in git history forever)
- No rate limiting on `/api/v1/admin/*` endpoints → brute force possible
- Token comparison is case-sensitive but not constant-time
- Token visible in server logs, error responses, monitoring tools
- No expiration, rotation mechanism, or audit trail

**Fix Required:**
1. Move to environment variable: `ADMIN_TOKEN = os.getenv("ADMIN_EMERGENCY_TOKEN")`
2. Add rate limiting middleware for `/api/v1/admin/*` (e.g., Redis-backed)
3. Use timing-safe comparison: `hmac.compare_digest(token, ADMIN_TOKEN)`
4. Add audit logging: log every admin endpoint call with IP, timestamp, result
5. Implement token rotation mechanism

### 3. No Authentication on Admin Endpoints ⚠️ CRITICAL
**File:** `backend/app/api/v1/endpoints/admin.py` (lines 22-90)
**Risk:** Unauthenticated SQL execution in production

**Issue:**
Endpoints accept raw `token: str` query parameter instead of using JWT authentication:
```python
async def fix_enum_case_raw(token: str, db: AsyncSession = Depends(get_db)):
    # Only checks token == hardcoded string
    if not await verify_admin_token(token):
        raise HTTPException(status_code=401, detail="Invalid admin token")
```

Problems:
- Token is a query parameter, visible in proxy logs, browser history, server logs
- Should be in Authorization header (standard OAuth2 Bearer token)
- No JWT validation (no expiration, no signature, no tenant isolation)
- Anyone with the token can execute ANY SQL statement

**Fix Required:**
1. Require `Authorization: Bearer <TOKEN>` header instead of query param
2. Integrate with JWT validation system (use `get_current_user` dependency)
3. Restrict to OWNER-role users only
4. Add endpoint-specific permission checks (e.g., `ADMIN_OPERATIONS_ALLOWED=true` env var)

---

## MEDIUM FINDINGS

### 4. No Commit/Rollback in `/fix-enum-case-raw` 
**File:** `backend/app/api/v1/endpoints/admin.py` (lines 40-89)
**Risk:** Partial updates, data inconsistency if operation fails mid-transaction

**Issue:**
Raw asyncpg connection doesn't explicit `commit()`:
```python
for stmt in sql_statements:
    await raw_conn.execute(stmt)  # No transaction management
```

If statement N fails, statements 1 to N-1 are already committed (depends on autocommit mode).

**Fix Required:**
```python
try:
    # Begin explicit transaction
    async with raw_conn.transaction():
        for stmt in sql_statements:
            await raw_conn.execute(stmt)
except Exception as e:
    # Automatic rollback from context manager
    logger.error(f"Transaction rolled back: {e}")
```

### 5. Admin Endpoint Not in TenantMiddleware Excluded List
**File:** `backend/app/core/middleware.py` (line 22)
**Risk:** Low - middleware correctly excludes `/api/v1/admin`

**Status:** ✅ CORRECT - Line 22 has `/api/v1/admin` in `_EXCLUDED_PREFIXES`

---

## GREEN FINDINGS (Secure)

### ✅ Auth Endpoint - Cross-Tenant Email Collision Fix
**File:** `backend/app/api/v1/endpoints/auth.py` (lines 46-61)
**Status:** CORRECT

Implementation:
```python
result = await db.execute(select(User).where(User.email == form_data.username))
users = result.scalars().all()
if len(users) != 1:
    raise HTTPException(status_code=401, detail="Incorrect email or password")
```

✅ Correct: Queries all users, rejects if count != 1
✅ Secure: Returns generic "Incorrect email or password" (no timing leak)
✅ Logic: Prevents collision but doesn't reveal tenant info

### ✅ Middleware UUID Validation
**File:** `backend/app/core/middleware.py` (lines 89-99)
**Status:** CORRECT

```python
try:
    uuid.UUID(tenant_id)
except ValueError:
    return JSONResponse(status_code=400, ...)
```

✅ Validates UUID format before using as request.state.tenant_id
✅ Rejects malformed tenants

### ✅ User Model - UniqueConstraint on (tenant_id, email)
**File:** `backend/app/models/user.py` (lines 110-112)
**Status:** CORRECT

```python
__table_args__ = (
    UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
)
```

✅ Enforces per-tenant email uniqueness at database level
✅ Prevents cross-tenant collision even if app logic fails

### ✅ Enum Values - Lowercase
**File:** `backend/app/models/user.py` (lines 30-32), `backend/app/models/tenant.py` (lines 26-30)
**Status:** CORRECT

```python
class UserRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
```

✅ All lowercase values match PostgreSQL enum definitions
✅ Fixed from uppercase migration (enum case mismatch resolved)

### ✅ Password Hashing - Bcrypt
**File:** `backend/app/core/security.py` (lines 26-65)
**Status:** CORRECT

✅ Uses bcrypt.checkpw() for timing-safe comparison
✅ Rejects passwords >72 bytes with clear error
✅ Generates fresh salt per hash
✅ No passlib vulnerability (bcrypt called directly)

### ✅ JWT Token Structure
**File:** `backend/app/core/security.py` (lines 68-95)
**Status:** CORRECT

✅ Includes tenant_id in payload (multi-tenant isolation)
✅ Includes role for RBAC
✅ Proper expiration (iat + exp)
✅ HS256 algorithm (acceptable for this tier)

### ✅ User Lookup in get_current_user
**File:** `backend/app/core/deps.py` (lines 138-215)
**Status:** CORRECT

✅ Validates token expiration via jwt.decode()
✅ Checks user exists (scalar_one_or_none())
✅ Validates token tenant_id matches user.tenant_id
✅ Validates request X-Tenant-ID matches user.tenant_id
✅ Validates user.is_active

### ✅ CASCADE Delete on User-Tenant Relationship
**File:** `backend/app/models/user.py` (line 59)
**Status:** CORRECT

```python
ForeignKey("tenants.id", ondelete="CASCADE")
```

✅ When tenant deleted, users automatically deleted
✅ No orphaned user records possible

---

## ACTION ITEMS

| Priority | Item | File | Lines |
|----------|------|------|-------|
| 🔴 CRITICAL | Move ADMIN_TOKEN to env var | admin.py | 14 |
| 🔴 CRITICAL | Add rate limiting to /admin/* | admin.py | 22-89 |
| 🔴 CRITICAL | Require Authorization header | admin.py | 17-19 |
| 🟡 HIGH | Add transaction mgmt to raw SQL | admin.py | 40-72 |
| 🟡 HIGH | Use timing-safe token compare | admin.py | 17-19 |
| 🟢 LOW | Add audit logging to admin calls | admin.py | all |

## Recommended Timeline

1. **Before next deploy:** Fix ADMIN_TOKEN (env var + authorization header)
2. **This week:** Add rate limiting and audit logging
3. **Next sprint:** Implement token rotation system
