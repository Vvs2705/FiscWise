# FiscWise

> Central fiscal do contador moderno: clientes, documentos, obrigações, e-CAC, notas fiscais, cobranças, guias, certificados e inteligência operacional em um único sistema.

## Para quem é

- **Contadores autônomos** — carteira de clientes com controle total, sem planilhas paralelas
- **Pequenos e médios escritórios** — controle granular de carteiras por responsável, isolamento total de dados
- **BPO financeiro/contábil** — alto volume de notas, guias e fechamento de obrigações mensais

## Módulos principais

| Módulo | Descrição |
|--------|-----------|
| **Clientes** | Cadastro fiscal completo com CNPJ, CNAE, regime tributário, município e UF |
| **Documentos** | Armazenamento seguro com URLs assinadas, MIME validation e limite de tamanho |
| **Obrigações fiscais** | Motor inteligente de calendarização por regime, CNAE, UF e município |
| **Notas fiscais (NFS-e)** | Emissão direta de honorários, conciliação contábil-financeira |
| **Central e-CAC** | Situação fiscal, procurações eletrônicas e caixa postal via Integra Contador |
| **Certificados digitais** | Cofre criptografado A1/A3 com alertas de vencimento e trilha de uso |
| **Guias e impostos** | DAS, DARF, GPS, ISS — controle de pagamento com comprovantes |
| **Cobrança e recebíveis** | Honorários mensais, Pix, boleto, régua de cobrança automática |
| **Portal do cliente** | Área exclusiva para envio de documentos, guias e notas fiscais |
| **WhatsApp** | Régua de cobrança e lembretes direto no canal do cliente |
| **IA operacional** | Classificação de documentos, extração de metadados, assistência fiscal |

## Stack

### Backend
- **Python 3.12+** / **FastAPI 0.115** — framework assíncrono de alta performance
- **SQLAlchemy 2.x async** + **asyncpg** — ORM async para PostgreSQL
- **Alembic** — migrações versionadas
- **Supabase** — PostgreSQL gerenciado + Storage privado
- **Redis** — rate limiting estrito e cache
- **Pydantic v2** — validação de contratos e schemas

### Frontend
- **React 18** + **TypeScript** + **Vite**
- **TanStack Query** — gerenciamento de estado server-side
- **Zustand** — estado local
- **Recharts** + **Framer Motion** — visualização e animações

### Infraestrutura
- **Fly.io** — deploy do backend (região GRU — São Paulo)
- **Vercel** — deploy do frontend
- **GitHub Actions** — CI/CD com testes, SAST e security scanning

## Como rodar localmente

### Pré-requisitos
- Python 3.12+
- Node.js 20+
- Docker e Docker Compose
- PostgreSQL 16 e Redis 7 (ou via Docker)

### Backend

```bash
# 1. Copie as variáveis de ambiente
cp backend/.env.example backend/.env
# Edite backend/.env com seus valores

# 2. Suba os serviços de infraestrutura
docker-compose up -d db redis

# 3. Instale as dependências
cd backend
pip install -r requirements.txt

# 4. Rode as migrations
alembic upgrade head

# 5. Suba o servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Via Docker Compose (tudo junto)

```bash
docker-compose up --build
```

## Variáveis de ambiente

Copie `backend/.env.example` e preencha:

```env
ENVIRONMENT=development
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/fiscwise_db
JWT_SECRET_KEY=<gere com: openssl rand -hex 64>
REDIS_URL=redis://localhost:6379/0
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SECRET_KEY=<service-role-key>
OPENAI_API_KEY=<opcional — para IA fiscal>
SENTRY_DSN=<opcional — observabilidade>
ALLOWED_ORIGINS=http://localhost:3000
```

## Como rodar os testes

```bash
# Backend
cd backend
pytest tests/ -v --cov=app --cov-report=term-missing

# Frontend
cd frontend
npm run lint
npx tsc --noEmit
npm run build
```

## Como fazer deploy

### Backend (Fly.io)

```bash
# Configurar secrets (primeira vez)
flyctl secrets set \
  DATABASE_URL="<sua-url-supabase>" \
  JWT_SECRET_KEY="$(openssl rand -hex 64)" \
  SUPABASE_SECRET_KEY="<service-role-key>" \
  OPENAI_API_KEY="<chave>"

# Deploy
flyctl deploy
```

### Frontend (Vercel)

```bash
cd frontend
vercel deploy --prod
```

## Segurança

Consulte [`docs/SECURITY_CORRECTIONS.md`](docs/SECURITY_CORRECTIONS.md) para o histórico de correções e checklist de blindagem de produção.

Destaques:
- Multi-tenant com isolamento por RLS no PostgreSQL
- Rate limiting estrito em todos os endpoints sensíveis
- Storage privado com URLs assinadas (TTL 300s)
- MIME sniffing real em uploads
- CI com TruffleHog, Safety e Bandit
- Docs API desabilitados em produção
