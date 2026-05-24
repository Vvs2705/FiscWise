# FiscWise Staging and Observability

## Targets

- Backend staging app: `fiscwise-staging` on Fly.io.
- Frontend staging: Vercel preview/deployment using staging env vars.
- Database/storage staging: separate Supabase project.
- Error monitoring: Sentry projects for backend and frontend.

## Required Secrets

Backend Fly staging:

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY`
- `OPENAI_API_KEY`
- `ADMIN_EMERGENCY_TOKEN`
- `ADMIN_OPERATIONS_ALLOWED=false`
- `REDIS_URL` if strict rate limiting should be active
- `SENTRY_DSN`

Frontend Vercel preview/staging:

- `VITE_API_URL=https://fiscwise-staging.fly.dev`
- `VITE_GOOGLE_CLIENT_ID`
- `VITE_SENTRY_DSN`
- `VITE_SENTRY_TRACES_SAMPLE_RATE=0.1`
- `VITE_APP_VERSION=1.0.0`

## Commands

Create/deploy Fly staging:

```powershell
flyctl apps create fiscwise-staging --org personal
flyctl secrets set DATABASE_URL="<staging-supabase-connection-url>" JWT_SECRET_KEY="<random-hex>" SUPABASE_URL="<staging-url>" SUPABASE_SECRET_KEY="<service-role-key>" OPENAI_API_KEY="<key>" ADMIN_EMERGENCY_TOKEN="<random-token>" ADMIN_OPERATIONS_ALLOWED=false SENTRY_DSN="<backend-dsn>" -a fiscwise-staging
flyctl deploy -c fly.staging.toml -a fiscwise-staging
```

Configure Vercel staging/preview:

```powershell
vercel env add VITE_API_URL preview
vercel env add VITE_SENTRY_DSN preview
vercel env add VITE_SENTRY_TRACES_SAMPLE_RATE preview
vercel env add VITE_APP_VERSION preview
vercel deploy
```

Supabase and Sentry resource creation require authenticated CLIs or dashboard/API tokens. Keep staging separate from production.
