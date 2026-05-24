# FiscWise — Progresso de Implementação

> Atualizado em: 2026-05-24
> Referência: `Evolução seguinte.md`

---

## Regra operacional de fases

- Ao completar 100% de uma fase: atualizar este arquivo, commitar, fazer push para GitHub, publicar backend no Fly.io, publicar frontend no Vercel e validar online antes de iniciar a fase seguinte.
- Fases parcialmente implementadas ficam em "Em andamento" e não contam como encerradas.

---

## ✅ FASE 1 — Semana 1 (Limpeza e fundação)

- [x] Rebranding ContaFlow → FiscWise (fly.toml, requirements.txt, api.ts)
- [x] Admin endpoints simplificados (removidos endpoints de emergência usados 1x)
- [x] Criado `Evolução seguinte.md` com roadmap completo
- [x] **Commit:** `2028c9f` — Semana 1 cleanup

---

## ✅ FASE 2 — Semana 2-3 (CI, testes, observabilidade)

- [x] Sentry (backend + frontend, `send_default_pii=False`)
- [x] GitHub Actions CI (backend-ci.yml, deploy-flyio.yml)
- [x] Audit log (`audit_events` + `log_audit_event()`)
- [x] Composite indexes (banco)
- [x] `usePermission` hook + `RequireRole` component
- [x] StateViews (EmptyState, ErrorState, PageSpinner)
- [x] Validators (CPF, CNPJ)
- [x] Diagnóstico guarded por `ADMIN_OPERATIONS_ALLOWED`

---

## ✅ FASE 3 — Semana 4 (RBAC frontend)

- [x] RBAC frontend com `usePermission` e `RequireRole`
- [x] Proteção de rotas por nível de acesso

---

## ✅ FASE 4 — Mês 2 (Motor de obrigações + Portal)

- [x] **5.7 — Motor de obrigações fiscais**
  - Migration: `obligation_rules`, `client_obligation_profiles`, `obligation_instances`, `document_checklist_items`
  - 10 regras fiscais seedadas (DAS, DEFIS, DCTFWeb, ISS_MENSAL, etc.)
  - `obligation_engine.py` — geração idempotente mensal
  - Scheduler: job dia 1 às 03h UTC
  - **Commit:** `b9df427`

- [x] **5.8 — Portal do cliente v1 (magic link)**
  - Migration: `portal_magic_tokens` (SHA-256 hash)
  - `POST /portal/magic-link/request` + `POST /portal/magic-link/verify`
  - `PortalLoginPage.tsx` + rota `/portal/login`
  - **Commit:** `a1111f4`

---

## ✅ FASE 5 — Mês 3-6 (Produto comercial)

- [x] **5.9 — Cobrança de documentos por e-mail**
  - Migration: `notification_templates`, `notification_messages`
  - `notification_engine.py` — scan + dispatch (provider-agnostic)
  - Scheduler: job toda segunda-feira às 09h UTC
  - API: `GET /notifications`, `POST /notifications/trigger-pending-docs`, `GET /notifications/stats`
  - Frontend: aba "Notificações" em `SettingsPage`
  - **Commit:** `2d87010`

- [x] **5.10 — Honorários recorrentes**
  - Migration: `annual_adjustment_percent` em `accounting_clients`
  - API: `GET/PATCH /clients/{id}/billing-config`, `GET /clients/{id}/billing-history`
  - API: `GET /financeiro/inadimplencia` (owner/admin)
  - Frontend: painel de inadimplência em `FinancePage`
  - **Commit:** `d874951`

- [x] **5.11 — Dashboard de produtividade**
  - `GET /dashboard/productivity` (owner/admin)
  - Frontend: `ProductivityPanel` em `DashboardPage`
  - **Commit:** `d367421`

- [x] **5.12 — Planos e limites**
  - Migration: tabela `plans` com free/intermediario/premium
  - `GET /subscription/plans`, `GET /subscription/usage`, `GET /subscription/limits-check`
  - Frontend: `UsageBar` em SettingsPage
  - **Commit:** `7cdadf8`

- [x] **5.13 — Gateway de pagamento (Asaas)**
  - Migration: `tenant_subscriptions` + `billing_webhook_events`
  - Service: `billing_service.py` (HMAC-SHA256, webhook handlers, idempotência)
  - API: `GET/POST /billing/subscription`, `POST /billing/webhooks/asaas`
  - Middleware exclusion para `/api/v1/billing/webhooks`

- [x] **5.15 — LGPD mínimo viável**
  - Migration `20260525g`: `terms_accepted_at`, `terms_version`, `deletion_requested_at` em `tenants`
  - API: `GET /account/export` (Art. 18 I) + `POST /account/delete` (Art. 18 VI)
  - `RegisterPage`: checkbox obrigatório LGPD
  - `TermsPage.tsx` + `PrivacyPage.tsx` + rotas `/termos` e `/privacidade`
  - **Commit:** `7b82c1a`

---

## ✅ INFRA — Migração Fly.io (concluída em 2026-05-24)

- [x] App `fiscwise` criado no Fly.io (região GRU — São Paulo)
- [x] 11 secrets transferidos do `contaflow` → `fiscwise`
- [x] Bug de migration corrigido (JSON com aspas triplas inválido)  — **Commit:** `9f9c850`
- [x] Deploy bem-sucedido — 2 máquinas em GRU, 2/2 healthchecks passing
- [x] App `contaflow` **deletado** definitivamente
- [x] `docker-compose.yml` e `backend/.env.example` atualizados para `fiscwise`
- [x] URL de produção: **https://fiscwise.fly.dev**

---

## 📋 PENDENTE — Próximas fases

- [x] **5.14 — IA operacional**
  - Classificação de documentos via IA após parsing do upload
  - Extração estruturada de competência, valor e vencimento quando identificados
  - Resumo operacional de cliente por IA com controle de plano e quota
  - Mascaramento de CPF/CNPJ antes de chamadas externas
  - Frontend exibe parsing, classificação, confiança, campos extraídos e resumo no drawer do cliente

- [x] **5.16 — Row Level Security (RLS) — primeira fatia segura**
  - `SET LOCAL app.current_tenant_id` no `get_current_user`
  - Helper PostgreSQL `current_app_tenant_id()`
  - Policies RLS em tabelas operacionais estritamente tenant-scoped
  - Background parser, audit log e schedulers ajustados para restaurar contexto de tenant quando necessário
  - Tabelas de auth, portal, billing webhooks e catálogos globais adiadas para rollout específico

- [ ] **5.13 (complemento) — Tela de upgrade de plano** (frontend)

- [ ] **Limpeza de docs** — ainda há referências a `contaflow.fly.dev` em:
  - `DEPLOYMENT_SUMMARY.md`, `PRODUCTION_STATUS.md`, `README.md`
  - `README_DEPLOYMENT.md`, `FRONTEND_DEPLOYMENT_CHECKLIST.md`
  - `frontend/FRONTEND_README.md`, `docs/VALIDACAO_ONLINE_FISCWISE.md`
  - `backend/alembic/env.py` (fallback URL de dev)
  - `ROADMAP.md` (item de migração já concluído)

- [ ] **5.17 — WhatsApp Business API**
- [ ] **5.18 — Monitor fiscal via parceiro**
- [ ] **5.19 — RAG fiscal**
- [ ] **5.20 — API pública + Webhooks**

---

## Em andamento — 2026-05-24

- [x] Clientes desativados separados da carteira operacional no frontend.
- [x] Ação visual de "Excluir" ajustada para "Desativar", alinhada ao comportamento real de soft-delete.
- [x] Base de IA operacional para documentos: conteúdo parseado é classificado por IA quando `OPENAI_API_KEY` está configurada.
- [x] CPF/CNPJ são mascarados antes de envio para IA externa.
- [x] Resumo operacional de cliente por IA com botão explícito, controle de plano Intermediário+ e quota mensal.
- [x] Frontend de documentos e drawer do cliente exibem classificação, confiança e campos extraídos.
- [x] Base segura para RLS: `app.current_tenant_id` passa a ser setado na sessão PostgreSQL durante autenticação e migration cria helper `current_app_tenant_id()`.
- [x] Primeira fatia RLS: policies em tabelas operacionais estritamente tenant-scoped, sem `FORCE ROW LEVEL SECURITY`.
- [x] **Correções críticas de estabilidade (produção):**
  - Resolvido bug de GroupingError no PostgreSQL em `/api/v1/dashboard/overview` usando literal de texto cru em `date_trunc`.
  - Corrigido CORS adicionando `www.fiscwise.com.br` e domínios Vercel no `ALLOWED_ORIGINS` do backend.
  - Resolvido crash de boot do frontend adicionando fallback seguro para `VITE_GOOGLE_CLIENT_ID`.
  - Corrigido erro de parsing de query parameter nos endpoints do backend removendo valor padrão inválido de `request: Request`.
- [ ] Próxima fatia RLS: desenhar policies específicas para auth, portal magic link, subscriptions/webhooks, notificações e templates globais.

---

## Notas técnicas

- Stack: Python 3.12 / FastAPI / SQLAlchemy async / Alembic / React 18 / TypeScript / Vite
- Deploy: **Fly.io** (backend — app `fiscwise`, https://fiscwise.fly.dev) + **Vercel** (frontend)
- DB: PostgreSQL via Supabase
- Segurança: JWT + X-Tenant-ID header, RBAC (owner/admin/member/client)
- ADMIN_OPERATIONS_ALLOWED: `false` em produção (segurança)
- Email: provider-agnostic — configure `EMAIL_PROVIDER=resend` + `RESEND_API_KEY`
- Billing: configure `BILLING_PROVIDER=asaas` + `ASAAS_API_KEY` + `BILLING_WEBHOOK_SECRET`
- LGPD: consentimento gravado no tenant; exportação e exclusão via `/account`
