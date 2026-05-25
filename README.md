# FiscWise — Central de Controle para Contadores Autônomos

> Controle sua carteira contábil com precisão. Clientes, documentos, prazos, certificados e obrigações fiscais em uma central feita para contadores autônomos.
> Produzido por **[Vstack Solutions](https://vstack-solution.com)**

## Links de Produção

| Serviço | URL |
|---------|-----|
| Frontend | https://frontend-orcin-one-22.vercel.app |
| Backend API | https://fiscwise.fly.dev |
| API Docs | https://fiscwise.fly.dev/docs |
| Monitoramento Fly.io | https://fly.io/apps/fiscwise/monitoring |

---

## Stack

### Backend
- **Python 3.12** + **FastAPI** — API REST assíncrona
- **SQLAlchemy 2.x async** + **asyncpg** — ORM com driver async para PostgreSQL
- **Alembic** — Migrações versionadas
- **Supabase** — PostgreSQL gerenciado + Storage para arquivos
- **JWT (python-jose)** + **bcrypt** — Autenticação e senhas
- **Pydantic v2** — Validação e DTOs
- **Docker** — Containerização
- **Fly.io** — Plataforma de deploy (app ID: `fiscwise`)

### Frontend
- **React 18** + **TypeScript 5.5** — UI
- **Vite 6.4** — Build tool (zero vulnerabilidades CVE)
- **Tailwind CSS 3** — Estilização
- **React Router v6** — Roteamento SPA
- **TanStack Query v5** — Data fetching e cache
- **Zustand** — Estado global
- **React Hook Form + Zod** — Formulários com validação
- **Recharts** — Gráficos e dashboards
- **Framer Motion** — Animações
- **Vercel** — Hospedagem do frontend

---

## Arquitetura

```
FiscWise/
├── backend/                    # API FastAPI
│   ├── app/
│   │   ├── api/v1/endpoints/  # Rotas HTTP
│   │   ├── core/              # Config, segurança, JWT
│   │   ├── models/            # ORM SQLAlchemy (User, Tenant, Client, etc.)
│   │   ├── schemas/           # Pydantic DTOs
│   │   ├── services/          # Lógica de negócio
│   │   └── main.py            # App + lifespan handler
│   ├── alembic/               # Migrações de banco
│   ├── tests/                 # pytest
│   ├── Dockerfile
│   ├── requirements.txt
│   └── run_migrations.py      # Script de migração para release_command
├── frontend/                   # SPA React
│   ├── src/
│   │   ├── pages/             # 10 páginas
│   │   ├── components/        # UI reutilizável
│   │   ├── lib/               # auth.ts, api.ts, hooks/
│   │   └── stores/            # Zustand stores
│   ├── vite.config.ts
│   └── package.json
├── fly.toml                    # Config Fly.io (com release_command)
└── README.md
```

### Modelo Multi-Tenant

Toda entidade de dados possui `tenant_id`. O middleware `TenantMiddleware` injeta o tenant automaticamente a partir do JWT. Não há compartilhamento de dados entre tenants.
Na experiência do produto, esse isolamento aparece como um ambiente exclusivo do contador, sem expor a complexidade técnica ao usuário final.

---

## Funcionalidades Implementadas

### Autenticação & Perfil
- Registro em 3 passos (empresa → usuário → plano)
- Login email/senha + Google OAuth
- JWT com expiração + refresh implícito
- Perfil editável (nome, telefone)
- Troca de senha com validação da senha atual

### Gestão de Clientes
- CRUD completo com paginação
- Importação via XLSX (read-excel-file, sem vulnerabilidades CVE)
- Campos: nome, CNPJ, email, telefone, endereço, tipo de empresa
- Código de cliente automático (`CLI-XXXX`)

### Documentos
- Upload para Supabase Storage
- Categorização por tipo (Contrato, Declaração, Relatório, etc.)
- Associação a clientes
- Visualização e download

### Financeiro
- Registro de receitas e despesas
- Categorias personalizadas
- Filtros por período
- Gráficos de fluxo de caixa

### Prazos / Obrigações Fiscais
- Cadastro de prazos por tipo de obrigação
- Associação a clientes
- Status: Pendente / Em andamento / Concluído / Atrasado
- Visualização em lista com alertas visuais

### Certificados Digitais
- Cadastro de certificados A1/A3
- Controle de validade com alertas de vencimento
- Associação a CPF/CNPJ

### Configurações
- **Perfil**: nome, telefone (editável)
- **Ambiente**: razão social, CNPJ, endereço, site, telefone
- **Plano**: Free / Starter / Pro com troca em tempo real
- **Segurança**: troca de senha
- **Pagamento**: estrutura preparada (integração futura Stripe)

---

## Deploy

### Backend — Fly.io

```bash
# Deploy completo (migrations + app)
fly deploy

# Migrações rodam automaticamente via release_command antes dos containers
# Ver fly.toml → [deploy] release_command
```

### Frontend — Vercel

```bash
# Deploy via CLI Vercel (configurado no projeto)
vercel --prod
```

### Variáveis de Ambiente (Backend)

| Variável | Descrição |
|----------|-----------|
| `DATABASE_URL` | PostgreSQL connection string (asyncpg) |
| `JWT_SECRET_KEY` | Chave secreta JWT |
| `SUPABASE_URL` | URL do projeto Supabase |
| `SUPABASE_KEY` | Anon key Supabase |
| `SUPABASE_SECRET_KEY` | Service role key Supabase (uploads) |
| `GOOGLE_CLIENT_ID` | OAuth Google |
| `ALLOWED_ORIGINS` | CORS origins separados por vírgula |

### Variáveis de Ambiente (Frontend)

| Variável | Descrição |
|----------|-----------|
| `VITE_API_URL` | URL da API backend |
| `VITE_GOOGLE_CLIENT_ID` | OAuth Google Client ID |

---

## Desenvolvimento Local

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev   # http://localhost:3000
```

---

## Migrações

```bash
# Criar nova migração
cd backend
alembic revision --autogenerate -m "descricao"

# Aplicar migrações
alembic upgrade head

# Ver status
alembic current
```

---

## Testes

```bash
cd backend
pytest tests/ -v
```

---

## Histórico de Commits Recentes

| Commit | Descrição |
|--------|-----------|
| `ae39fab` | fix: elimina todos os erros e avisos de build, segurança e qualidade |
| `0c4c1a3` | feat: perfil completo, configurações e cadastro redesenhado |
| `4603696` | feat(sidebar): logo clicável retorna ao dashboard |
| `5df15ab` | feat(seo): crédito Vstack Solutions + SEO estruturado |
| `179fdd4` | feat(brand): identidade de marca FiscWise — logo, favicon e meta tags |
| `22af9b1` | feat(ui): redesign visual completo — dark mode, animações, nova sidebar |

---

## Empresa

**Vstack Solutions** — https://vstack-solution.com
Todos os direitos reservados © 2026
