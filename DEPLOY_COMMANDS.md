# 🚀 Deployment Commands — Copy-Paste Ready

**Run these commands in order. Each one is self-contained.**

---

## 🔐 STEP 1: Get Supabase DATABASE_URL

**This requires manual action in Supabase Dashboard:**

1. Open: https://app.supabase.com/project/lkgmgbieottygodrdubi
2. Click: **Project Settings** (gear icon, bottom left)
3. Click: **Database** tab
4. Scroll to: **Connection Pooling**
5. Copy the **Connection string** (starts with `postgresql://`)
6. Note down the full string

**Example (yours will look like this):**
```
postgresql://postgres.lkgmgbieottygodrdubi:SOME_PASSWORD@aws-0-gru2.pooler.supabase.com:6543/postgres
```

**Convert it for asyncpg (replace first `postgresql://` with `postgresql+asyncpg://`):**
```
postgresql+asyncpg://postgres.lkgmgbieottygodrdubi:SOME_PASSWORD@aws-0-gru2.pooler.supabase.com:6543/postgres
```

**👉 Save this as your SUPABASE_DATABASE_URL value** ✅

---

## 🔐 STEP 2: Generate JWT_SECRET_KEY

**Run this in PowerShell:**

```powershell
# Windows PowerShell (Administrator or normal)
$bytes = [System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32)
$hex = [System.BitConverter]::ToString($bytes) -replace '-', ''
Write-Host $hex
```

**Output example:**
```
8A2F5E6D9C4B1A7F3E5D2B8C6A9F1E4D7C2A5B8F6E3D9C1B4A7F2E5D8C6B9A
```

**👉 Save this as your JWT_SECRET_KEY value** ✅

---

## 🔐 STEP 3: Get Fly.io API Token

**Run this in PowerShell:**

```powershell
# First, verify you're logged in
flyctl auth whoami

# If not logged in:
flyctl auth login

# Create a new token
flyctl tokens create deploy
```

**It will output:**
```
FlyV1 XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

**👉 Copy the entire token (including "FlyV1 " prefix)** ✅
**👉 Save as your FLY_API_TOKEN value**

---

## 📝 STEP 4: Gather All Secrets (Summary)

By now you should have these 4 values:

```
FLY_API_TOKEN = FlyV1 xxxxxxxxx...
SUPABASE_DATABASE_URL = postgresql+asyncpg://postgres...
JWT_SECRET_KEY = 8A2F5E6D9C4B...
SUPABASE_SECRET_KEY = sb_secret_yi9NzmY8a6XDSTQDAwOIpQ_OHR-eFV1
```

✅ If you have all 4, proceed to STEP 5

---

## 🔧 STEP 5: Configure GitHub Secrets (Automated)

**Run this PowerShell script** (will use GitHub CLI):

```powershell
# Set all secrets at once
$secrets = @{
    'FLY_API_TOKEN' = 'FlyV1 xxxx...'  # Replace with your token
    'SUPABASE_DATABASE_URL' = 'postgresql+asyncpg://...'  # Replace with your URL
    'JWT_SECRET_KEY' = '8A2F5E6D...'  # Replace with your key
    'SUPABASE_SECRET_KEY' = 'sb_secret_yi9NzmY8a6XDSTQDAwOIpQ_OHR-eFV1'
}

foreach ($secret in $secrets.GetEnumerator()) {
    gh secret set $secret.Key --body $secret.Value
    Write-Host "✅ Set $($secret.Key)"
}
```

**Or manually in GitHub UI:**
```
https://github.com/Vvs2705/ContaFlow/settings/secrets/actions
→ "New repository secret"
→ Add each 4 secrets above
```

---

## 🚀 STEP 6: Deploy to Production

**Commit and push to main:**

```bash
cd 'C:\Users\VINICIUS\Videos\MEUS PROJETOS\ContaFlow'
git add .
git commit -m "feat: configure production environment with Supabase + Fly.io"
git push origin main
```

**This triggers GitHub Actions:**
1. Builds Docker image
2. Pushes to Fly.io
3. Runs migrations
4. Starts server
5. Health check validation

**Watch the deployment:**
```bash
# Option 1: GitHub Actions
https://github.com/Vvs2705/ContaFlow/actions

# Option 2: Fly.io CLI
flyctl logs --app contaflow --follow
```

---

## ✅ STEP 7: Verify Deployment

**After deployment completes (3-5 min), test:**

```bash
# Test 1: Health check
curl https://contaflow.fly.dev/api/v1/health
# Expected: {"status": "ok"}

# Test 2: Check logs for errors
flyctl logs --app contaflow --lines 50

# Test 3: Test registration endpoint
curl -X POST https://contaflow.fly.dev/api/v1/auth/register `
  -H "Content-Type: application/json" `
  -d '{
    "email": "test@contaflow.dev",
    "password": "TestPass123!",
    "tenant_name": "TestTenant"
  }'
```

---

## 🔍 STEP 8: Update Frontend (if needed)

If frontend was deployed before and still points to localhost:

1. Go to: https://vercel.com/dashboard
2. Click: **contabilidadeflow** project
3. Go to: **Settings** → **Environment Variables**
4. Update:
   - `VITE_API_URL` = `https://contaflow.fly.dev`
   - Redeploy: `vercel deploy --prod`

Or manually via Vercel CLI:
```bash
cd frontend
vercel env add VITE_API_URL
# Enter: https://contaflow.fly.dev
vercel deploy --prod
```

---

## 📊 Summary of URLs

After deployment, these should all be working:

| Service | URL | Test |
|---------|-----|------|
| **Frontend** | https://contabilidadeflow.com.br | Open in browser |
| **Backend Health** | https://contaflow.fly.dev/api/v1/health | `curl` command above |
| **Backend API** | https://contaflow.fly.dev/api/v1 | Try `/auth/register` |
| **Supabase** | https://app.supabase.com/project/lkgmgbieottygodrdubi | Check logs |
| **Fly.io** | https://fly.io/apps/contaflow | Check deployment |

---

## ⚠️ Troubleshooting

### Deployment fails with "could not connect to database"
```
✅ Solution: Verify SUPABASE_DATABASE_URL is correct in GitHub secrets
- Must include "asyncpg" in the protocol
- Must have the correct password from Supabase
```

### Deployment times out
```
✅ Solution: Migrations taking too long
# Check Fly app logs:
flyctl logs --app contaflow
# Manually run migrations:
flyctl ssh console --app contaflow
python -m alembic upgrade head
```

### Frontend calls localhost instead of Fly.io
```
✅ Solution: VITE_API_URL not updated in Vercel or frontend env
# Redeploy Vercel with new env vars
vercel deploy --prod
```

### JWT validation fails
```
✅ Solution: JWT_SECRET_KEY mismatch
# Regenerate: openssl rand -hex 64
# Update in: GitHub secrets + Fly.io secrets
# Redeploy: git push origin main
```

---

## 🎯 You are here

```
[ ✅ Backend code written ]
[ ✅ Frontend code written ]
[ ✅ Docker configured ]
[ ✅ GitHub Actions workflow created ]
[ ⏳ Get credentials (Steps 1-4) ] ← YOU ARE HERE
[ ⏳ Configure GitHub secrets (Step 5) ]
[ ⏳ Deploy (Step 6) ]
[ ⏳ Verify (Step 7) ]
```

**Next: Get Supabase DATABASE_URL from https://app.supabase.com/project/lkgmgbieottygodrdubi → Settings → Database → Connection Pooling**

---

**Questions? Check DEPLOYMENT_CREDENTIALS_SETUP.md for more details** 📖
