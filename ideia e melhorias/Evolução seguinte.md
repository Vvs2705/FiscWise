# FiscWise — Evolução Seguinte

**Versão:** 1.0  
**Data:** 24/05/2026  
**Baseado em:** Análise técnica do repositório + Plano Estratégico Técnico e Comercial  
**Status:** Plano de ação vivo — atualizar conforme execução

---

## Contexto

O FiscWise está em estágio de MVP funcional. O produto roda, tem multi-tenant, autenticação, módulos básicos de clientes, documentos, prazos, certificados, financeiro, calculadora fiscal e DAS mensal. A stack é moderna e adequada. O problema não é técnico de linguagem — é de profundidade de produto, segurança, arquitetura de serviços e diferenciais competitivos.

Este documento define o que fazer a seguir: o que limpar, o que manter, o que mudar e o que construir.

---

## 1. Limpeza já executada

Os seguintes arquivos foram removidos nesta sessão por serem resíduos do projeto anterior (ContaFlow) sem qualquer importação ou uso no FiscWise:

| Arquivo removido | Motivo |
|---|---|
| `frontend/src/lib/ctflowData.ts` | Arquivo órfão do ContaFlow com dados mock hardcoded. Nenhum arquivo importava este módulo. |
| `package-lock.json` (raiz) | Lock file na raiz sem `package.json` correspondente. Gerado no passado quando o projeto tinha outra estrutura. |

O seguinte arquivo foi corrigido:

| Arquivo | Correção |
|---|---|
| `backend/requirements.txt` | Header comentado dizia "ContaFlow Backend Dependencies / Python 3.11+" — corrigido para "FiscWise Backend Dependencies / Python 3.12+" |

---

## 2. O que ainda precisa ser removido ou desativado

### 2.1 — Remover imediatamente

| Arquivo | Motivo | Ação |
|---|---|---|
| `infra/postgres/init.sql` | Script de init do banco ainda referencia `contaflow_db`, `contaflow_app` e banco ContaFlow. O projeto usa Supabase, não container local. Arquivo não é executado por nenhum processo atual. | **Deletar** o arquivo ou reescrever do zero referenciando FiscWise |
| `.venv/` na raiz do projeto | Existe um `.venv` na raiz E um `backend/.venv`. O `.venv` da raiz é resíduo. O ambiente correto é `backend/.venv`. | **Deletar** `.venv` da raiz. Confirmar que `.gitignore` da raiz exclui ambos os `.venv` |
| `frontend/src/pages/BillingPage.tsx` | Arquivo com 5 linhas que só faz `<Navigate to="/financeiro" replace />`. A rota `/billing` já está configurada como redirect direto no `App.tsx`. O arquivo pode ser eliminado e a rota simplificada para redirect inline. | **Deletar** arquivo. Manter redirect inline no `App.tsx` |

### 2.2 — Desativar em produção (não deletar ainda)

| Arquivo | Situação | Ação |
|---|---|---|
| `backend/app/api/v1/endpoints/admin.py` | Contém endpoints de emergência (`/fix-enum-case`, `/fix-enum-case-raw`) criados para corrigir um bug de migração de enum que já foi resolvido pelas migrations `20260520_fix_enum_case`. Esses endpoints existem expondo superfície de ataque. Estão protegidos por `ADMIN_OPERATIONS_ALLOWED=false` por padrão, mas o código permanece na base. | **Remover** os endpoints de fix-enum (bug já resolvido). **Manter** apenas os endpoints de gestão de plano (`/set-plan-by-email`, `/tenant-by-email`) que ainda são úteis para operação. |
| `backend/app/api/v1/endpoints/diagnostic.py` | Endpoints de debug que expõem informações internas de banco (enum values, migration history). Restrito a `owner` por RBAC, o que é aceitável, mas deve ser movido para um blueprint de admin interno ou protegido por feature flag de ambiente. | **Mover** para módulo `admin` ou proteger com env var `DIAGNOSTICS_ENABLED`. Em produção real, esse endpoint não deve existir sem proteção adicional de IP allowlist. |

---

## 3. O que deve ser MANTIDO (base sólida)

Os itens abaixo estão corretos e não devem ser tocados agora:

| Item | Por quê manter |
|---|---|
| **Stack FastAPI + SQLAlchemy async + asyncpg** | Moderna, adequada para o domínio. Não há gargalo de performance que justifique troca de linguagem agora. |
| **Multi-tenant por `tenant_id` em todas as tabelas** | Decisão correta desde o início. Fundação de SaaS sólida. |
| **UUID em todos os IDs** | Correto para SaaS distribuído e exposição segura. |
| **Alembic com migrations versionadas** | Processo correto. As 11 migrations refletem evolução real. |
| **RBAC básico (owner/admin/member/client)** | A estrutura de roles está correta. Falta aplicar de forma mais granular nos endpoints. |
| **Pydantic v2 + schemas separados dos models** | Separação correta. |
| **TanStack Query no frontend** | Correto. Cache, loading states e refetch automático. |
| **Lazy loading de páginas no React** | Já implementado em `App.tsx`. Reduz bundle inicial. |
| **`plan_access.py` com controle de planos** | Estrutura boa. Deve ser expandida conforme novos planos. |
| **Lifespan context manager no FastAPI** | Correto. Substitui `on_event` deprecado. |
| **APScheduler para billing mensal** | Funcional para MVP. Ver nota de melhoria abaixo. |
| **Rate limiting Redis-backed com fail-open** | Estrutura correta. Problema: "fail open" sem Redis é inseguro em produção. |

---

## 4. O que deve ser ALTERADO (melhorar o que existe)

### 4.1 Backend — Arquitetura

**Problema:** Os endpoints em `operations.py` são monolíticos. Toda lógica de negócio está nos routers, sem camada de serviço ou repositório.

**Ação:** Extrair para estrutura de domínios:
```
backend/app/
  domain/
    clients/
      service.py       ← lógica de negócio de clientes
      repository.py    ← queries de banco
      schemas.py       ← schemas específicos do domínio
    obligations/
      service.py
      repository.py
    documents/
      service.py
      repository.py
    billing/
      service.py
      repository.py
    notifications/
      service.py
      templates.py
```

**Prioridade:** P1 — fazer antes de adicionar novos endpoints grandes.

---

### 4.2 Backend — Scheduler (APScheduler)

**Problema atual em `services/scheduler.py`:**
- A task `generate_monthly_billing_scheduled` cria um novo engine de banco **dentro do job** (`create_async_engine(settings.DATABASE_URL)`). Isso abre conexões extras, não usa o pool da aplicação, e pode vazar conexões se o job falhar.
- APScheduler rodando in-process junto com a API significa que se a API reiniciar, o job pendente é perdido.
- Não há retry automático, dead letter, ou log estruturado de falha.

**Ação:**
- Curto prazo: corrigir o scheduler para receber a `AsyncSession` via injeção, não criar engine próprio.
- Médio prazo: migrar jobs críticos (billing mensal, alertas de vencimento) para fila assíncrona real (Redis + worker separado ou Celery/ARQ).

---

### 4.3 Backend — Rate Limit "Fail Open"

**Problema:** O `RateLimitMiddleware` falha aberto sem Redis (`redis_url=settings.REDIS_URL or None`). Em produção sem Redis configurado, qualquer IP pode fazer requests ilimitadas.

**Ação:** Adicionar variável `RATE_LIMIT_STRICT=true` no ambiente de produção. Se Redis não disponível e strict mode ativo, retornar 503 em vez de abrir tudo.

---

### 4.4 Backend — Segurança de tokens JWT

**Problema:** JWT é armazenado em `localStorage` no frontend (padrão atual via `authStore.ts`). Isso é vulnerável a XSS.

**Ação:** Avaliar migração para cookie `HttpOnly` + `SameSite=Strict` para o access token. Criar refresh token com maior TTL em cookie seguro. Manter `localStorage` apenas para dados não-sensíveis (preferências de UI).

---

### 4.5 Backend — Storage de documentos

**Problema:** Os modelos `ClientDocument` e `CompanyDocument` têm campo `file_url` como string simples. Se o storage for público (padrão Supabase), qualquer pessoa com a URL acessa o arquivo.

**Ação:**
- Configurar bucket do Supabase como **privado**.
- Todos os endpoints que retornam documentos devem gerar **URL assinada** com TTL curto (15-60 min) em vez de retornar a URL permanente.
- Nunca expor a `storage_key` diretamente ao cliente.

---

### 4.6 Frontend — Controle de permissões nas rotas e ações

**Problema:** O `ProtectedRoute` apenas verifica se o usuário está autenticado. Não há controle de role nas rotas nem nas ações (botões, formulários).

**Ação:**
- Criar hook `usePermission(role: UserRole)` que consulta o store de auth.
- Envolver ações destrutivas (deletar cliente, alterar plano) com `RequireRole` component.
- Ocultar seções de configurações avançadas de usuários com role `member`.

---

### 4.7 Frontend — Design system

**Problema:** Componentes UI em `components/ui/` são básicos e inconsistentes. Tailwind classes espalhadas diretamente nas páginas criam inconsistência visual.

**Ação:**
- Criar tokens de design no Tailwind config (cores semânticas, spacing, bordas).
- Expandir `components/ui/` com: `Table`, `Modal`, `Tabs`, `Toast`, `Spinner`, `EmptyState`, `ErrorState`, `Skeleton`.
- Documentar internamente: cada componente novo deve ter variantes definidas.

---

### 4.8 Backend — Validação de CPF/CNPJ

**Problema:** Os campos `document` (CNPJ/CPF) em `AccountingClient` e `Tenant` são strings simples sem validação de formato ou dígito verificador.

**Ação:** Adicionar validação via Pydantic validator no schema de criação/edição de clientes. Usar biblioteca `brutils` ou implementar validação pura para CPF e CNPJ com cálculo de dígito verificador.

---

### 4.9 Backend — Testes

**Problema:** `backend/tests/__init__.py` é o único arquivo de teste. Zero cobertura real.

**Ação:** Criar testes para os fluxos críticos:
1. Registro + login + JWT válido.
2. Criação de cliente com isolamento de tenant (cliente de tenant A não aparece para tenant B).
3. Upload de documento → status → URL assinada.
4. Criação de recebível + scheduler de billing.
5. Plan access control (feature bloqueada em plano free).

---

## 5. O que deve ser IMPLEMENTADO DO ZERO (por prioridade)

### FASE 1 — Fundação robusta (Semanas 1-4)
**Objetivo:** Produto confiável o suficiente para primeiro cliente pagante.

#### 5.1 — Audit Log

Criar tabela `audit_events` e middleware que registra automaticamente:

```sql
audit_events (
  id            uuid primary key,
  tenant_id     uuid not null,
  actor_user_id uuid,
  actor_role    text,
  action        text not null,        -- 'client.create', 'document.upload', 'login.success'
  entity_type   text not null,
  entity_id     uuid,
  before_data   jsonb,
  after_data    jsonb,
  ip_address    inet,
  user_agent    text,
  created_at    timestamptz default now()
)
```

**Registrar obrigatoriamente:** login, logout, falha de autenticação, criação/edição/exclusão de cliente, upload/download de documento, alteração de plano, acesso a certificado.

---

#### 5.2 — CI/CD básico

Criar pipeline GitHub Actions com:
- `lint` (ruff, mypy no backend; eslint, tsc no frontend)
- `test` (pytest no backend)
- `build` (docker build no backend; vite build no frontend)
- Deploy automático para staging em merge na branch `develop`
- Deploy para produção apenas manual com aprovação

---

#### 5.3 — Ambiente staging separado

Criar ambiente staging em Fly.io com banco Supabase de staging separado. Nunca testar em produção. Configurar variáveis de ambiente por ambiente.

---

#### 5.4 — Sentry + logs estruturados

Integrar Sentry no backend (`sentry-sdk[fastapi]`) e no frontend (`@sentry/react`). Configurar alertas para erros 5xx. Migrar `logging.basicConfig` para logs estruturados em JSON via `structlog` ou manter `loguru` com formato JSON.

---

#### 5.5 — Índices compostos no banco

Criar migrations com índices compostos que ainda faltam:

```sql
-- Clients
create index if not exists idx_clients_tenant_status
  on accounting_clients(tenant_id, status);

-- Deadlines  
create index if not exists idx_deadlines_tenant_due_status
  on deadline_items(tenant_id, due_date, status);

-- Documents
create index if not exists idx_documents_tenant_client_created
  on client_documents(tenant_id, client_id, created_at desc);

-- DAS Payments
create index if not exists idx_das_tenant_client_period
  on das_payments(tenant_id, client_id, period);

-- Receivables
create index if not exists idx_receivables_tenant_due_status
  on account_receivables(tenant_id, due_date, status);
```

---

### FASE 2 — Produto vendável v1 (Meses 2-3)
**Objetivo:** Diferencial mínimo para vender com convicção.

#### 5.6 — Motor de obrigações fiscais v1

Esta é a funcionalidade mais importante para diferenciação de mercado.

**Novas tabelas necessárias:**

```sql
-- Regras de obrigação (template)
obligation_rules (
  id                    uuid primary key,
  code                  text not null unique,        -- 'DAS', 'DEFIS', 'DCTFWEB', 'SPED_FISCAL'
  name                  text not null,
  jurisdiction          text not null,               -- 'federal', 'estadual', 'municipal'
  state                 char(2),
  applies_to_regimes    text[],                      -- ['simples_nacional', 'lucro_presumido']
  applies_to_entity_types text[],                    -- ['pj', 'mei']
  applies_to_cnaes      text[],                      -- null = todos os CNAEs
  recurrence            text not null,               -- 'monthly', 'quarterly', 'yearly', 'event'
  due_day               int,
  requires_employees    boolean default false,
  active                boolean default true,
  valid_from            date,
  valid_until           date
)

-- Perfil de obrigações por cliente
client_obligation_profiles (
  id                         uuid primary key,
  tenant_id                  uuid not null,
  client_id                  uuid not null unique,
  tax_regime                 text,                   -- 'simples_nacional', 'lucro_presumido', 'lucro_real', 'mei'
  cnae_main                  text,
  cnae_secondary             text[],
  state                      char(2),
  has_employees              boolean default false,
  has_state_registration     boolean default false,
  has_municipal_registration boolean default false,
  updated_at                 timestamptz default now()
)

-- Instâncias geradas (obrigação concreta de um cliente em uma competência)
obligation_instances (
  id               uuid primary key,
  tenant_id        uuid not null,
  client_id        uuid not null,
  rule_id          uuid,
  competence_month date not null,                  -- primeiro dia do mês: 2026-05-01
  due_date         date not null,
  status           text not null default 'pending', -- 'pending', 'in_progress', 'delivered', 'overdue', 'cancelled'
  priority         text not null default 'medium',
  assigned_to      uuid,                           -- user_id
  delivery_proof   text,                           -- URL do comprovante
  completed_at     timestamptz,
  created_at       timestamptz default now()
)
```

**Lógica do motor:**
- Job mensal (dia 1) que gera `obligation_instances` para todos os clientes ativos.
- Filtrar regras aplicáveis por: regime tributário, CNAE, UF, inscrições, porte.
- Calcular `due_date` com base em `due_day` da regra (respeitar feriados no futuro).
- Não gerar duplicata se instância já existe para (client_id, rule_id, competence_month).

**Migrar:** O modelo `DeadlineItem` atual é manual. O motor de obrigações é automático. Os dois devem coexistir: `DeadlineItem` para prazos customizados, `obligation_instances` para obrigações fiscais automáticas.

---

#### 5.7 — Checklist mensal por cliente

Permitir que o escritório configure um checklist de documentos necessários por mês por cliente. Integrado com `obligation_instances`.

**Tabela:**
```sql
document_checklist_items (
  id               uuid primary key,
  tenant_id        uuid not null,
  client_id        uuid not null,
  obligation_id    uuid,             -- pode ser null (checklist manual)
  competence_month date not null,
  document_name    text not null,
  status           text not null default 'pending',  -- 'pending', 'received', 'approved', 'rejected'
  received_at      timestamptz,
  notes            text
)
```

---

#### 5.8 — Portal do cliente v1 completo

O `portal.py` existe mas está incompleto. Construir:
- Tela de login do portal com magic link (email com token de 1 uso, 24h de validade).
- Após login: cliente vê suas pendências do mês atual.
- Upload de documento direto pelo portal (vinculado ao checklist).
- Visualização de guias/documentos enviados pelo escritório.
- Não usar a mesma tela de login do escritório — criar rota separada `/portal/login`.

---

#### 5.9 — Cobrança de documentos por e-mail

Automatizar cobrança de documentos pendentes.

**Fluxo:**
1. Escritório configura: "cobrar documentos pendentes toda segunda-feira às 9h".
2. Sistema verifica clientes com `document_checklist_items.status = 'pending'`.
3. Envia e-mail com lista de pendências e link para o portal.
4. Registra envio em `notification_messages`.

**Tabelas necessárias:**
```sql
notification_templates (
  id        uuid primary key,
  tenant_id uuid,           -- null = template global do sistema
  channel   text not null,  -- 'email', 'whatsapp'
  name      text not null,
  subject   text,
  body      text not null,
  variables jsonb           -- variáveis que podem ser substituídas
)

notification_messages (
  id                  uuid primary key,
  tenant_id           uuid not null,
  client_id           uuid,
  channel             text not null,
  recipient           text not null,
  template_id         uuid,
  body                text not null,
  status              text not null,  -- 'pending', 'sent', 'delivered', 'failed'
  provider            text,           -- 'sendgrid', 'resend', 'smtp'
  provider_message_id text,
  sent_at             timestamptz,
  created_at          timestamptz default now()
)
```

---

#### 5.10 — Honorários recorrentes (melhoria do scheduler atual)

O scheduler atual já gera recebíveis mensais. O que falta:
- Interface no frontend para o escritório configurar: valor, dia de vencimento e reajuste anual por cliente.
- Histórico de cobranças por cliente.
- Régua de cobrança: lembrete antes do vencimento, aviso de atraso (via e-mail).
- Relatório de inadimplência (clientes com recebível `overdue`).

---

#### 5.11 — Dashboard de produtividade do escritório

Painel exclusivo para donos/admins com:
- Obrigações por colaborador (assigned_to).
- Taxa de cumprimento no prazo.
- Clientes com mais pendências.
- Documentos aguardando aprovação.
- Receita total do mês vs meses anteriores (já existe parcialmente).
- Alertas: certificados vencendo em 30 dias, recebíveis em atraso.

---

#### 5.12 — Planos e limites reais

O `plan_access.py` tem 3 planos (free/intermediario/premium) mas sem enforcement de limites reais. Implementar:
- Limite de clientes ativos por plano (ex: starter = 30, pro = 150, business = 500).
- Limite de usuários por plano.
- Contador de uso de IA por mês.
- Endpoint `/api/v1/subscription/usage` para o frontend mostrar uso atual vs limites.
- Bloquear criação de cliente quando atingir limite do plano.

**Tabela de planos:**
```sql
plans (
  id                  uuid primary key,
  slug                text unique not null,
  name                text not null,
  price_monthly       numeric(12,2),
  max_clients         int,
  max_users           int,
  max_ai_calls_month  int,
  features            jsonb,
  active              boolean default true
)
```

---

### FASE 3 — Produto comercial (Meses 4-6)
**Objetivo:** Clientes pagantes reais com billing automático.

#### 5.13 — Gateway de pagamento (Pix/Boleto)

Integrar Asaas ou Iugu (mais aderentes ao mercado brasileiro que Stripe para boleto+Pix recorrente).

**Fluxo:**
1. Escritório cria assinatura no FiscWise.
2. FiscWise cria customer + subscription no gateway.
3. Gateway emite boleto/Pix mensal automaticamente.
4. Webhook do gateway confirma pagamento → atualiza `subscription_status` no tenant.
5. Tenant inadimplente → acesso suspenso após X dias.

**Tabela:**
```sql
tenant_subscriptions (
  id                       uuid primary key,
  tenant_id                uuid not null unique,
  plan_id                  uuid not null,
  status                   text not null,  -- 'active', 'past_due', 'cancelled', 'trialing'
  billing_provider         text,           -- 'asaas', 'iugu'
  provider_customer_id     text,
  provider_subscription_id text,
  current_period_start     timestamptz,
  current_period_end       timestamptz,
  trial_ends_at            timestamptz,
  created_at               timestamptz default now()
)
```

---

#### 5.14 — IA operacional v1

Expandir a IA além da calculadora fiscal para:
1. **Classificação de documento:** ao fazer upload, IA analisa o arquivo e sugere tipo e competência.
2. **Extração de dados:** de guias DAS, notas fiscais, extratos — extrair CNPJ, competência, valor, vencimento.
3. **Resumo do cliente:** gerar texto "O cliente X tem 3 pendências críticas e 1 obrigação vencendo em 2 dias."
4. **Alerta de risco:** "Certificado vence em 8 dias e há obrigação DCTFWeb pendente para este cliente."

**Regras de governança para IA:**
- Nunca enviar dados completos de CPF/CNPJ ao modelo externo — mascarar antes.
- Toda resposta de IA deve ter aviso: "Resultado estimado. Valide com o responsável técnico."
- Registrar prompts e respostas em tabela de log com custo estimado.
- Quota por plano (já existe base no `plan_access.py`).

---

#### 5.15 — LGPD mínimo viável

- Criar Termos de Uso e Política de Privacidade no frontend (páginas estáticas).
- Fluxo de aceite na criação de conta (checkbox + timestamp de aceite).
- Endpoint `/api/v1/account/export` — exportar todos os dados do tenant.
- Endpoint `/api/v1/account/delete` — solicitar exclusão (gera ticket, não exclusão imediata).
- Política de retenção de documentos: definir e documentar.
- DPA (Data Processing Agreement) para clientes B2B — template jurídico.

---

#### 5.16 — Row Level Security no banco

Ativar RLS no PostgreSQL para dupla proteção contra vazamento cross-tenant:

```sql
-- Exemplo para accounting_clients
ALTER TABLE accounting_clients ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON accounting_clients
  USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

O middleware da aplicação deve setar a variável de sessão `app.current_tenant_id` em cada request. Isso garante isolamento no nível do banco mesmo se houver bug na camada de aplicação.

---

### FASE 4 — Diferencial forte (Meses 7-12)
**Objetivo:** Sair de MVP para plataforma.

#### 5.17 — WhatsApp Business API

Integrar via Evolution API (self-hosted) ou Twilio/Zapi (gerenciado).

**Funcionalidades:**
- Solicitação automática de documentos via WhatsApp (template aprovado).
- Caixa de entrada unificada por cliente.
- Transformar mensagem em tarefa.
- Documento recebido via WhatsApp → associado ao checklist automaticamente.
- Dashboard de SLA de atendimento.

---

#### 5.18 — Monitor fiscal via parceiro

Integrar com parceiro (ex: Tecnospeed, Questor) para:
- Busca automática de NF-e na Receita Federal.
- Consulta de situação fiscal do CNPJ.
- Alertas de débitos e irregularidades.
- Download automático de certidões.

---

#### 5.19 — RAG fiscal

Base de conhecimento vetorial para a IA do escritório:
- Alimentar com regras fiscais, manuais, FAQs, histórico.
- IA responde perguntas do contador com base nessa base, não em conhecimento geral do modelo.
- Cada resposta indica a fonte e grau de confiança.
- Permite que o escritório adicione procedimentos próprios.

---

#### 5.20 — API pública + Webhooks

Para integrações com sistemas externos dos clientes:
- Webhooks para: cliente criado, documento recebido, prazo vencido, pagamento confirmado.
- API REST documentada com autenticação por API key.
- SDK simples (opcional, médio prazo).

---

## 6. Ordem de execução recomendada

### Semana 1
- [ ] Deletar `infra/postgres/init.sql` ou reescrever para FiscWise
- [ ] Remover `frontend/src/pages/BillingPage.tsx` (redirect já existe inline no App.tsx)
- [ ] Verificar e deletar `.venv` da raiz do projeto
- [ ] Remover endpoints de fix-enum do `admin.py` (bug já corrigido pelas migrations)
- [ ] Garantir que ambos os `.venv` estão no `.gitignore`
- [ ] Criar ambiente de staging separado (Fly.io + Supabase staging)
- [ ] Integrar Sentry (backend + frontend)

### Semana 2-3
- [ ] Criar pipeline CI/CD no GitHub Actions (lint + test + build)
- [ ] Criar testes para fluxos críticos (auth, tenant isolation, plan access)
- [ ] Criar migration com índices compostos faltantes
- [ ] Corrigir scheduler: não criar engine próprio dentro do job
- [ ] Configurar storage privado + URL assinada no Supabase
- [ ] Criar `audit_events` table + middleware de auditoria

### Semana 4
- [ ] Implementar controle de permissões granular no frontend (hook `usePermission`)
- [ ] Expandir `components/ui/` com componentes ausentes (Table, Skeleton, EmptyState)
- [ ] Adicionar validação de CPF/CNPJ no schema de clientes
- [ ] Migrar auth token para cookie `HttpOnly` ou pelo menos documentar risco de localStorage

### Mês 2
- [ ] Criar `obligation_rules` (seed inicial com DAS, DEFIS, DCTFWeb, ISS mensal)
- [ ] Criar `client_obligation_profiles` e tela para preenchê-los
- [ ] Motor de geração mensal de `obligation_instances`
- [ ] Checklist mensal por cliente
- [ ] Portal do cliente v1 com magic link

### Mês 3
- [ ] Cobrança de documentos por e-mail automático
- [ ] Régua de cobrança de honorários
- [ ] Dashboard de produtividade para owners/admins
- [ ] Enforcement real de limites por plano (clientes, usuários, IA)
- [ ] Tabela `plans` + endpoint de uso

### Mês 4-6
- [ ] Gateway de pagamento (Asaas ou Iugu)
- [ ] IA operacional: classificação e extração de documentos
- [ ] LGPD mínimo viável
- [ ] Row Level Security no banco
- [ ] 3-5 escritórios piloto pagantes

### Mês 7-12
- [ ] WhatsApp Business API
- [ ] Monitor fiscal via parceiro
- [ ] RAG fiscal
- [ ] API pública + webhooks

---

## 7. Riscos e decisões abertas

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Motor de obrigações com regras erradas | Alta | Alto | Especialista contábil validando regras antes de ativar. Resultado marcado como "automático — validar com contador". |
| IA gerando recomendação fiscal incorreta | Média | Alto | Disclaimer obrigatório. Nunca apresentar como parecer definitivo. Log de todas as respostas. |
| Certificado A1 armazenado sem criptografia | Alta | Crítico | **Não armazenar senha do certificado em texto puro nunca.** Avaliar KMS ou parceiro especializado. |
| Scheduler APScheduler perdendo jobs em reinicialização | Média | Médio | Migrar billing crítico para fila persistente (Redis Streams ou Celery) antes de escalar. |
| Storage de documentos público por engano | Alta | Crítico | Auditar bucket Supabase agora. Garantir que é privado. URL assinada obrigatória. |
| Escalabilidade do banco com muitos tenants | Baixa | Alto | Índices compostos resolvem por enquanto. Particionamento quando passar de 500 tenants ativos. |
| Custo de IA disparando | Média | Médio | Quotas por plano (estrutura existe). Cache de respostas similares. Modelo barato para classificação, forte para análise. |

---

## 8. Decisões técnicas fechadas (não reabrir)

| Decisão | Por quê está fechada |
|---|---|
| **Não migrar para Java agora** | Gargalo não é linguagem. Python é adequado para IA/documentos/automação. Reescrita atrasa produto sem ganho real no estágio atual. |
| **Manter Supabase no curto prazo** | Ok para validação. Criar migrations limpas para viabilizar saída quando necessário. Não acoplar com features Supabase-específicas além de storage. |
| **Manter Fly.io no curto prazo** | Ok para início. Subir para 2+ máquinas com staging separado. Avaliar RDS/GCP SP depois de tração real. |
| **Manter Vite + React (não migrar para Next.js)** | Não migrar agora. Next.js só faz sentido se precisar de SSR/SEO. Marketing site pode ser criado separado em Next.js. |
| **Não usar Kubernetes agora** | Kubernetes aumenta complexidade. ECS/Fargate ou Fly Machines quando houver time e volume justificando. |

---

## 9. Checklist de saúde técnica atual

Status do projeto na data deste documento (24/05/2026):

| Item | Status | Ação necessária |
|---|---|---|
| Multi-tenant isolado | ✅ Ok | Adicionar RLS como segunda camada |
| Autenticação JWT | ✅ Ok | Migrar para HttpOnly cookie |
| RBAC básico | ✅ Ok | Aplicar mais granularmente nos endpoints |
| Migrations versionadas | ✅ Ok | Manter padrão |
| Rate limiting | ⚠️ Parcial | Não pode fail-open em produção |
| Storage privado | ❓ Não verificado | Auditar bucket Supabase agora |
| Audit log | ❌ Ausente | Implementar na Fase 1 |
| Testes automatizados | ❌ Ausente | Criar cobertura mínima na Fase 1 |
| CI/CD | ❌ Ausente | Criar na Semana 2 |
| Sentry/observabilidade | ❌ Ausente | Integrar na Semana 1 |
| Ambiente staging | ❌ Ausente | Criar na Semana 1 |
| Motor de obrigações | ❌ Ausente | Implementar na Fase 2 |
| Checklist mensal | ❌ Ausente | Implementar na Fase 2 |
| Portal cliente funcional | ⚠️ Parcial | Completar na Fase 2 |
| Cobrança automática | ❌ Ausente | Implementar na Fase 2 |
| WhatsApp operacional | ❌ Ausente | Implementar na Fase 4 |
| LGPD mínimo | ❌ Ausente | Implementar na Fase 3 |
| Gateway pagamento | ❌ Ausente | Implementar na Fase 3 |

---

*Documento vivo. Atualizar ao completar cada item.*
