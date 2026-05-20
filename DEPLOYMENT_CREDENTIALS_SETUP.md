# 🔐 Deployment Credentials Setup — ContaFlow Production

**Last Updated:** 2026-05-20  
**Status:** Ready for credential configuration

---

## 📋 Quick Summary

You have three services to connect:
1. **Supabase** (Database) ✅ Project exists
2. **Fly.io** (Backend) ⚠️ App created, needs secrets
3. **Vercel** (Frontend) ✅ Deployed
4. **GitHub Actions** (CI/CD) ⚠️ Needs secrets

---

## 🔑 Required Credentials (Checklist)

### Step 1️⃣ — Get Supabase DATABASE_URL

This is the most critical credential. Without it, nothing will work.

**WHERE TO GET IT:**
```
1. Open: https://app.supabase.com/project/lkgmgbieottygodrdubi
2. Go to: Project Settings → Database → Connection pooling
3. Find "Connection string" (usually under "URI" section)
4. Copy the connection string that looks like:
   postgresql://postgres.lkgmgbieottygodrdubi:[PASSWORD]@aws-0-region.pooler.supabase.com:6543/postgres
```

**TRANSFORM IT:**
```
Replace: postgresql://
With:    postgresql+asyncpg://

Result should look like:
postgresql+asyncpg://postgres.lkgmgbieottygodrdubi:[PASSWORD]@aws-0-region.pooler.supabase.com:6543/postgres
```

**✅ Store as:** `SUPABASE_DATABASE_URL`

---

### Step 2️⃣ — Generate JWT_SECRET_KEY

**Option 1 (Windows PowerShell):**
```powershell
# PowerShell
$bytes = [System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32)
$hex = [System.BitConverter]::ToString($bytes) -replace '-', ''
Write-Host $hex
```

**Option 2 (Linux/WSL/Git Bash):**
```bash
openssl rand -hex 64
```

**✅ Store as:** `JWT_SECRET_KEY`

---

### Step 3️⃣ — Get Fly.io API Token

**WHERE TO GET IT:**
```
1. Open: https://fly.io/user/personal_access_tokens
2. Click: "Create new token"
3. Name it: "GitHub Actions Deployment"
4. Copy the token (it won't show again)
```

**✅ Store as:** `FLY_API_TOKEN`

---

### Step 4️⃣ — Already Have Supabase Secret Key

From previous setup:
```
sb_secret_yi9NzmY8a6XDSTQDAwOIpQ_OHR-eFV1
```

**✅ Store as:** `SUPABASE_SECRET_KEY`

---

## 📝 Step-by-Step Deployment Process

### PART A: GitHub Secrets Configuration

```bash
# Go to your GitHub repo
# https://github.com/Vvs2705/ContaFlow/settings/secrets/actions
```

**Create these 4 secrets:**

| Secret Name | Value | Source |
|------------|-------|--------|
| `FLY_API_TOKEN` | [Get from Fly.io Step 3] | Fly.io personal access tokens |
| `SUPABASE_DATABASE_URL` | [Transform from Step 1] | Supabase connection pooling |
| `JWT_SECRET_KEY` | [Generate in Step 2] | OpenSSL command |
| `SUPABASE_SECRET_KEY` | `sb_secret_yi9NzmY8a6XDSTQDAwOIpQ_OHR-eFV1` | From memory |

---

### PART B: Fly.io Secrets Configuration

Once GitHub secrets are set, deploy will automatically configure Fly.io secrets via the workflow.

**Manual verification (optional):**
```bash
flyctl secrets list --app contaflow
```

**Should show:**
```
NAME                   	DIGEST
DATABASE_URL           	[set]
JWT_SECRET_KEY         	[set]
SUPABASE_SECRET_KEY    	[set]
SUPABASE_URL           	[set from fly.toml]
```

---

### PART C: Frontend Environment Configuration

The frontend is already deployed to Vercel. Environment variables are set via Vercel dashboard.

**Verify in Vercel:**
```
https://vercel.com/dashboard/vvs2705/contabilidadeflow
→ Settings → Environment Variables
```

**Should have:**
- `VITE_API_URL` = `https://contaflow.fly.dev` (for production)
- `VITE_SUPABASE_URL` = `https://lkgmgbieottygodrdubi.supabase.co`
- `VITE_SUPABASE_ANON_KEY` = `sb_publishable_OVeiHE33OoGHEi2opCC1ZQ_2dszkaQY`

---

## 🚀 Deployment Trigger

Once all credentials are set in GitHub, just push to main:

```bash
git add .
git commit -m "deployment: prepare production environment"
git push origin main
```

**What happens automatically:**
1. GitHub Actions workflow runs
2. Builds Docker image
3. Pushes to Fly.io
4. Runs migrations (alembic upgrade head)
5. Starts backend server
6. Health check validates /api/v1/health
7. If health check passes → ✅ Deployment success

**Watch the deployment:**
```bash
# Option 1: GitHub Actions Dashboard
https://github.com/Vvs2705/ContaFlow/actions

# Option 2: Fly.io Dashboard
https://fly.io/apps/contaflow
```

---

## ✅ Verification After Deployment

Once deployed, use this checklist:

```
□ 1. Health check passes
   curl https://contaflow.fly.dev/api/v1/health
   Expected: {"status": "ok"}

□ 2. User registration works
   POST to https://contaflow.fly.dev/api/v1/auth/register
   
□ 3. Frontend loads
   https://contabilidadeflow.com.br
   
□ 4. API requests work
   Click "Dashboard" → should fetch data from backend
   
□ 5. Tenant isolation works
   Register 2 different users in 2 browsers
   Each should see only their own data
```

See: `DEPLOYMENT_VERIFICATION.md` for full checklist

---

## 🔍 Troubleshooting

### Missing SUPABASE_DATABASE_URL
```
Error: "could not connect to database"
Solution: Get the connection string from Supabase Settings → Database → Connection pooling
```

### JWT validation fails
```
Error: "401 Unauthorized" on every request
Solution: Make sure JWT_SECRET_KEY is set and same in all three places (GitHub → Fly.io → Backend)
```

### Fly.io deploy hangs
```
Error: Deploy times out after 10 minutes
Solution: Check flyctl logs → likely migrations taking too long
Run: flyctl ssh console --app contaflow
Then: python -m alembic upgrade head
```

### Frontend still calls localhost
```
Error: Frontend shows "Cannot reach API"
Solution: Update VITE_API_URL in Vercel environment variables to https://contaflow.fly.dev
Redeploy Vercel after updating
```

---

## 📍 Current Status

| Service | Status | Next Step |
|---------|--------|-----------|
| Supabase | ✅ Created | Get DATABASE_URL from pooling settings |
| Fly.io | ⚠️ App exists | Configure secrets, then deploy |
| Vercel | ✅ Deployed | Update VITE_API_URL to Fly.io URL |
| GitHub Actions | ⚠️ Workflow exists | Configure 4 secrets |

---

## 🎯 Timeline

1. **Get credentials** (5 min) — Follow steps 1-4 above
2. **Configure GitHub secrets** (2 min) — Add 4 secrets
3. **Push to main** (1 min) — Trigger deployment
4. **Wait for deployment** (3-5 min) — GitHub Actions runs
5. **Verify** (5 min) — Run health check + test endpoints

**Total: ~20 minutes to production** ✅

---

**Next: Gather the credentials from Supabase, Fly.io, and generate JWT_SECRET_KEY, then I'll help you configure everything and deploy.** 🚀
