# FiscWise — Progresso de Implementação

> Atualizado em: 2026-05-24
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

**Commit:** Pendente

---

## 📋 FASE R2 — Login premium

> A primeira impressão do produto. Deve vender antes do usuário entrar.

- [ ] Quebrar `LoginPage.tsx` em componentes menores:
  - [ ] `LoginBrandPanel.tsx` — painel esquerdo com narrativa visual
  - [ ] `LoginForm.tsx` — formulário limpo
  - [ ] `FloatingMetricCards.tsx` — cards animados (obrigações, documentos, certificados)
  - [ ] `FiscalRadarAnimation.tsx` — radar fiscal com pontos de clientes e status
  - [ ] `OtpInput.tsx` — 6 caixas OTP com microinteração por dígito (substituir o atual)
- [ ] Aplicar paleta escura + glassmorphism no card de login
- [ ] Implementar aurora background animada no painel esquerdo
- [ ] Atualizar headline: "Controle sua carteira contábil com precisão."
- [ ] Atualizar subheadline voltada ao contador autônomo
- [ ] Microinterações: fade in painel, slide up formulário, stagger nos cards, hover teal nos inputs
- [ ] Melhorar responsividade mobile (painel esquerdo some em mobile, formulário ocupa tela toda)

**Critério de conclusão:** login causa boa primeira impressão, radar fiscal aparece, cards flutuam.

---

## 📋 FASE R3 — Dashboard cockpit ("Sua rotina de hoje")

> Substituir dashboard genérico por cockpit diário que responde: "O que preciso fazer hoje?"

- [ ] Quebrar `DashboardPage.tsx` em componentes de feature:
  - [ ] `DashboardHero.tsx` — boas-vindas com nome do usuário e data
  - [ ] `DailyFocusCard.tsx` — card principal com resumo das pendências do dia
  - [ ] `MetricsGrid.tsx` — KPIs acionáveis (obrigações hoje, clientes com pendência, docs aguardando, certs vencendo)
  - [ ] `ClientAttentionList.tsx` — lista com score de risco por cliente (Alto/Médio/Baixo/Regular)
  - [ ] `FiscalWeekTimeline.tsx` — agenda fiscal da semana em formato timeline
  - [ ] `PendingDocumentsCard.tsx` — documentos aguardando conferência
  - [ ] `MonthlyClosingCard.tsx` — progresso de fechamentos da competência atual
  - [ ] `PortfolioRiskCard.tsx` — score 0-100 da saúde da carteira
  - [ ] `QuickActions.tsx` — ações rápidas (novo cliente, nova obrigação, upload documento)
- [ ] Remover `ProductivityPanel` (por colaborador) do MVP — mover para configurações avançadas
- [ ] Ajustar métricas para contador autônomo (remover métricas de equipe)
- [ ] Criar endpoint `GET /dashboard/portfolio-health` (score 0-100)

**Critério de conclusão:** dashboard mostra prioridades reais do dia, sem linguagem de equipe.

---

## 📋 FASE R4 — Design system premium

> Sem design system, cada tela fica inconsistente. Esta fase cria a base reutilizável.

- [ ] Instalar e configurar `shadcn/ui` (customizado com tokens FiscWise — não usar visual padrão)
- [ ] Instalar `sonner` (substituir `react-hot-toast`)
- [ ] Instalar `vaul` (drawers)
- [ ] Instalar `cmdk` (command palette)
- [ ] Instalar `@tanstack/react-table`
- [ ] Instalar `driver.js`
- [ ] Instalar `embla-carousel-react`
- [ ] Criar `Button` com variantes premium (primary, secondary, ghost, danger, premium com gradiente teal)
- [ ] Criar `Card` com variantes (MetricCard, ActionCard, RiskCard, DocumentCard, CertificateCard)
- [ ] Criar `Badge` / `StatusPill` com variantes (regular, attention, critical, pending, completed, overdue, paid, expiring)
- [ ] Criar `Drawer` base usando Vaul
- [ ] Criar `Table` base usando TanStack Table
- [ ] Criar `CommandMenu` (`Ctrl+K`) com busca de clientes e ações rápidas
- [ ] Criar `EmptyState` premium (ilustração + CTA — substituir o atual)
- [ ] Criar `LoadingSkeleton` consistente para todas as telas
- [ ] Criar `ProgressRing` para score da carteira
- [ ] Criar `FiscalTimeline` para timeline de cliente

**Critério de conclusão:** componentes existem, são usados nas novas telas, command palette funciona com `Ctrl+K`.

---

## 📋 FASE R5 — Tabelas e drawers nas telas principais

> Elevar a qualidade visual das telas mais usadas.

- [ ] **Clientes** — refatorar com TanStack Table:
  - [ ] Colunas: nome, CPF/CNPJ, regime, status, pendências, última interação, ação
  - [ ] Badge de risco por cliente (Alto/Médio/Baixo/Regular)
  - [ ] Busca rápida com debounce
  - [ ] Filtros por regime tributário e status
  - [ ] Visualização em lista e cards (toggle)
  - [ ] `ClientDetailsDrawer` — drawer lateral com: Resumo / Documentos / Obrigações / Guias / Certificados / Financeiro / Histórico / Notas internas
  - [ ] Rota `/clientes/:id` com página dedicada de detalhe
- [ ] **Documentos** — refatorar:
  - [ ] Drag & drop premium para upload
  - [ ] `DocumentPreviewDrawer` com preview inline
  - [ ] Status: Recebido / Aguardando conferência / Aprovado / Rejeitado / Pendente do cliente
  - [ ] Filtros por tipo, cliente, competência
- [ ] **Agenda Fiscal** — refatorar:
  - [ ] Visualização calendário + lista + semana
  - [ ] Filtros por cliente e tipo de obrigação
  - [ ] Marcar como concluído com animação
  - [ ] Transformar prazo em tarefa com 1 clique
- [ ] **Obrigações** — refatorar:
  - [ ] Status visual: Pendente / Em andamento / Aguardando cliente / Concluída / Atrasada
  - [ ] `CreateObligationDrawer` (criação rápida sem sair da tela)
- [ ] **Certificados** — cards com barra de vencimento + botão "avisar cliente"
- [ ] **Financeiro** — métricas: Recebido no mês / A receber / Em atraso / Clientes inadimplentes / Ticket médio

**Critério de conclusão:** tabelas das 5 telas principais usam TanStack Table, drawers funcionam, busca e filtros operam.

---

## 📋 FASE R6 — Aba "Aprender" + Onboarding

> Reduzir abandono, acelerar ativação e aumentar percepção de valor.

- [ ] Criar rota `/aprender` com `LearningPage.tsx`
- [ ] Criar `GettingStartedChecklist` — checklist de ativação no dashboard (some quando completo)
- [ ] Criar cards de tutorial estáticos para os primeiros conteúdos:
  - Como cadastrar seu primeiro cliente
  - Como criar uma obrigação fiscal
  - Como organizar documentos por cliente
  - Como controlar certificados digitais
  - Como usar a calculadora fiscal
- [ ] Adicionar botão "Aprender sobre esta tela" em cada página (abre overlay contextual)
- [ ] Instalar e configurar `Driver.js` para tours guiados:
  - [ ] Tour do Painel (5 passos)
  - [ ] Tour de Clientes (4 passos)
  - [ ] Tour da Agenda Fiscal (4 passos)
  - [ ] Tour de Documentos (3 passos)
- [ ] Criar fluxo de onboarding no primeiro login:
  - Tela "Bem-vindo" com escolha de perfil (MEI / Simples / Lucro Presumido / etc.)
  - Cadastrar primeiro cliente
  - Criar primeira obrigação
  - Tour do painel
- [ ] Backend: `user_onboarding_state` — campo JSON em `users` para rastrear tours concluídos

**Critério de conclusão:** usuário novo sabe o que fazer ao entrar, tour funciona, aba Aprender tem conteúdo útil.

---

## 📋 FASE R7 — Diferenciais únicos

> Recursos que nenhum concorrente genérico tem. Fazem o produto ser lembrado.

- [ ] **Modo Foco** — resolver pendências uma por vez:
  - Card "Iniciar Modo Foco" no dashboard
  - Interface 1 tarefa por vez com contexto do cliente
  - Ações: Resolver / Adiar / Aguardando cliente / Pular
- [ ] **Score da Carteira** — saúde 0-100:
  - Endpoint `GET /dashboard/portfolio-health`
  - Card visual com `ProgressRing` e 3 pontos de atenção
  - Cálculo: obrigações atrasadas, docs pendentes, certs vencendo, guias em aberto, recebíveis em atraso
- [ ] **Timeline do Cliente** — histórico cronológico em `/clientes/:id`:
  - Documentos recebidos, obrigações concluídas, guias enviadas, certificados cadastrados
  - Visual tipo feed com ícone + data + descrição
- [ ] **Templates de mensagem** — textos prontos para WhatsApp/e-mail:
  - "Seus documentos do mês ainda não chegaram"
  - "Sua guia DAS vence em X dias"
  - "Seu certificado digital vence em X dias"
- [ ] **Relatório simples por cliente** — exportar PDF com situação do cliente:
  - Obrigações do período, documentos, guias, situação financeira

**Critério de conclusão:** Modo Foco funciona, Score da Carteira exibe no painel, Timeline aparece no detalhe do cliente.

---

# PARTE C — Pendências técnicas e backlog

## 📋 Pendências técnicas

- [ ] **RLS — próxima fatia**: policies para auth, portal magic link, subscriptions, webhooks, notification templates globais
- [ ] **5.13 complemento** — tela de upgrade de plano (frontend Asaas)
- [ ] **Limpeza de docs** — referências `contaflow.fly.dev` ainda existem em:
  `DEPLOYMENT_SUMMARY.md`, `PRODUCTION_STATUS.md`, `README.md`, `README_DEPLOYMENT.md`,
  `FRONTEND_DEPLOYMENT_CHECKLIST.md`, `frontend/FRONTEND_README.md`,
  `docs/VALIDACAO_ONLINE_FISCWISE.md`, `backend/alembic/env.py`, `ROADMAP.md`

## 📋 Backlog — Fase 6 do plano original

- [ ] **5.17 — WhatsApp Business API**
- [ ] **5.18 — Monitor fiscal via parceiro**
- [ ] **5.19 — RAG fiscal** (busca em legislação)
- [ ] **5.20 — API pública + Webhooks**

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
