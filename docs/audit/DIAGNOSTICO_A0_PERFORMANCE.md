# Diagnóstico A0 — Stack real, banco e desempenho (2026-11-12)

Relatório base da Frente A da missão noturna. Números medidos na madrugada de
12/11/2026; onde a medição não foi possível a partir da nuvem, está dito.

## 1. Stack real (o documento da missão estava desatualizado)

| Camada | Onde roda | Região | Plano |
|---|---|---|---|
| API FastAPI | Google Cloud Run, serviço `fiscwise-api`, projeto `fiscwise-prod-da9a` | `southamerica-east1` (São Paulo) | pago por uso, `min-instances 0`, `max-instances 1`, 1 vCPU / 1 GiB, concurrency 80, cpu-boost |
| Banco + Storage | Supabase "fiscwise" (ref `sigpsvbkvatzlhbhdmrw`), Postgres 17.11 | `sa-east-1` (São Paulo) | Free |
| Conexão ao banco | Supavisor, `aws-1-sa-east-1.pooler.supabase.com:5432` (modo sessão), usuário `fiscwise_app` | SP | — |
| Front SPA (Vite + React) | Cloudflare Pages, projeto `fiscwise` | borda global | Free |
| DNS | Cloudflare (`fiscwise.com.br`) | — | Free |
| Rotinas agendadas | Cloud Scheduler → `POST /api/v1/internal/tick` de hora em hora | SP | Free |

Neon, Vercel e Fly.io foram excluídos. **Back-end e banco estão na mesma região**
(São Paulo), então o item A1.6 (migração de região) não se aplica.

## 2. Banco de dados (pg_stat_statements já ativo)

Estado em 12/11 03:30 UTC, estatísticas acumuladas desde 25/10:

| Métrica | Valor |
|---|---|
| Tamanho do banco | 14 MB |
| Conexões abertas da aplicação no momento | 0 (Cloud Run estava em zero instâncias) |
| Chamadas SQL do `fiscwise_app` desde 25/10 | 4.616 |
| Tempo total de execução dessas chamadas | 1,58 s (média 0,34 ms por chamada) |
| Cache hit do buffer | 99,99 % |
| Linhas nas tabelas de negócio | 7 tenants, 7 usuários, 6 clientes, 69 eventos de auditoria |

**Conclusão: o banco não é o gargalo.** Nenhuma consulta da aplicação passa de 1 ms
de média; as 20 "mais lentas" são DDL de migração (até 80 ms) e `INSERT`s isolados
(12–32 ms, custo de primeira página). O problema histórico do Neon (quota esgotada
sem uso) era o health check do Fly.io em `/ready` a cada 15 s, já eliminado.

### 2.1 As consultas mais frequentes (o padrão que importa)

| Consulta | Chamadas | Comentário |
|---|---|---|
| `BEGIN` / `ROLLBACK` | 710 / 670 | sessão aberta por requisição; quase tudo é leitura |
| `SELECT set_config('app.current_tenant_id', …)` | 639 | contexto de RLS, 1 por transação |
| `SELECT tenants.*` | 317 | carregado **em toda requisição autenticada** |
| `SELECT users.*` | 294 | idem (`get_current_user`) |
| `SELECT tenant_subscriptions.*` | 257 | idem (`Tenant.subscription`, `lazy="selectin"`) |
| `WITH RECURSIVE typeinfo_tree …` (introspecção do asyncpg) | 115 | 1 por conexão nova: cada cold start do Cloud Run recria o pool |
| `DISCARD ALL` | 98 | reset do pooler ao devolver a conexão (3,7 ms cada) |
| `SELECT accounting_clients.*` | 70 | listagem completa, sem paginação |

**Padrão N+1 na autenticação:** `User.tenant` e `Tenant.users` são `lazy="selectin"`.
Carregar o usuário do token dispara também o tenant, **todos os usuários do tenant**
e a assinatura: 4 consultas + `set_config` = 5 idas ao banco antes de a rota rodar.
Com Cloud Run e Supabase na mesma região cada ida custa ~1 ms, mas é desperdício
puro e cresce com o número de usuários por escritório.

**Dashboard (`/dashboard/overview`):** 12 consultas sequenciais (6 `count`, 3 `sum`,
3 listagens) na mesma sessão. Pode virar 3 (contagens e somas com `FILTER`).

### 2.2 Advisors do Supabase (performance)

- 14 chaves estrangeiras sem índice (ex.: `fiscal_nfes.client_id`, `obligation_instances.rule_id`,
  `notification_messages.client_id`, `tenant_subscriptions.plan_id`, `whatsapp_messages.tenant_id`).
- 4 índices duplicados (`ix_*` + `uq_*` idênticos em `client_obligation_profiles`,
  `obligation_rules`, `plans`, `portal_magic_tokens`).
- 109 índices nunca usados: esperado com a base quase vazia; não remover agora.

### 2.3 Bug de produção encontrado nos logs do Postgres (11/11 19:19–19:20 UTC)

```
column tax_guides.updated_at does not exist
column ecac_proxies.updated_at does not exist
```

As migrations `f3b145a829ef` (guias) e `e3b145a829ef` (e-CAC) criaram as tabelas
**sem** `updated_at` (e `ecac_fiscal_situations` sem `created_at` nem `updated_at`),
mas os modelos herdam `TenantBase`, que tem as duas colunas. Qualquer `SELECT` do ORM
nessas tabelas falha com 500: **os módulos Guias e Central e-CAC estão quebrados em
produção.** Correção: migration aditiva (vai para a fila de aprovação, regra 2).
Repassado às Frentes B e G.

### 2.4 Segurança (advisor)

- 5 tabelas sem RLS: `alembic_version`, `fiscal_benefits`, `obligation_rules`, `plans`,
  `billing_webhook_events`. São tabelas globais (sem `tenant_id`), lidas pela própria
  API com usuário dedicado; o risco real é só se a chave `anon` do Supabase for exposta
  (o front não usa Supabase client). Fica registrado para o Portão de Segurança.
- Função `current_app_tenant_id` com `search_path` mutável (aviso).

## 3. Egress e conexões

- Egress do Supabase: a aplicação devolveu 58 MB de tuplas desde 02/10 (acumulado de
  todos os usuários). Irrelevante para a cota Free (5 GB/mês).
- O pooler recicla a conexão do servidor a cada 3.600 s (`server lifetime over`);
  com `min-instances 0` o pool do SQLAlchemy (5 + 10 overflow) é recriado a cada
  cold start, daí as 115 introspecções do asyncpg. Trocar para a porta 6543
  (modo transação) é possível (prepared statements já desligados) mas não traz ganho
  com 1 instância; manter 5432.

## 4. Latência da API (p95)

A nuvem desta sessão **não alcança** `*.run.app` nem `fiscwise.com.br` (proxy de
saída devolve 403) e não há credencial do GCP para ler os logs do Cloud Run. O p95
real **não pôde ser medido** aqui. O que dá para afirmar pelo código e pela
configuração:

| Cenário | Estimativa | Por quê |
|---|---|---|
| Cold start (primeira requisição após inatividade) | 3–8 s | `min-instances 0`, imagem `python:3.12-slim`, import de Sentry + SQLAlchemy, criação do pool e introspecção do asyncpg |
| Requisição autenticada aquecida | 15–40 ms | 5 idas ao banco na autenticação + consulta da rota, tudo em SP |
| `/dashboard/overview` aquecido | 30–60 ms | 12 consultas sequenciais |

Para ter o número real, a Frente A3 entrega um workflow `perf-probe` (GitHub
Actions, `workflow_dispatch`) que mede p50/p95 de `/live`, `/health`, `/ready` e
do caminho de autenticação, frio e quente.

### 4.1 Medido em produção pelo `perf-probe` (2026-11-12 05:21 UTC)

Runner do GitHub Actions em `eastus2` (EUA) → Cloud Run em São Paulo, 20
chamadas quentes por endpoint ([run](https://github.com/Vvs2705/FiscWise/actions/runs/43160845588)).
A instância já estava ligada (um run 1 min antes a acordou), então a coluna
"fria" aqui **não** é cold start:

| Endpoint | Status | Fria | p50 | p95 | max |
|---|---|---|---|---|---|
| `GET /live` | 200 | 169 ms | 153 ms | 159 ms | 176 ms |
| `GET /health` | 200 | 150 ms | 151 ms | 157 ms | 308 ms |
| `GET /api/v1/health` | 200 | 150 ms | 151 ms | 160 ms | 276 ms |
| `GET /api/v1/clients` (sem token, pilha inteira de middlewares) | 401 | 148 ms | 151 ms | 163 ms | 307 ms |

Front (`https://fiscwise.com.br/`, HTML de 1,9 KB pela Cloudflare): DNS 103 ms,
TLS 117 ms, TTFB 191 ms.

Leitura: a ida e volta EUA → SP responde por ~140 ms disso; o servidor em si
fica em ~10 ms numa rota sem banco, igual ao estimado. De São Paulo a mesma
chamada deve ficar abaixo de 30 ms. Falta medir o cold start de verdade (rodar o
`perf-probe` depois de 15 min sem tráfego) e uma rota autenticada com banco,
que precisa de token e fica para o dono rodar do PC.

## 5. Web Vitals (front)

Medição local do build de produção (Vite preview) com Playwright, perfil Moto G4,
rede Slow 4G (400 kbps, 400 ms de latência) e CPU 4x mais lenta. Sem CDN e sem
Google Fonts (bloqueadas na nuvem), então é o **custo intrínseco do bundle**:

| Página | FCP | LCP | CLS | Transferido | Requisições |
|---|---|---|---|---|---|
| `/login` | 6,4 s | **8,9 s** | 0,001 | 211 KB | 20 |
| `/register` | 6,6 s | **9,1 s** | 0 | 235 KB | 25 |

Metas do Google: LCP ≤ 2,5 s, CLS ≤ 0,1, INP ≤ 200 ms. O CLS está ótimo; o LCP em
rede lenta está 3,5x acima da meta.

### 5.1 Depois da Frente C (PR #72, mesclado na `main` em 2026-11-12)

Mesma medição (build de produção local, Vite preview, Moto G4, Slow 4G, CPU 4x),
mediana de 3 rodadas, sobre a `main` com o PR #72 (chunk de entrada de 45 KB
para 8 KB gzip; `vendor-motion` fora do caminho crítico do login):

| Página | FCP antes → depois | LCP antes → depois | CLS | Transferido | Requisições |
|---|---|---|---|---|---|
| `/login` | 6,4 s → **6,0 s** | 8,9 s → **6,1 s** (−31%) | 0 | 211 → 221 KB | 20 → 27 |
| `/register` | 6,6 s → **5,9 s** | 9,1 s → **6,9 s** (−24%) | 0 | 235 → 202 KB | 25 → 31 |

O ganho vem do primeiro render acontecer antes de baixar o resto: o total
transferido quase não muda (os chunks viraram lazy), mas o LCP cai 2,8 s no
login. Ainda falta 2,4x para a meta de 2,5 s em Slow 4G; o próximo degrau é o
CSS (72 KB bruto num arquivo só) e `vendor-react` + `vendor-form` no caminho
crítico. Em rede 4G normal e com CDN o número real é bem menor; o `perf-probe`
(Actions) mede isso em produção.

Bundle de produção (gzip): `vendor-react` 54 KB, `index` 45 KB, `vendor-motion`
(framer-motion) 42 KB, `vendor-utils` 28 KB, `vendor-form` 23 KB, `vendor-query`
13 KB, CSS 72 KB bruto. A página de login carrega framer-motion e o formulário
inteiro antes do primeiro paint. Pontos para a Frente C: tirar framer-motion do
caminho crítico do login, `font-display` já é `swap` (ok), preload do CSS, e
dividir `index` (149 KB) que concentra Sidebar, stores e utilitários.

E2E: atualizado em 13/11/2026. `frontend/playwright.config.ts` existe e o CI roda
o job `frontend-e2e` (opcional, `continue-on-error`), só nas páginas públicas com
`vite preview`, sem backend. O E2E offline ainda depende de um backend de preview.

## 6. Integrações externas (A2)

Todas as chamadas `httpx` já têm timeout (15–30 s): Supabase Storage, Resend,
Mercado Pago, OpenAI, SERPRO, webhooks de saída. Falta: **retry com backoff** e
mensagem clara ao usuário quando o serviço externo falha; a consulta de CNPJ é feita
no front. Não existe fila de trabalho: o parse de documentos usa `BackgroundTasks`
do FastAPI (morre se a instância do Cloud Run for desligada) e a cobrança mensal
roda inteira dentro do tick horário.

Cache: `plans` e `obligation_rules` são lidos do banco a cada uso; o front já
cacheia planos por 30 min. Redis não está configurado (REDIS_URL vazio) e o
rate limit de admin cai para "desligado" sem ele.

## 7. Monitoramento (A3)

- Sentry está no código (back e front) mas `SENTRY_DSN`/`VITE_SENTRY_DSN` estão
  vazios em produção: nenhum erro é capturado hoje.
- Não há Web Analytics nem Web Vitals em produção (Vercel Speed Insights não se
  aplica mais; o equivalente grátis é **Cloudflare Web Analytics**, que exige um
  token criado no painel do Cloudflare → pendência do dono).
- Logs do Cloud Run são texto solto; não há duração por requisição.

## 8. O que a Frente A faz com isso

| Tarefa | PR | Toca em | Merge |
|---|---|---|---|
| A1 Auth em 1 consulta (5 → 2), dashboards agregados (13 → 5 e 9 → 4), paginação com teto nas listagens, `lazy` correto nos relacionamentos | [#73](https://github.com/Vvs2705/FiscWise/pull/73) | código (auth) | **fila de aprovação** (toca em auth) |
| A1 Migration: 8 colunas faltantes (guias, e-CAC, fiscal_nfes, invoice_events, invoice_rejections, whatsapp_messages), 14 índices nas FKs, remoção dos 4 índices duplicados | [#76](https://github.com/Vvs2705/FiscWise/pull/76) | migration | **fila de aprovação** |
| A2 Retry/backoff + 503 claro nas integrações; cache em memória de `plans`/`obligation_rules`; SERPRO em paralelo (4 por vez) | [#71](https://github.com/Vvs2705/FiscWise/pull/71) | código | **mesclado** |
| A2 Fila em Postgres (`background_jobs`) com tick horário, `GET /jobs`, parse de documento e `invoice.emit` para a Frente G | [#77](https://github.com/Vvs2705/FiscWise/pull/77) | migration + fluxo fiscal | **fila de aprovação** |
| A3 Cloudflare Web Analytics (token opcional), log JSON com duração por requisição, Web Vitals, Playwright com perfis mobile e Slow 4G, workflow `perf-probe` | [#75](https://github.com/Vvs2705/FiscWise/pull/75) | código/CI | **mesclado** |
