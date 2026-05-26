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

- [x] **5.13 (complemento) — Tela de upgrade de plano** (frontend)

- [x] **Limpeza de docs** — referências a `contaflow.fly.dev` limpas em todos os arquivos de documentação e configurações.

- [x] **5.17 — WhatsApp Business API** (Concluído em 2026-05-25: models, migrations RLS, inbox unificada, whatsapp widget no cockpit)
- [x] **5.18 — Monitor fiscal via parceiro** (Concluído em 2026-05-25: models `FiscalMonitorSummary` e `FiscalNFe`, sync automatico de status/guias/NF-es e aba de cockpit diário)
- [x] **5.19 — RAG fiscal** (Concluído em 2026-05-25: vectors/procedures `RagDocument`, indexação de keywords tf-idf, injeção de contexto na IA e aba de Base de Conhecimento em Configurações)
- [x] **5.20 — API pública + Webhooks** (Concluído em 2026-05-25: TenantApiKey, WebhookSubscription, WebhookDeliveryLog, migration RLS 20260525o, api_key_service.py, webhook_service.py, endpoints /developer, fire-and-forget dispatch, 17 testes passando)

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
  - Resolvido bug de GroupingError no PostgreSQL em `/api/v1/dashboard/overview` usando literal de text cru em `date_trunc`.
  - Corrigido CORS adicionando `www.fiscwise.com.br` e domínios Vercel no `ALLOWED_ORIGINS` do backend.
  - Resolvido crash de boot do frontend adicionando fallback seguro para `VITE_GOOGLE_CLIENT_ID`.
  - Corrigido erro de parsing de query parameter nos endpoints do backend removendo valor padrão inválido de `request: Request`.
- [x] **Autenticação de Dois Fatores (2FA) — Commit `abe75ab`:**
  - Migration `20260525k`: campos `two_factor_enabled`, `two_factor_secret`, `two_factor_method` em `users`
  - Seeds de planos anuais (`intermediario_anual`, `premium_anual`, `enterprise`)
  - `pyotp` + `qrcode[pil]` adicionados ao `requirements.txt`
  - `security.py`: `create_mfa_token()` + `verify_mfa_token()` (JWT curto 5min)
  - `auth.py`: reescrita completa — `/login` detecta 2FA → retorna `requires_2fa`, `/login/verify-2fa`, `/2fa/setup` (QR Code), `/2fa/enable-totp`, `/2fa/confirm-email`, `/2fa/disable`, `/2fa/status`
  - Frontend: `auth.ts` com API 2FA completa; `useAuth.ts` com estado `mfaChallenge`
  - `LoginPage.tsx`: tela OTP animada com 6 caixas, countdown reenvio email
  - `SettingsPage.tsx` aba Segurança: card 2FA com escolha de método, QR Code, ativação TOTP/Email, desativação
- [x] Próxima fatia RLS: desenhar policies específicas para auth, portal magic link, subscriptions/webhooks, notificações, templates globais, e convites de portal (Concluído em 2026-05-25 via migrations `20260525j`, `20260525o`, e `20260525p`).

---

## ✅ REDESIGN — FASES 1 a 5: Nova Experiência Premium (Concluído em 2026-05-25)

- [x] **Fase 1: Reposicionamento e visual** (Ajuste de textos de escritório para contador autônomo, design tokens, paleta de cores teal/emerald)
- [x] **Fase 2: Login premium** (Painel esquerdo com radar fiscal e cards flutuantes, ajuste de layout e formulário responsivo, tela de 2FA limpa)
- [x] **Fase 3: Dashboard cockpit** (DailyFocusCard "Foco de Hoje", ClientAttentionList, FiscalWeekTimeline, remoção de painel de colaboradores)
- [x] **Fase 4: Design system** (Button, Card, Badge, Drawer, Table, CommandMenu, EmptyState, LoadingSkeleton, ProgressRing, FiscalTimeline)
- [x] **Fase 5: Tabelas e drawers nas telas principais**
  - [x] Rota `/clientes/:id` e painel cockpit de clientes (`ClientDetailCockpit`)
  - [x] Slider lateral `ClientDetailsDrawer` e `ClientDetailPage`
  - [x] Dropzone de upload e drawer de visualização de PDF/imagem inline em `DocumentsPage`
  - [x] Agenda Fiscal (`DeadlinesPage`) com ação rápida de conclusão e filtros
  - [x] Criação de obrigações avulsas (`CreateObligationDrawer`) em `ObrigacoesPage`
  - [x] Certificados Digitais (`CertificatesPage`) com `CertificateCard`, dias restantes e aviso ao cliente
  - [x] Financeiro (`FinancePage`) com `MetricCard` KPIs e listagem de recebíveis em grade/lista

---

## ✅ REDESIGN — FASE 6: Central "Aprender" & Onboarding (Concluído em 2026-05-25)

- [x] Criar rota `/aprender` e a tela principal `LearningPage`
- [x] Criar cards de tutoriais e caminhos de aprendizado contábil
- [x] Desenvolver checklist de primeiros passos no onboarding (Setup Tracker dinâmico)
- [x] Adicionar tour interativo guiado com Driver.js (Dashboard, Clientes, Documentos)
- [x] Inserir botões contextuais "Guia" (Aprender sobre esta tela) nas páginas principais (Painel, Clientes, Documentos, Certificados, Financeiro)

---

## ✅ REDESIGN — FASE 7: Diferenciais, Comunicação e Relatórios (Concluído em 2026-05-25)

- [x] Criar e integrar a experiência imersiva do `<ModoFocoModal />` no dashboard
- [x] Implementar ações operacionais diretas no Modo Foco (Concluir, Adiar 7 dias, Aguardar Cliente, Pular) integradas a mutações reais no banco
- [x] Tornar o Score da Carteira (`PortfolioRiskCard`) interativo com regras de cálculo detalhadas e dicas acionáveis de recuperação
- [x] Enriquecer a Timeline de Atividades do cliente no cockpit com Certificados e Recebíveis
- [x] Adicionar botões de ações rápidas inline diretamente na Timeline (Pagar DAS e Honorários)
- [x] Criar a aba `Comunicação` no cockpit de detalhes do cliente com gerador de modelos (DAS, documentos pendentes, certificados)
- [x] Integrar triggers de comunicação por e-mail e atalho direto formatado para WhatsApp Web
- [x] Inserir lembretes inteligentes contextuais nas abas de Prazos e Certificados
- [x] Desenvolver o componente `ClientStatusReportModal` para impressão nativa e download PDF de diagnóstico do cliente
- [x] Validar compilação limpa do frontend com 0 erros ou warnings de tipo

---

## ✅ REDESIGN — FASE 8: Tela de Upgrade & Limpeza de Docs (Concluído em 2026-05-25)

- [x] Criar componente `<UpgradePlanoModal />` com multi-step checkout (Pix, Boleto, Cartão com animação virtual)
- [x] Integrar `<UpgradePlanoModal />` na aba Planos (`SettingsPage.tsx`) com mutações reais no Asaas
- [x] Validar compilação limpa do frontend com 0 erros/warnings
- [x] Confirmar e certificar limpeza completa de referências a `contaflow.fly.dev` em todos os documentos

---

## Notas técnicas

- Stack: Python 3.12 / FastAPI / SQLAlchemy async / Alembic / React 18 / TypeScript / Vite
- Deploy: **Fly.io** (backend — app `fiscwise`, https://fiscwise.fly.dev) + **Vercel** (frontend)
- DB: PostgreSQL via Supabase
- Segurança: JWT + X-Tenant-ID header, RBAC (owner/admin/member/client), **2FA TOTP/Email**
- ADMIN_OPERATIONS_ALLOWED: `false` em produção (segurança)
- Email: provider-agnostic — configure `EMAIL_PROVIDER=resend` + `RESEND_API_KEY`
- Billing: configure `BILLING_PROVIDER=asaas` + `ASAAS_API_KEY` + `BILLING_WEBHOOK_SECRET`
- LGPD: consentimento gravado no tenant; exportação e exclusão via `/account`
- 2FA: TOTP via `pyotp` (RFC 6238) + Email OTP (in-process cache, migrar para Redis em produção)
