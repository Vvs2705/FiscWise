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

## ✅ FASE 5 (cont.) — Mês 4-6 (Produto comercial)

- [x] **5.13 — Gateway de pagamento (Asaas)**
  - Migration: `tenant_subscriptions` + `billing_webhook_events`
  - Model: `billing.py` (TenantSubscription, BillingWebhookEvent)
  - Service: `billing_service.py` (verify_asaas_signature, webhook handlers, idempotency)
  - Endpoint: `GET/POST /billing/subscription`, `POST /billing/webhooks/asaas`
  - Middleware exclusion para `/api/v1/billing/webhooks`
  - Router registrado em `api.py`
  - **Commit:** (incluído em commits anteriores)
  - ⚠️ Frontend de assinatura/upgrade ainda pendente (tela de upgrade de plano)

- [x] **5.15 — LGPD mínimo viável**
  - Migration `20260525g`: `terms_accepted_at`, `terms_version`, `deletion_requested_at` em `tenants`
  - Onboarding: armazena `terms_accepted_at=now_utc` e `terms_version='v1.0'`
  - Schema: campo `terms_accepted: bool` com validator LGPD (422 se false)
  - Endpoint `GET /account/export` — exporta dados pessoais + tenant + contagens (Art. 18 I)
  - Endpoint `POST /account/delete` — registra solicitação de exclusão (Art. 18 VI, 202 Accepted)
  - Router `/account` registrado em `api.py`
  - `RegisterPage`: checkbox obrigatório com links para `/termos` e `/privacidade`
  - `TermsPage.tsx`: Termos de Uso completo (12 seções, PT-BR)
  - `PrivacyPage.tsx`: Política de Privacidade LGPD completa (Art. 18 direitos, tabela base legal)
  - Rotas públicas `/termos` e `/privacidade` em `App.tsx`
  - `RegisterData` interface atualizada com `terms_accepted: boolean`
  - **Commit:** `7b82c1a` — feat(lgpd): implement LGPD Art. 18

---

## ⚠️ PENDENTE — Ação manual necessária

- [ ] **Deploy Fly.io:** O app no Fly.io chama-se `contaflow` (nome antigo, pré-rebranding).
  - Atualize `fly.toml` linha 4: `app = "contaflow"` e execute `fly deploy`
  - **OU** crie o app com o novo nome: `fly apps create fiscwise` e faça `fly deploy`
  - Código já está no GitHub (`git push` feito com sucesso)

---

## 📋 PENDENTE — Próximas fases

- [ ] **5.14 — IA operacional**
  - Classificação de documentos (ML/AI)
  - Extração de dados de notas fiscais
  - Resumo de cliente

- [ ] **5.16 — Row Level Security (RLS)**
  - Políticas RLS no PostgreSQL para todas as tabelas de tenant
  - Tabelas identificadas (todas com `tenant_id`):
    `accounting_clients`, `deadline_items`, `client_documents`, `digital_certificates`,
    `account_receivables`, `client_portal_invites`, `company_partners`, `company_documents`,
    `das_payments`, `calculator_simulations`, `tax_scenarios`, `fiscal_assistant_messages`,
    `client_obligation_profiles`, `obligation_instances`, `document_checklist_items`,
    `notification_messages`, `tenant_subscriptions`, `audit_events`, `users`
  - Implementação via `SET LOCAL app.current_tenant_id` no `get_current_user`
  - ⚠️ DB user postgres é superuser (bypassa RLS) — avaliar criar role limitado

- [ ] **5.13 (complemento) — Tela de upgrade de plano (frontend)**
  - Tela de assinatura/upgrade integrada com Asaas

- [ ] **5.17 — WhatsApp Business API**
- [ ] **5.18 — Monitor fiscal via parceiro**
- [ ] **5.19 — RAG fiscal** (busca em legislação)
- [ ] **5.20 — API pública + Webhooks**

---

## Notas técnicas

- Stack: Python 3.12 / FastAPI / SQLAlchemy async / Alembic / React 18 / TypeScript / Vite
- Deploy: Fly.io (backend — app `contaflow`) + Vercel (frontend)
- DB: PostgreSQL via Supabase
- Segurança: JWT + X-Tenant-ID header, RBAC (owner/admin/member/client)
- Email: provider-agnostic — configure `EMAIL_PROVIDER=resend` + `RESEND_API_KEY`
- Billing: configure `BILLING_PROVIDER=asaas` + `ASAAS_API_KEY` + `BILLING_WEBHOOK_SECRET`
- LGPD: `terms_accepted_at` + `terms_version` gravados no tenant; exportação e exclusão via `/account`
