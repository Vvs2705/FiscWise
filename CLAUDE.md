# FiscWise — Central Fiscal do Contador Moderno

SaaS de gestão fiscal/contábil **EM PRODUÇÃO** (dados fiscais e financeiros de terceiros — LGPD se aplica). Multi-tenant com Row-Level Security no PostgreSQL. Backend FastAPI + SQLAlchemy 2.x async (Python 3.12+); frontend React 18 + TypeScript + Vite + Tailwind. Deploy: backend no Fly.io, frontend na Vercel, banco no Supabase (PostgreSQL 17 + pgvector), Redis para cache/rate-limit.

## Estrutura

```
backend/
  app/
    api/v1/endpoints/   # Routers FastAPI (auth, billing, obligations, ecac, portal, whatsapp, ...)
    core/               # Config, deps (sessão async + tenant), security, middleware, rate limit, audit
    domain/             # Bounded contexts (ecac, invoices, obligations, guias, fiscal_mailbox, monthly_closing)
    fiscal/             # Camada de isolamento das libs fiscais (nfelib etc.) — TODO acesso a NF-e passa por aqui
    models/  schemas/  services/
  alembic/versions/     # Migrations (nomeadas por data: 20260525x_...)
  tests/                # pytest + pytest-asyncio (asyncio_mode=auto)
frontend/
  src/                  # components, features, pages, stores (Zustand), lib
.github/workflows/      # ci.yml (testes+lint+SAST) e security-review.yml (Claude security review em PRs)
```

## Comandos

```bash
# Backend (a partir de backend/)
uvicorn app.main:app --reload --port 8000
pytest                          # suíte completa
alembic revision --autogenerate -m "descricao"
alembic upgrade head

# Frontend (a partir de frontend/)
npm run dev / npm run build / npm run lint / npm run type-check
```

## Convenções

- **Async em tudo**: SQLAlchemy 2.x com `await db.execute(...)`; sessão async criada em `core/deps.py`.
- **Multi-tenant/RLS**: JWT carrega `tenant_id`; a sessão seta `app.current_tenant_id` no Postgres e as policies RLS filtram por tenant. Nenhuma query sem contexto de tenant.
- **Domínios**: lógica de negócio em `app/domain/<contexto>/`; endpoints finos em `api/v1/endpoints/`.
- **Schemas Pydantic v2** em `app/schemas/` (request/response).
- **Libs fiscais**: consultar o **Context7 MCP** antes de usar APIs de nfelib/erpbrasil/brazilfiscalreport — essas APIs mudam com frequência. Nunca fazer parsing manual de XML de NF-e; usar os bindings da nfelib via `app/fiscal/`.

## Baseline de testes

- **04/07/2026: 252 passed, 0 failed (~56s), 208 warnings** — Python 3.14 local, SQLite async via aiosqlite.
- Deprecations do nosso código (`datetime.utcnow()`, `HTTP_422_UNPROCESSABLE_ENTITY`) foram zeradas em 04/07/2026; os ~200 warnings restantes vêm de libs de terceiros (jose, passlib, pydantic v1-style Config em alguns schemas).
- Qualquer PR deve manter a suíte verde; rodar `pytest` a partir de `backend/` antes de commit.

## Tooling

- **MCPs ativos**:
  - `postgres` (read-only) — `.mcp.json` local (gitignored, contém credencial) com `@henkey/postgres-mcp-server` apontando para o Supabase via role `mcp_readonly` (apenas CONNECT/USAGE/SELECT, sujeita a RLS). Use para inspecionar schema/dados sem risco.
  - `supabase` — gestão do projeto `lkgmgbieottygodrdubi` (FiscWise).
  - `context7` — documentação atualizada de libs.
- **Stack fiscal** (instalada 03/07/2026): `nfelib` 2.5.2 (bindings XML NF-e/NFS-e/CT-e/MDF-e gerados dos XSDs da Fazenda), `erpbrasil.edoc` 3.1.1 (transmissão SEFAZ), `brazilfiscalreport` 1.0.1 (DANFE em PDF). Isoladas atrás de `app/fiscal/` — trocar de lib não pode vazar para o resto do app. Para NFS-e municipal (Abrasf/Ginfes/Betha), avaliar `PyNFe` como complemento.
- **CI**: `ci.yml` roda pytest (Postgres+Redis de serviço), ESLint/tsc/build, Gitleaks, pip-audit, Bandit, npm audit. `security-review.yml` roda o Claude security review em cada PR via `claude-code-action` autenticado pelo **plano ativo** (secret `CLAUDE_CODE_OAUTH_TOKEN`, gerado com `claude setup-token`) — sem consumo de API.

## Regras de produção

1. **Nenhuma migration destrutiva** (DROP/ALTER que perde dados) sem backup verificado e aprovação explícita do Vinicius.
2. **Testes obrigatórios antes de deploy**: suíte verde local + CI verde no PR.
3. **Certificados digitais A1 (.pfx) NUNCA no repositório** — carregar via variável de ambiente/secret manager. Idem senhas e connection strings (`.mcp.json` é gitignored por isso).
4. Escritas no banco de produção só via migrations Alembic revisadas — nunca SQL manual destrutivo.
5. RLS é a fronteira de segurança entre tenants — qualquer mudança em policies exige revisão de segurança.
