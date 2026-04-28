# FASE 10 - Deployment & CI/CD

## 🎯 Objetivo

Implementar pipeline completo de deployment e CI/CD para o ContaFlow, incluindo containerização Docker, deploy em Railway (backend) e Vercel (frontend), e automação via GitHub Actions.

## 📋 Escopo

### 1. **Docker Production Setup**

#### Backend Dockerfile (Otimizado)
```dockerfile
# Multi-stage build para otimização
FROM python:3.12-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.12-slim

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . .

# Make sure scripts are executable
RUN chmod +x scripts/*.sh

# Set Python path
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Frontend Dockerfile
```dockerfile
# Build stage
FROM node:20-alpine as builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
```

#### docker-compose.prod.yml
```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
      SECRET_KEY: ${SECRET_KEY}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      VOYAGE_API_KEY: ${VOYAGE_API_KEY}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    ports:
      - "8000:8000"
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "80:80"
    depends_on:
      - api
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### 2. **Railway Deployment (Backend)**

#### railway.toml
```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 100
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10

[env]
PYTHONUNBUFFERED = "1"
```

#### Configuração Railway
1. **Criar Projeto no Railway**
   - Conectar repositório GitHub
   - Selecionar branch `main`

2. **Adicionar PostgreSQL Plugin**
   - Railway fornece DATABASE_URL automaticamente
   - Habilitar pgvector extension via Railway CLI:
     ```bash
     railway run psql -c "CREATE EXTENSION IF NOT EXISTS vector;"
     ```

3. **Adicionar Redis Plugin**
   - Railway fornece REDIS_URL automaticamente

4. **Configurar Environment Variables**
   ```
   SECRET_KEY=<generate-secure-key>
   ANTHROPIC_API_KEY=<your-key>
   VOYAGE_API_KEY=<your-key>
   ALLOWED_ORIGINS=https://contaflow.vercel.app
   ```

5. **Deploy Automático**
   - Push para `main` → Deploy automático
   - Railway gera URL: `https://contaflow-production.up.railway.app`

### 3. **Vercel Deployment (Frontend)**

#### vercel.json
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "devCommand": "npm run dev",
  "installCommand": "npm install",
  "framework": "vite",
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "X-Content-Type-Options",
          "value": "nosniff"
        },
        {
          "key": "X-Frame-Options",
          "value": "DENY"
        },
        {
          "key": "X-XSS-Protection",
          "value": "1; mode=block"
        }
      ]
    }
  ]
}
```

#### Configuração Vercel
1. **Importar Projeto**
   - Conectar repositório GitHub
   - Framework Preset: Vite
   - Root Directory: `frontend`

2. **Environment Variables**
   ```
   VITE_API_URL=https://contaflow-production.up.railway.app
   VITE_APP_NAME=ContaFlow
   ```

3. **Deploy Automático**
   - Push para `main` → Deploy automático
   - Vercel gera URL: `https://contaflow.vercel.app`

### 4. **GitHub Actions CI/CD**

#### .github/workflows/backend-ci.yml
```yaml
name: Backend CI

on:
  push:
    branches: [main, develop]
    paths:
      - 'backend/**'
  pull_request:
    branches: [main]
    paths:
      - 'backend/**'

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      
      - name: Install dependencies
        working-directory: ./backend
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      
      - name: Run linter
        working-directory: ./backend
        run: |
          pip install ruff
          ruff check .
      
      - name: Run type checker
        working-directory: ./backend
        run: |
          pip install mypy
          mypy app --ignore-missing-imports
      
      - name: Run tests
        working-directory: ./backend
        env:
          DATABASE_URL: postgresql+asyncpg://test_user:test_pass@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379/0
          SECRET_KEY: test-secret-key-for-ci
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          VOYAGE_API_KEY: ${{ secrets.VOYAGE_API_KEY }}
        run: |
          pytest tests/ -v --cov=app --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./backend/coverage.xml
          flags: backend

  build:
    runs-on: ubuntu-latest
    needs: test
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Build Docker image
        working-directory: ./backend
        run: |
          docker build -t contaflow-backend:${{ github.sha }} .
```

#### .github/workflows/frontend-ci.yml
```yaml
name: Frontend CI

on:
  push:
    branches: [main, develop]
    paths:
      - 'frontend/**'
  pull_request:
    branches: [main]
    paths:
      - 'frontend/**'

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Install dependencies
        working-directory: ./frontend
        run: npm ci
      
      - name: Run linter
        working-directory: ./frontend
        run: npm run lint
      
      - name: Run type checker
        working-directory: ./frontend
        run: npm run type-check
      
      - name: Run tests
        working-directory: ./frontend
        run: npm run test
      
      - name: Build
        working-directory: ./frontend
        env:
          VITE_API_URL: https://contaflow-production.up.railway.app
        run: npm run build
      
      - name: Upload build artifacts
        uses: actions/upload-artifact@v4
        with:
          name: frontend-build
          path: frontend/dist
```

#### .github/workflows/deploy.yml
```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy-backend:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to Railway
        uses: bervProject/railway-deploy@main
        with:
          railway_token: ${{ secrets.RAILWAY_TOKEN }}
          service: backend
  
  deploy-frontend:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          working-directory: ./frontend
```

### 5. **Health Checks & Monitoring**

#### Backend Health Endpoint
```python
# app/api/v1/endpoints/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_db

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint for load balancers."""
    return {
        "status": "healthy",
        "service": "contaflow-api",
        "version": "1.0.0"
    }

@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Readiness check - verifies database connection."""
    try:
        await db.execute("SELECT 1")
        return {
            "status": "ready",
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "not_ready",
            "database": "disconnected",
            "error": str(e)
        }
```

#### Monitoring com Sentry
```python
# app/main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[FastApiIntegration()],
        traces_sample_rate=0.1,
        environment=settings.ENVIRONMENT,
    )
```

### 6. **Environment Variables Management**

#### Backend .env.production
```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db

# Redis
REDIS_URL=redis://:password@host:6379/0

# Security
SECRET_KEY=<generate-with-openssl-rand-hex-32>
ALLOWED_ORIGINS=https://contaflow.vercel.app,https://app.contaflow.com

# AI Services
ANTHROPIC_API_KEY=sk-ant-...
VOYAGE_API_KEY=pa-...

# Monitoring
SENTRY_DSN=https://...@sentry.io/...
ENVIRONMENT=production

# Features
TOP_K_RESULTS=5
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

#### Frontend .env.production
```env
VITE_API_URL=https://contaflow-production.up.railway.app
VITE_APP_NAME=ContaFlow
VITE_SENTRY_DSN=https://...@sentry.io/...
```

### 7. **Database Migrations em Produção**

#### Script de Deploy
```bash
#!/bin/bash
# scripts/deploy-production.sh

set -e

echo "🚀 Starting production deployment..."

# Run migrations
echo "📦 Running database migrations..."
alembic upgrade head

# Verify migrations
echo "✅ Verifying migrations..."
alembic current

# Start application
echo "🎉 Starting application..."
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

#### Railway Deploy Command
```bash
railway run bash scripts/deploy-production.sh
```

### 8. **Backup & Recovery**

#### PostgreSQL Backup (Railway)
```bash
# Backup database
railway run pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore database
railway run psql $DATABASE_URL < backup_20260427_140000.sql
```

#### Automated Backups (GitHub Actions)
```yaml
name: Database Backup

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC

jobs:
  backup:
    runs-on: ubuntu-latest
    
    steps:
      - name: Backup database
        run: |
          pg_dump ${{ secrets.DATABASE_URL }} > backup.sql
      
      - name: Upload to S3
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Copy to S3
        run: |
          aws s3 cp backup.sql s3://contaflow-backups/$(date +%Y%m%d_%H%M%S).sql
```

### 9. **Custom Domain Setup**

#### Backend (Railway)
1. Adicionar domínio customizado: `api.contaflow.com`
2. Configurar DNS:
   ```
   CNAME api.contaflow.com → contaflow-production.up.railway.app
   ```
3. Railway provisiona SSL automaticamente (Let's Encrypt)

#### Frontend (Vercel)
1. Adicionar domínio customizado: `app.contaflow.com`
2. Configurar DNS:
   ```
   CNAME app.contaflow.com → cname.vercel-dns.com
   ```
3. Vercel provisiona SSL automaticamente

### 10. **Performance Optimization**

#### Backend
- Gunicorn com múltiplos workers
- Connection pooling (SQLAlchemy)
- Redis caching
- CDN para assets estáticos

#### Frontend
- Code splitting (Vite)
- Lazy loading de rotas
- Image optimization
- Gzip compression (Nginx)

## 🚀 Entregáveis

### Arquivos a Criar/Modificar

1. **Docker**:
   - `backend/Dockerfile` (production-optimized)
   - `frontend/Dockerfile` + `nginx.conf`
   - `docker-compose.prod.yml`

2. **Railway**:
   - `backend/railway.toml`
   - `scripts/deploy-production.sh`

3. **Vercel**:
   - `frontend/vercel.json`

4. **GitHub Actions**:
   - `.github/workflows/backend-ci.yml`
   - `.github/workflows/frontend-ci.yml`
   - `.github/workflows/deploy.yml`

5. **Health Checks**:
   - `backend/app/api/v1/endpoints/health.py`
   - Registrar router em `api.py`

6. **Environment**:
   - `.env.production.example` (backend)
   - `.env.production.example` (frontend)

### Documentação

1. `DEPLOYMENT.md` - Guia completo de deployment
2. `MONITORING.md` - Setup de monitoring e alertas

## ✅ Critérios de Aceitação

- [ ] Dockerfile otimizado para backend (multi-stage)
- [ ] Dockerfile otimizado para frontend (Nginx)
- [ ] Railway deployment configurado e funcionando
- [ ] Vercel deployment configurado e funcionando
- [ ] GitHub Actions CI/CD pipeline funcionando
- [ ] Health checks implementados (/health, /ready)
- [ ] Environment variables configuradas
- [ ] Custom domains configurados (opcional)
- [ ] SSL/TLS habilitado
- [ ] Monitoring com Sentry configurado (opcional)
- [ ] Backup automático configurado

## 🎯 Checklist de Deploy

- [ ] Gerar SECRET_KEY seguro
- [ ] Configurar ANTHROPIC_API_KEY
- [ ] Configurar VOYAGE_API_KEY
- [ ] Criar projeto no Railway
- [ ] Adicionar PostgreSQL plugin (Railway)
- [ ] Habilitar pgvector extension
- [ ] Adicionar Redis plugin (Railway)
- [ ] Configurar environment variables (Railway)
- [ ] Deploy backend (Railway)
- [ ] Criar projeto no Vercel
- [ ] Configurar environment variables (Vercel)
- [ ] Deploy frontend (Vercel)
- [ ] Testar endpoints da API
- [ ] Testar frontend em produção
- [ ] Configurar GitHub Actions secrets
- [ ] Testar CI/CD pipeline
- [ ] Configurar custom domains (opcional)
- [ ] Configurar monitoring (opcional)

---

**Fase 10 - Deployment: PRONTO PARA IMPLEMENTAÇÃO** 🚀☁️🔧
