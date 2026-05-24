# FiscWise — Progresso de Implementação

> Atualizado em: 2026-05-24
> Referência: `Evolução seguinte.md`

---

## ✅ FASE 1 — Semana 1 (Limpeza e fundação)

- [x] Rebranding ContaFlow → FiscWise (fly.toml, requirements.txt, api.ts)
- [x] Admin endpoints simplificados (removidos endpoints de emergência usados 1x)
- [x] Criado `Evolução seguinte.md` com roadmap completo
- [x] **Commit:** `2028c9f` — Semana 1 cleanup

---

## ✅ FASE 2 — Semana 2-3 (CI, testes, observabilidade)

> Já estava implementado antes desta sessão:
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

> Já estava implementado antes desta sessão.
- [x] RBAC frontend com `usePermission` e `RequireRole`
- [x] Proteção de rotas por nível de acesso

---

## ✅ FASE 4 — Mês 2 (Motor de obrigações + Portal)

- [x] **5.7 — Motor de obrigações fiscais**
  - Migration: `obligation_rules`, `client_obligation_profiles`, `obligation_instances`, `document_checklist_items`
  - 10 regras fiscais seedadas (DAS, DEFIS, DCTFWeb, ISS_MENSAL, etc.)
  - `obligation_engine.py` — geração idempotente mensal
  - Scheduler: job dia 1 às 03h UTC
  - API: `GET/POST /obligations/instances`, `PATCH /obligations/instances/{id}`, `GET/PUT /obligations/profiles/{client_id}`, `GET/POST /obligations/checklist`, `POST /obligations/generate`
  - Frontend: `ObrigacoesPage.tsx` + rota `/obrigacoes`
  - **Commit:** `b9df427`

- [x] **5.8 — Portal do cliente v1 (magic link)**
  - Migration: `portal_magic_tokens` (SHA-256 hash)
  - `POST /portal/magic-link/request` (owner/admin)
  - `POST /portal/magic-link/verify` (público)
  - `PortalLoginPage.tsx` + rota `/portal/login`
  - Middleware exclusion para `/api/v1/portal/magic-link`
  - **Commit:** `a1111f4`

---

## ✅ FASE 5 — Mês 3 (Honorários, dashboard, planos)

- [x] **5.11 — Dashboard de produtividade**
  - `GET /dashboard/productivity` (owner/admin)
  - Schemas: `ProductivityOverview`, `CollaboratorStats`, `ClientPendingStats`
  - Frontend: `ProductivityPanel` em `DashboardPage` (só para owner/admin)
  - **Commit:** `d367421`

- [x] **5.9 — Cobrança de documentos por e-mail**
  - Migration: `notification_templates`, `notification_messages`
  - `NotificationTemplate.render()` com substituição de variáveis
  - `notification_engine.py` — scan + dispatch (provider-agnostic)
  - Scheduler: job toda segunda-feira às 09h UTC
  - API: `GET /notifications`, `POST /notifications/trigger-pending-docs`, `GET /notifications/stats`
  - Frontend: aba "Notificações" em `SettingsPage`
  - **Commit:** `2d87010`

- [x] **5.10 — Honorários recorrentes**
  - Migration: `annual_adjustment_percent` em `accounting_clients`
  - Schemas: `monthly_fee`, `billing_day`, `annual_adjustment_percent` expostos
  - API: `GET/PATCH /clients/{id}/billing-config`, `GET /clients/{id}/billing-history`
  - API: `GET /financeiro/inadimplencia` (owner/admin)
  - Frontend: `useInadimplenciaReport` + painel na `FinancePage`
  - **Commit:** `d874951`

- [x] **Planos e limites (Subscription)**
  - Migration: tabela `plans` com free/intermediario/premium
  - `Plan` model + `GET /subscription/plans`, `GET /subscription/usage`, `GET /subscription/limits-check`
  - Enforcement de limite de clientes no `create_client`
  - Frontend: `UsageBar` em SettingsPage
  - **Commit:** `7cdadf8` (sessão anterior)

---

## 🔄 EM ANDAMENTO — Mês 4-6 (Produto comercial)

- [ ] **5.13 — Gateway de pagamento (Asaas/Iugu)**
  - [x] Migration: `tenant_subscriptions` + `billing_webhook_events`
  - [x] Model: `billing.py` (TenantSubscription, BillingWebhookEvent)
  - [x] Service: `billing_service.py` (webhook handlers, idempotency)
  - [ ] Endpoint: `billing.py` (GET/POST /billing/subscription, webhooks Asaas/Iugu)
  - [ ] Registrar router em `api.py`
  - [ ] Frontend: tela de assinatura/upgrade

- [ ] **5.14 — IA operacional**
  - Classificação de documentos
  - Extração de dados de notas fiscais
  - Resumo de cliente

- [ ] **5.15 — LGPD mínimo viável**
  - Termos de uso + Política de privacidade (páginas)
  - Consentimento no cadastro
  - `/account/export` e `/account/delete`

- [ ] **5.16 — Row Level Security (RLS)**
  - Políticas RLS no PostgreSQL para todas as tabelas de tenant

---

## 📋 FASE 6 — Mês 7-12 (Escala e IA avançada)

- [ ] **5.17 — WhatsApp Business API**
- [ ] **5.18 — Monitor fiscal via parceiro**
- [ ] **5.19 — RAG fiscal** (busca em legislação)
- [ ] **5.20 — API pública + Webhooks**

---

## Notas técnicas

- Stack: Python 3.12 / FastAPI / SQLAlchemy async / Alembic / React 18 / TypeScript / Vite
- Deploy: Fly.io (backend `fiscwise`) + Vercel (frontend)
- DB: PostgreSQL via Supabase
- Segurança: JWT + X-Tenant-ID header, RBAC (owner/admin/member/client)
- Email: provider-agnostic — configure `EMAIL_PROVIDER=resend` + `RESEND_API_KEY`
- Billing: configure `BILLING_PROVIDER=asaas` + `ASAAS_API_KEY` + `BILLING_WEBHOOK_SECRET`
