# FiscWise — Progresso de Implementação

> Atualizado em: 2026-05-25
> Referências: `Evolução seguinte.md` · `FISCWISE_REDESIGN_MASTERPLAN.md`

---

## Regra operacional de fases

- Ao completar 100% de uma fase: atualizar este arquivo, commitar, fazer push para GitHub, publicar backend no Fly.io, publicar frontend no Vercel e **validar online** antes de iniciar a fase seguinte.
- Fases parcialmente implementadas ficam em "Em andamento" e não contam como encerradas.

---

# PARTE A — Backend, Infra e Produto (concluídas)

## ✅ FASE A1 — Semana 1 (Limpeza e fundação)

- [x] Rebranding ContaFlow → FiscWise (fly.toml, requirements.txt, api.ts)
- [x] Admin endpoints simplificados
- [x] `Evolução seguinte.md` com roadmap completo
- [x] **Commit:** `2028c9f`

## ✅ FASE A2 — Semana 2-3 (CI, testes, observabilidade)

- [x] Sentry backend + frontend (`send_default_pii=False`)
- [x] GitHub Actions CI (`backend-ci.yml`, `deploy-flyio.yml`)
- [x] Audit log (`audit_events` + `log_audit_event()`)
- [x] Composite indexes no banco
- [x] `usePermission` hook + `RequireRole` component
- [x] StateViews (EmptyState, ErrorState, PageSpinner)
- [x] Validators CPF/CNPJ
- [x] Diagnóstico guarded por `ADMIN_OPERATIONS_ALLOWED`

## ✅ FASE A3 — Semana 4 (RBAC)

- [x] RBAC frontend com `usePermission` e `RequireRole`
- [x] Proteção de rotas por nível de acesso

## ✅ FASE A4 — Mês 2 (Motor de obrigações + Portal)

- [x] **5.7 — Motor de obrigações fiscais**
  - Migration: `obligation_rules`, `client_obligation_profiles`, `obligation_instances`, `document_checklist_items`
  - 10 regras fiscais seedadas, `obligation_engine.py` idempotente, scheduler dia 1 às 03h
  - **Commit:** `b9df427`
- [x] **5.8 — Portal do cliente v1 (magic link)**
  - SHA-256 token, `POST /portal/magic-link/{request,verify}`, `PortalLoginPage.tsx`
  - **Commit:** `a1111f4`

## ✅ FASE A5 — Mês 3-6 (Produto comercial)

- [x] **5.9 — Notificações por e-mail** — `notification_engine.py`, scheduler segunda às 09h, aba Notificações em Settings — **Commit:** `2d87010`
- [x] **5.10 — Honorários recorrentes** — billing-config, histórico, inadimplência — **Commit:** `d874951`
- [x] **5.11 — Dashboard de produtividade** — `GET /dashboard/productivity`, `ProductivityPanel` — **Commit:** `d367421`
- [x] **5.12 — Planos e limites** — tabela `plans`, usage, limits-check, `UsageBar` — **Commit:** `7cdadf8`
- [x] **5.13 — Gateway Asaas** — `tenant_subscriptions`, webhook HMAC-SHA256, idempotência
- [x] **5.14 — IA operacional** — classificação de documentos, extração estruturada, resumo por cliente, mascaramento CPF/CNPJ, quota por plano
- [x] **5.15 — LGPD mínimo viável** — migration `20260525g`, `/account/export`, `/account/delete`, checkbox cadastro, TermsPage, PrivacyPage — **Commit:** `7b82c1a`
- [x] **5.16 — RLS (primeira fatia)** — `SET LOCAL app.current_tenant_id`, helper PG, policies operacionais tenant-scoped

## ✅ FASE A6 — Segurança avançada

- [x] **2FA TOTP + Email** — migration `20260525k`, `pyotp`, `/login/verify-2fa`, `/2fa/setup`, QR Code, tela OTP animada em LoginPage, aba Segurança em Settings — **Commit:** `abe75ab`

## ✅ INFRA — Migração Fly.io (2026-05-24)

- [x] App `fiscwise` criado (GRU — São Paulo), 11 secrets migrados
- [x] Bug migration JSON corrigido — **Commit:** `9f9c850`
- [x] 2 máquinas em GRU, 2/2 healthchecks passing
- [x] App `contaflow` deletado definitivamente
- [x] URL de produção: **https://fiscwise.fly.dev**

---

# PARTE B — Redesign Premium (FISCWISE_REDESIGN_MASTERPLAN.md)

> Objetivo: transformar o FiscWise em produto premium e desejável para **contadores autônomos**.
> Referência completa: `ideia e melhorias/FISCWISE_REDESIGN_MASTERPLAN.md`

---

## ✅ FASE R1 — Reposicionamento e tokens visuais

> Antes de qualquer tela nova, corrigir linguagem e criar base visual. Sem isso o produto continua parecendo genérico.

- [x] Remover linguagem de "escritório/equipe/colaborador" do README, login e configurações
- [x] Renomear "Dashboard" → "Painel" no menu lateral
- [x] Renomear "Agenda / Prazos" → "Agenda Fiscal"
- [x] Renomear "DAS Mensal" → "Guias e DAS"
- [x] Renomear "Calculadora Fiscal" → "Calculadora"
- [x] Reordenar menu: Painel, Clientes, Agenda Fiscal, Obrigações, Documentos, Guias e DAS, Certificados, Financeiro, Calculadora, Configurações
- [x] Criar `frontend/src/styles/tokens.css` com paleta `--fw-*` completa (escuro, teal, azul, dourado)
- [x] Criar `frontend/src/lib/motion.ts` com padrões reutilizáveis (fadeIn, slideUp, staggerContainer, cardHover)
- [x] Importar tokens.css no `index.css`
- [x] Atualizar README com nova descrição voltada ao contador autônomo
- [x] Corrigir textos do LoginPage (remover linguagem de escritório)
- [x] Corrigir copy do dashboard (substituir por linguagem de contador autônomo)

**Critério de conclusão:** ✅ Produto fala com contador autônomo, tokens visuais existem e estão disponíveis para uso.

**Commit:** `2053fe4`

---

## ✅ REDESIGN — FASE 2: Login premium

> A primeira impressão do produto. Deve vender antes do usuário entrar.

- [x] Quebrar `LoginPage.tsx` em componentes menores:
  - [x] `LoginBrandPanel.tsx` — painel esquerdo com narrativa visual (já existia)
  - [x] `FloatingMetricCards.tsx` — cards animados (já existia, melhorado com motion.ts)
  - [x] `FiscalRadarAnimation.tsx` — radar fiscal (já existia, melhorado com motion.ts)
  - [x] `OtpInput.tsx` — 6 caixas OTP extraído para componente reutilizável
- [x] Aplicar paleta escura + glassmorphism no card de login (já implementado)
- [x] Implementar aurora background animada no painel esquerdo (já implementado)
- [x] Atualizar headline: "Controle sua carteira contábil com precisão." (já implementado)
- [x] Atualizar subheadline voltada ao contador autônomo (já implementado)
- [x] Microinterações: fade in painel, slide up formulário, stagger nos cards (já implementado)
- [x] Melhorar responsividade mobile (painel esquerdo some em mobile, formulário ocupa tela toda) (já implementado)

**Critério de conclusão:** ✅ Login causa boa primeira impressão, radar fiscal aparece, cards flutuam.

**Commit:** `75d0dd4`

---

## ✅ FASE R3 — Dashboard cockpit ("Sua rotina de hoje")

> Substituir dashboard genérico por cockpit diário que responde: "O que preciso fazer hoje?"

- [x] Quebrar `DashboardPage.tsx` em componentes de feature:
  - [x] `DashboardHero.tsx` — boas-vindas com botões de ação e alerta de erro
  - [x] `DailyFocusCard.tsx` — card principal com resumo das pendências do dia (danger/warning/info/success)
  - [x] `MetricsGrid.tsx` — 4 KPIs acionáveis (obrigações, clientes, documentos, recebíveis)
  - [x] `ClientAttentionList.tsx` — lista com score de risco por cliente (Alto/Médio/Baixo/Regular) + ícones
  - [x] `FiscalWeekTimeline.tsx` — agenda fiscal da semana em formato timeline (5 dias)
  - [x] `PendingDocumentsCard.tsx` — documentos aguardando conferência com status
  - [x] `MonthlyClosingCard.tsx` — progresso de fechamentos da competência atual (barra animada + grid de status)
  - [x] `PortfolioRiskCard.tsx` — score 0-100 da saúde da carteira (circular progress + fatores de risco)
  - [x] `QuickActions.tsx` — ações rápidas (novo cliente, nova obrigação, upload documento, certificado, guia, calculadora)
- [x] Refatorar `DashboardPage.tsx` para usar todos os novos componentes
- [x] Remover imports não utilizados (useNavigate, usePermission)
- [x] Ajustar métricas para contador autônomo (dados reais do backend)
- [x] Implementar cálculo de score da carteira no frontend (baseado em obrigações atrasadas, docs pendentes, certs vencendo, recebíveis)

**Critério de conclusão:** ✅ Dashboard mostra prioridades reais do dia, componentes modulares, sem linguagem de equipe.

**Arquivos criados:**
- `frontend/src/features/dashboard/components/DashboardHero.tsx`
- `frontend/src/features/dashboard/components/DailyFocusCard.tsx`
- `frontend/src/features/dashboard/components/MetricsGrid.tsx`
- `frontend/src/features/dashboard/components/ClientAttentionList.tsx`
- `frontend/src/features/dashboard/components/FiscalWeekTimeline.tsx`
- `frontend/src/features/dashboard/components/PendingDocumentsCard.tsx`
- `frontend/src/features/dashboard/components/MonthlyClosingCard.tsx`
- `frontend/src/features/dashboard/components/PortfolioRiskCard.tsx`
- `frontend/src/features/dashboard/components/QuickActions.tsx`

**Arquivos modificados:**
- `frontend/src/pages/DashboardPage.tsx` — refatorado completamente para usar componentes modulares

**Nota:** Endpoint `GET /dashboard/portfolio-health` não foi necessário — cálculo implementado no frontend usando dados existentes.

---

## ✅ FASE R4 — Design system premium

> Sem design system, cada tela fica inconsistente. Esta fase cria a base reutilizável.

- [x] Instalar e configurar `shadcn/ui` (customizado com tokens FiscWise — não usar visual padrão)
- [x] Instalar `sonner` (substituir `react-hot-toast`)
- [x] Instalar `vaul` (drawers)
- [x] Instalar `cmdk` (command palette)
- [x] Instalar `@tanstack/react-table`
- [x] Instalar `driver.js`
- [x] Instalar `embla-carousel-react`
- [x] Criar `Button` com variantes premium (primary, secondary, ghost, danger, premium com gradiente teal)
- [x] Criar `Card` com variantes (MetricCard, ActionCard, RiskCard, DocumentCard, CertificateCard)
- [x] Criar `Badge` / `StatusPill` com variantes (regular, attention, critical, pending, completed, overdue, paid, expiring)
- [x] Criar `Drawer` base usando Vaul
- [x] Criar `Table` base usando TanStack Table
- [x] Criar `CommandMenu` (`Ctrl+K`) com busca de clientes e ações rápidas
- [x] Criar `EmptyState` premium (ilustração + CTA — substituir o atual)
- [x] Criar `LoadingSkeleton` consistente para todas as telas
- [x] Criar `ProgressRing` para score da carteira
- [x] Criar `FiscalTimeline` para timeline de cliente

**Critério de conclusão:** ✅ Componentes de fundação do design system criados e exportados para reuso, Command Palette funcional com `Ctrl+K` e `sonner` Toaster integrado globalmente.

---

## ✅ FASE R5 — Tabelas e drawers nas telas principais (Concluído em 2026-05-25)

> Elevar a qualidade visual das telas mais usadas.

- [x] **Clientes** — refatorar com TanStack Table:
  - [x] Colunas: nome, CPF/CNPJ, regime, status, pendências, última interação, ação
  - [x] Badge de risco por cliente (Alto/Médio/Baixo/Regular)
  - [x] Busca rápida com debounce
  - [x] Filtros por regime tributário e status
  - [x] Visualização em lista e cards (toggle)
  - [x] `ClientDetailsDrawer` — drawer lateral com: Resumo / Documentos / Obrigações / Guias / Certificados / Financeiro / Histórico / Notas internas
  - [x] Rota `/clientes/:id` com página dedicada de detalhe
- [x] **Documentos** — refatorar:
  - [x] Drag & drop premium para upload
  - [x] `DocumentPreviewDrawer` com preview inline
  - [x] Status: Recebido / Aguardando conferência / Aprovado / Rejeitado / Pendente do cliente
  - [x] Filtros por tipo, cliente, competência
- [x] **Agenda Fiscal** — refatorar:
  - [x] Visualização calendário + lista + semana
  - [x] Filtros por cliente e tipo de obrigação
  - [x] Marcar como concluído com animação
  - [x] Transformar prazo em tarefa com 1 clique
- [x] **Obrigações** — refatorar:
  - [x] Status visual: Pendente / Em andamento / Aguardando cliente / Concluída / Atrasada
  - [x] `CreateObligationDrawer` (criação rápida sem sair da tela)
- [x] **Certificados** — cards com barra de vencimento + botão "avisar cliente"
- [x] **Financeiro** — métricas: Recebido no mês / A receber / Em atraso / Clientes inadimplentes / Ticket médio

**Critério de conclusão:** tabelas das 5 telas principais usam TanStack Table, drawers funcionam, busca e filtros operam.

---

## ✅ FASE R6 — Aba "Aprender" + Onboarding (Concluído em 2026-05-25)

> Reduzir abandono, acelerar ativação e aumentar percepção de valor.

- [x] Criar rota `/aprender` com `LearningPage.tsx`
- [x] Criar `GettingStartedChecklist` — checklist de ativação no dashboard (some quando completo)
- [x] Criar cards de tutorial estáticos para os primeiros conteúdos:
  - Como cadastrar seu primeiro cliente
  - Como criar uma obrigação fiscal
  - Como organizar documentos por cliente
  - Como controlar certificados digitais
  - Como usar a calculadora fiscal
- [x] Adicionar botão "Aprender sobre esta tela" em cada página (abre overlay contextual)
- [x] Instalar e configurar `Driver.js` para tours guiados:
  - [x] Tour do Painel (5 passos)
  - [x] Tour de Clientes (4 passos)
  - [x] Tour da Agenda Fiscal (4 passos)
  - [x] Tour de Documentos (3 passos)
- [x] Criar fluxo de onboarding no primeiro login:
  - Tela "Bem-vindo" com escolha de perfil (MEI / Simples / Lucro Presumido / etc.)
  - Cadastrar primeiro cliente
  - Criar primeira obrigação
  - Tour do painel
- [x] Backend: `user_onboarding_state` — campo JSON em `users` para rastrear tours concluídos

**Critério de conclusão:** usuário novo sabe o que fazer ao entrar, tour funciona, aba Aprender tem conteúdo útil.

---

## ✅ FASE R7 — Diferenciais únicos (Concluído em 2026-05-25)

> Recursos que nenhum concorrente genérico tem. Fazem o produto ser lembrado.

- [x] **Modo Foco** — resolver pendências uma por vez:
  - Card "Iniciar Modo Foco" no dashboard
  - Interface 1 tarefa por vez com contexto do cliente
  - Ações: Resolver / Adiar / Aguardando cliente / Pular
- [x] **Score da Carteira** — saúde 0-100:
  - Endpoint `GET /dashboard/portfolio-health`
  - Card visual com `ProgressRing` e 3 pontos de atenção
  - Cálculo: obrigações atrasadas, docs pendentes, certs vencendo, guias em aberto, recebíveis em atraso
- [x] **Timeline do Cliente** — histórico cronológico em `/clientes/:id`:
  - Documentos recebidos, obrigações concluídas, guias enviadas, certificados cadastrados
  - Visual tipo feed com ícone + data + descrição
- [x] **Templates de mensagem** — textos prontos para WhatsApp/e-mail:
  - "Seus documentos do mês ainda não chegaram"
  - "Sua guia DAS vence em X dias"
  - "Seu certificado digital vence em X dias"
- [x] **Relatório simples por cliente** — exportar PDF com situação do cliente:
  - Obrigações do período, documentos, guias, situação financeira

**Critério de conclusão:** Modo Foco funciona, Score da Carteira exibe no painel, Timeline aparece no detalhe do cliente.

---

# PARTE C — Pendências técnicas e backlog


## 📋 Pendências técnicas

- [x] **RLS — próxima fatia**: policies para auth, portal magic link, subscriptions, webhooks, notification templates globais, e convites de portal (Concluído em 2026-05-25 via migrations `20260525j`, `20260525o`, e `20260525p`)
- [x] **5.13 complemento** — tela de upgrade de plano (frontend Asaas)
- [x] **Limpeza de docs** — referências `contaflow.fly.dev` limpas

## 📋 Backlog — Fase 6 do plano original

- [x] **5.17 — WhatsApp Business API** (Concluído em 2026-05-25: models, migrations RLS, inbox unificada, whatsapp widget no cockpit)
- [x] **5.18 — Monitor fiscal via parceiro** (Concluído em 2026-05-25: models `FiscalMonitorSummary` e `FiscalNFe`, sync automatico de status/guias/NF-es e aba de cockpit diário)
- [x] **5.19 — RAG fiscal** (Concluído em 2026-05-25: vectors/procedures `RagDocument`, indexação de keywords tf-idf, injeção de contexto na IA e aba de Base de Conhecimento em Configurações)
- [x] **5.20 — API pública + Webhooks** (Concluído em 2026-05-25: `TenantApiKey`, `WebhookSubscription`, `WebhookDeliveryLog`, migration RLS `20260525o`, `api_key_service.py`, `webhook_service.py`, endpoints `/developer`, fire-and-forget dispatch em `client.created`/`document.uploaded`/`das.paid`, hook `useDeveloper.ts`, aba Desenvolvedor em Configurações, 17 testes passando)

---

# Notas técnicas

- **Stack backend:** Python 3.12 / FastAPI / SQLAlchemy async / Alembic / asyncpg
- **Stack frontend:** React 18 / TypeScript / Vite / Tailwind / TanStack Query / Zustand / Recharts / Framer Motion / Lucide
- **Deploy:** Fly.io (`fiscwise`, https://fiscwise.fly.dev) + Vercel (frontend)
- **DB:** PostgreSQL via Supabase
- **Segurança:** JWT + X-Tenant-ID, RBAC, 2FA TOTP/Email, RLS (parcial)
- **LGPD:** consentimento no tenant, exportação e exclusão via `/account`
- **Bibliotecas a instalar (Fase R4):** `shadcn/ui`, `sonner`, `vaul`, `cmdk`, `@tanstack/react-table`, `driver.js`, `embla-carousel-react`
- **Substituições:** `react-hot-toast` → `sonner` | `TanStack Table` adicional (sem remover Recharts)
