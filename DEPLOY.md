# Deploy — FiscWise (stack gratuita, servidores em São Paulo)

Tudo que guarda ou processa dado fica em São Paulo. Todos os serviços têm plano
gratuito agora e plano pago na mesma ferramenta para quando houver clientes.

| Camada | Serviço | Região |
|---|---|---|
| Backend (FastAPI) | Google Cloud Run | `southamerica-east1` |
| Rotinas agendadas | Google Cloud Scheduler → `POST /api/v1/internal/tick` | `southamerica-east1` |
| Segredos | Google Secret Manager | — |
| Banco + arquivos | Supabase (Postgres + Storage) | `sa-east-1` |
| Redis (rate limit) | Upstash | `sa-east-1` |
| Frontend | Cloudflare Pages | CDN |
| DNS / WAF / captcha | Cloudflare | — |
| E-mail | Resend | — |
| Erros / uptime | Sentry / Better Stack | — |
| Backup do banco | GitHub Actions → Cloudflare R2 (criptografado com `age`) | — |

## Como as rotinas agendadas funcionam

No Cloud Run a instância desliga quando não há tráfego, então o APScheduler
dentro do processo não serve. Com `SCHEDULER_MODE=external`:

- o APScheduler não sobe;
- o Cloud Scheduler chama `POST /api/v1/internal/tick` de hora em hora, com o
  header `X-Cron-Secret`;
- o tick roda as rotinas devidas naquela hora (mesmos horários de antes, em
  UTC, definidos em `backend/app/services/scheduler.py`);
- a chamada horária também mantém o Supabase Free ativo (ele pausa após 7 dias
  sem uso).

Em desenvolvimento e no `docker-compose`, o padrão continua `SCHEDULER_MODE=internal`.

## Fila de trabalho em segundo plano (`background_jobs`)

Trabalho que não cabe na requisição (parse de documento, emissão de NFS-e) vai
para a tabela `background_jobs` no Postgres, não para o `BackgroundTasks` do
FastAPI (que morre quando o Cloud Run desliga a instância). Sem Redis, sem
worker fixo, custo zero. Código: `backend/app/services/job_queue.py`.

- **Disparo:** logo após o commit do `enqueue`, a API tenta processar numa task
  própria (best-effort). O que sobrar é processado pela rotina
  `process_job_queue` em todo tick horário (orçamento de 5 min; o deadline do
  Scheduler é 900 s).
- **Concorrência:** `SELECT ... FOR UPDATE SKIP LOCKED`; job `running` há mais de
  15 min é considerado abandonado e volta a rodar.
- **Status:** `GET /api/v1/jobs/{id}` e `GET /api/v1/jobs?status=&limit=` (só do
  escritório do usuário). Front: `useJob(id)` / `useJobs()` em
  `frontend/src/lib/hooks/useJobs.ts`.

Contrato para registrar um novo tipo de job:

```python
from app.services.job_queue import JobContext, job_handler

@job_handler("dominio.acao")
async def handler(ctx: JobContext) -> dict | None:
    ...  # ctx.db já tem o contexto RLS de ctx.tenant_id
```

| Regra | Valor |
|---|---|
| `kind` | `"<domínio>.<ação>"`; o módulo do handler entra em `HANDLER_MODULES` |
| `payload` | JSON pequeno, só IDs |
| `idempotency_key` | `"<kind>:<id>"`; repetir o `enqueue` devolve o mesmo job |
| Retry | exceção → nova tentativa em 1 min, 5 min, 25 min (`max_attempts` = 3); `JobRetry(delay_s)` escolhe o atraso; `PermanentJobError` falha sem retry |
| Idempotência do handler | obrigatória: o job pode rodar de novo se a instância morrer no meio |

Kinds existentes:

| kind | payload | chave | o que faz |
|---|---|---|---|
| `document.parse` | `{"document_id", "storage_path", "file_name", "tmp_path"}` | `document.parse:<document_id>` | parse do upload em `POST /clients/{id}/documents` (a resposta traz `job_id`) |
| `invoice.emit` | `{"invoice_id", "tenant_id"}` | `invoice.emit:<invoice_id>` | emite a nota que está em status **`queued`** pelo `InvoiceService.process_emission_sync` (provedor atual: simulação). Nota fora de `queued` é ignorada. Falha de conexão com o provedor devolve a nota para `queued` (evento `emit_retry`) e agenda retry; rejeição segue o domínio (`invoice_rejections` + evento) |

Varredor: em todo tick, `drain_queued_invoices` enfileira `invoice.emit` para
toda nota em `queued` há mais de 10 min sem job pendente (a chave impede
duplicar). Quem põe a nota em `queued` (ex.: `/sync/push` offline) não precisa
enfileirar: basta deixá-la em `queued`. Offline nunca autoriza a emissão.

## E-mail transacional (Resend)

Tudo o que o sistema envia passa por `backend/app/services/email_service.py`:
código de acesso (2FA), ativação do 2FA, redefinição de senha, pedido de
exclusão de dados (LGPD), link de acesso do portal do cliente, aviso de
documentos pendentes, lembrete de pagamento e alerta de certificado vencendo.
Sem `RESEND_ENABLED=true` e `RESEND_API_KEY`, nada é enviado: o envio só fica
no log e as telas que dependem dele avisam ou escondem a opção.

| Variável | Onde fica | Valor |
|---|---|---|
| `RESEND_ENABLED` | `cloudrun.env.yaml` | `"true"` |
| `RESEND_API_KEY` | Secret Manager (`RESEND_API_KEY`) | chave `fiscwise-api`, Sending access, domínio fiscwise.com.br |
| `RESEND_FROM` | opcional | padrão `FiscWise <nao-responda@fiscwise.com.br>` |

O domínio fiscwise.com.br está verificado no Resend (região sa-east-1), com
DKIM, SPF e DMARC no Cloudflare. Para trocar a chave, crie uma versão nova do
segredo e faça um deploy:

```
printf '%s' 'NOVA_CHAVE' | gcloud secrets versions add RESEND_API_KEY --data-file=- --project fiscwise-prod-da9a
```

Teste manual com a chave no ambiente local:
`cd backend && RESEND_ENABLED=true RESEND_API_KEY=... python -m app.services.email_service voce@exemplo.com`

## Passo a passo

Os comandos abaixo usam o `gcloud` (Cloud Shell no navegador já vem com ele).
Troque `PROJECT_ID` pelo ID do projeto criado.

### 1. Contas

Criar no e-mail da empresa, com 2FA por aplicativo e dois administradores:
Google Cloud, Supabase, Upstash, Cloudflare, Resend, Sentry, Better Stack e
Bitwarden (cofre de senhas).

No Google Cloud, criar um alerta de orçamento de US$ 5
(Faturamento → Orçamentos e alertas).

### 2. Supabase

1. Novo projeto na região **South America (São Paulo)**. Deixe o Supabase gerar
   a senha do banco e guarde-a no cofre.
2. Storage: criar o bucket de documentos como **privado**.
3. Copiar a connection string do **Session pooler** (porta 5432, IPv4). Ela é
   usada em `DATABASE_URL` e em `BACKUP_DATABASE_URL`. O Cloud Run não tem saída
   IPv6, então a conexão direta do Supabase não funciona.
4. Copiar `SUPABASE_URL` e a chave secreta (service role) para `SUPABASE_SECRET_KEY`.

### 3. Upstash (opcional)

Só quando o Cloud Run passar de uma instância: com uma instância o rate limit
conta em memória. Banco Redis na região **São Paulo (sa-east-1)**. Copiar a URL
`rediss://...` para `REDIS_URL`.

### 4. Google Cloud

```bash
gcloud config set project PROJECT_ID
gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
  secretmanager.googleapis.com cloudscheduler.googleapis.com \
  iamcredentials.googleapis.com

# Repositório de imagens em São Paulo
gcloud artifacts repositories create fiscwise \
  --repository-format=docker --location=southamerica-east1

# Conta de serviço que o backend usa em produção (só lê segredos)
gcloud iam service-accounts create fiscwise-api
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:fiscwise-api@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Conta de serviço que o GitHub Actions usa para deploy
gcloud iam service-accounts create fiscwise-deployer
# secretmanager.viewer: só vê se o segredo existe (não lê o valor). O deploy
# usa isso para montar os segredos do Mercado Pago sozinho.
for ROLE in roles/run.admin roles/artifactregistry.writer roles/secretmanager.viewer; do
  gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:fiscwise-deployer@PROJECT_ID.iam.gserviceaccount.com" \
    --role="$ROLE"
done
gcloud iam service-accounts add-iam-policy-binding \
  fiscwise-api@PROJECT_ID.iam.gserviceaccount.com \
  --member="serviceAccount:fiscwise-deployer@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# Workload Identity Federation: o GitHub entra sem chave JSON guardada
gcloud iam workload-identity-pools create github --location=global
gcloud iam workload-identity-pools providers create-oidc github \
  --location=global --workload-identity-pool=github \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository=='Vvs2705/FiscWise'"
PROJECT_NUMBER=$(gcloud projects describe PROJECT_ID --format='value(projectNumber)')
gcloud iam service-accounts add-iam-policy-binding \
  fiscwise-deployer@PROJECT_ID.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github/attribute.repository/Vvs2705/FiscWise"
```

### 5. Segredos (Secret Manager)

Obrigatórios para o deploy:

```bash
printf '%s' 'postgresql://...pooler.supabase.com:5432/postgres' | gcloud secrets create DATABASE_URL --data-file=-
openssl rand -hex 64 | tr -d '\n' | gcloud secrets create JWT_SECRET_KEY --data-file=-
printf '%s' 'CHAVE_SERVICE_ROLE'  | gcloud secrets create SUPABASE_SECRET_KEY --data-file=-
openssl rand -hex 32 | tr -d '\n' | gcloud secrets create CRON_SECRET --data-file=-
```

Opcionais (crie quando for usar e liste em `CLOUD_RUN_EXTRA_SECRETS`, passo 6):
`REDIS_URL` (só quando o serviço passar de uma instância; sem ele o rate limit da API inteira conta em memória do processo), `OPENAI_API_KEY`, `SENTRY_DSN`, `RESEND_API_KEY`, `WHATSAPP_WEBHOOK_SECRET`.
Os três do Mercado Pago (`MERCADO_PAGO_ACCESS_TOKEN`, `MERCADO_PAGO_PUBLIC_KEY`,
`MERCADO_PAGO_WEBHOOK_SECRET`) não precisam entrar na lista: ver passo 10.

Nunca coloque esses valores em `.env` versionado, `.mcp.json`, README ou chat.

### 6. Variáveis do repositório no GitHub

Settings → Secrets and variables → Actions → **Variables**:

| Variável | Valor |
|---|---|
| `GCP_PROJECT_ID` | ID do projeto (liga o workflow de deploy) |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github/providers/github` |
| `GCP_DEPLOY_SERVICE_ACCOUNT` | `fiscwise-deployer@PROJECT_ID.iam.gserviceaccount.com` |
| `SUPABASE_URL` | URL do projeto Supabase |
| `GOOGLE_CLIENT_ID` | Client ID do Google OAuth |
| `CLOUD_RUN_EXTRA_SECRETS` | Opcional, ex.: `OPENAI_API_KEY=OPENAI_API_KEY:latest,SENTRY_DSN=SENTRY_DSN:latest` |

Criar também o environment **production** (Settings → Environments), usado
pelos workflows de deploy e backup.

### 7. Primeiro deploy

Actions → **Deploy backend (Cloud Run)** → Run workflow. Ele:

1. constrói a imagem e envia ao Artifact Registry em São Paulo;
2. roda as migrations num Cloud Run Job (`python run_migrations.py`);
3. publica o serviço `fiscwise-api` (`min-instances=0`, `max-instances=1`, 1 vCPU, 1 GiB);
4. testa `/ready`.

Depois disso, todo merge na `main` que mexer em `backend/` faz deploy sozinho.

A URL do serviço (`https://fiscwise-api-...run.app`) aparece no fim do workflow
e no console do Cloud Run. Inclua o domínio do frontend em `ALLOWED_ORIGINS`
no `cloudrun.env.yaml` se for diferente dos que já estão lá.

### 8. Cloud Scheduler (tick de hora em hora)

```bash
API_URL=$(gcloud run services describe fiscwise-api --region southamerica-east1 --format 'value(status.url)')
gcloud scheduler jobs create http fiscwise-tick \
  --location=southamerica-east1 \
  --schedule="0 * * * *" --time-zone="Etc/UTC" \
  --uri="${API_URL}/api/v1/internal/tick" --http-method=POST \
  --headers="X-Cron-Secret=$(gcloud secrets versions access latest --secret=CRON_SECRET)" \
  --attempt-deadline=900s
```

Teste com `gcloud scheduler jobs run fiscwise-tick --location=southamerica-east1`
e veja o resultado nos logs do Cloud Run (`Scheduler tick at ...`).

### 9. Frontend (Cloudflare Pages)

Workers & Pages → Create → Pages → conectar o repositório:

- Root directory: `frontend`
- Build command: `npm run build`
- Output: `dist`
- Variáveis: `VITE_API_URL` = URL do Cloud Run (passo 7), `VITE_GOOGLE_CLIENT_ID`

O Pages já serve `index.html` para as rotas do SPA. Depois, apontar
`fiscwise.com.br` e `www` para o projeto do Pages.

**Cloudflare Web Analytics (grátis, inclui Core Web Vitals: LCP, INP, CLS):**

1. Painel do Cloudflare → **Analytics & Logs → Web Analytics → Add a site**.
   Informe `fiscwise.com.br` e escolha a instalação manual (snippet JS).
2. Copie o valor de `token` do snippet (`data-cf-beacon='{"token": "..."}'`,
   32 caracteres hexadecimais).
3. Workers & Pages → projeto `fiscwise` → Settings → Environment variables →
   **Production**: `VITE_CF_BEACON_TOKEN` = o token. Refaça o deploy.

O `vite.config.ts` injeta o beacon (`static.cloudflareinsights.com/beacon.min.js`,
`defer`) no `index.html` só quando a variável existe e tem formato válido; sem
ela o HTML não muda. Não ative também o "Enable Web Analytics" automático do
Pages, senão as visitas contam em dobro.

Privacidade/LGPD: o beacon do Cloudflare não usa cookies nem localStorage,
não faz fingerprinting e não exige banner de consentimento; envia URL da
página, referrer, user agent e tempos de carregamento. A página `/privacidade`
pode citar o Cloudflare como operador de métricas de desempenho.

**Web Vitals próprios (opcional):** `src/lib/vitals.ts` mede LCP, CLS, INP,
FCP e TTFB e, se `VITE_VITALS_ENDPOINT` estiver definido no build, envia um
JSON por `navigator.sendBeacon` quando a aba fica oculta. Sem a variável o
código nem entra no bundle de produção. Não há coletor hoje: o Cloudflare Web
Analytics acima já cobre os Core Web Vitals.

**E2E (Playwright):** `npm run e2e` (desktop, Pixel 5 e Pixel 5 + Slow 4G) e
`npm run e2e:mobile`. Primeira vez: `npx playwright install chromium` (ou
`PW_CHROMIUM_PATH=/caminho/do/chromium`). Os testes sobem `vite build` +
`vite preview` na porta 4173 sozinhos. `E2E_BASE_URL` testa outra URL (ex.: um
preview do Pages); `E2E_API_URL` habilita os specs que dependem de API real.

### 10. Domínio da API e webhook do Mercado Pago

O mapeamento de domínio nativo do Cloud Run não existe em São Paulo, e
`api.fiscwise.com.br` **não existe**. A API responde em
`https://fiscwise-api-45ckqevl6a-rj.a.run.app` (essa URL não muda enquanto o
serviço `fiscwise-api` existir no mesmo projeto e região).

**URL do webhook do Mercado Pago (cadastrar no painel):**

```
https://fiscwise-api-45ckqevl6a-rj.a.run.app/api/v1/billing/webhook/mercadopago
```

No painel do MP (Suas integrações → aplicação → Webhooks → Configurar
notificações, aba **Modo produtivo**), marque os eventos **Pagamentos**
(`payment`) e, em **Planos e assinaturas**, a assinatura
(`subscription_preapproval`) e o pagamento recorrente
(`subscription_authorized_payment`). A assinatura mensal só avisa pelo painel
(o preapproval não usa o `notification_url`), então esse cadastro é obrigatório. A "assinatura secreta" gerada ali vai para
o segredo `MERCADO_PAGO_WEBHOOK_SECRET`. O `notification_url` enviado em cada
checkout sai de `PUBLIC_URL` (`cloudrun.env.yaml`) e aponta para a mesma URL.

Segredos (Secret Manager, nomes exatos — o deploy monta sozinho quando existem):

```bash
printf '%s' 'APP_USR-...' | gcloud secrets create MERCADO_PAGO_ACCESS_TOKEN --data-file=-
printf '%s' 'APP_USR-...' | gcloud secrets create MERCADO_PAGO_PUBLIC_KEY --data-file=-
printf '%s' 'ASSINATURA_SECRETA_DO_PAINEL' | gcloud secrets create MERCADO_PAGO_WEBHOOK_SECRET --data-file=-
```

Para trocar um valor: `gcloud secrets versions add NOME --data-file=-` e rodar o
deploy de novo. Se o log do deploy disser "Sem permissão para ver o segredo",
dê `roles/secretmanager.viewer` à `fiscwise-deployer` (passo 4).
Com `PAGAMENTOS_GO_LIVE: "true"`, faltar qualquer um dos três segredos derruba
o deploy de propósito.

Roteiro de homologação no sandbox: `docs/audit/HOMOLOGACAO_MERCADO_PAGO.md`.

**Domínio próprio depois (opcional):** um Cloudflare Worker na rota
`api.fiscwise.com.br/*` que repassa tudo para o Cloud Run, mantendo método,
corpo, query string e os cabeçalhos `x-signature` e `x-request-id`:

```js
export default {
  async fetch(request) {
    const url = new URL(request.url);
    url.hostname = "fiscwise-api-45ckqevl6a-rj.a.run.app";
    return fetch(new Request(url, request));
  },
};
```

Depois: DNS `api` com proxy laranja, `PUBLIC_URL` e `VITE_API_URL` para
`https://api.fiscwise.com.br`, e trocar a URL no painel do Mercado Pago.

### 11. Backup (GitHub Actions → R2)

1. No Cloudflare: R2 → criar bucket `fiscwise-backups`, com regra de ciclo de
   vida apagando objetos após 30 dias. Criar um token de API do R2 com permissão
   de escrita só nesse bucket.
2. Gerar o par de chaves do `age` no seu computador: `age-keygen -o fiscwise-backup.key`.
   Guardar o arquivo **inteiro** no cofre (é a única forma de abrir os backups).
   A linha `public key: age1...` vai para o GitHub.
3. GitHub → Variables: `BACKUP_AGE_RECIPIENT` (a chave pública `age1...`),
   `R2_BUCKET`, `R2_ACCOUNT_ID`.
   GitHub → Secrets: `BACKUP_DATABASE_URL` (Session pooler), `R2_ACCESS_KEY_ID`,
   `R2_SECRET_ACCESS_KEY`.
4. Actions → **Database backup** → Run workflow para testar. Depois roda todo
   dia às 03:00 de Brasília.

O backup cobre o schema `public` (dados do sistema). Os arquivos do Supabase
Storage ainda não são copiados; isso fica para uma próxima etapa.

Restaurar (num banco descartável, uma vez por mês):

```bash
age -d -i fiscwise-backup.key fiscwise-AAAAMMDDTHHMMZ.dump.age > fiscwise.dump
pg_restore --no-owner --no-privileges -d "postgresql://..." fiscwise.dump
```

### 12. Monitoramento

- Sentry (plano Developer, grátis): criar projeto Python e React;
  `SENTRY_DSN` no Secret Manager e `VITE_SENTRY_DSN` no Pages. **Pendente**:
  hoje os dois estão vazios e nenhum erro é capturado.
- Log por requisição: em production/staging a API escreve uma linha JSON por
  requisição no stdout (`app/core/request_log.py`), que o Cloud Logging lê como
  log estruturado: `httpRequest` (método, rota, status, latência), `route`
  (template, ex. `/api/v1/clients/{client_id}`), `duration_ms`, `tenant_id` e o
  trace. Nunca grava token, query string, corpo, e-mail, IP ou CPF/CNPJ. Toda
  resposta traz `Server-Timing: app;dur=<ms>` (aparece no DevTools → Network →
  Timing). Em dev: `REQUEST_LOG_JSON=true`.

  Ver p50/p95 no **Logs Explorer** (projeto do Cloud Run), consulta:

  ```
  resource.type="cloud_run_revision"
  resource.labels.service_name="fiscwise-api"
  jsonPayload.message="request"
  ```

  Para percentis: no resultado, **Create metric** (tipo *Distribution*, campo
  `jsonPayload.duration_ms`, label `jsonPayload.route`) e abra no Metrics
  Explorer com agregação 50th/95th percentile, ou use o Log Analytics (grátis):

  ```sql
  SELECT JSON_VALUE(json_payload.route) AS route,
         COUNT(*) AS n,
         APPROX_QUANTILES(CAST(JSON_VALUE(json_payload.duration_ms) AS FLOAT64), 100)[OFFSET(50)] AS p50_ms,
         APPROX_QUANTILES(CAST(JSON_VALUE(json_payload.duration_ms) AS FLOAT64), 100)[OFFSET(95)] AS p95_ms
  FROM `<projeto>.global._Default._AllLogs`
  WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
    AND JSON_VALUE(json_payload.message) = 'request'
  GROUP BY route ORDER BY n DESC
  ```

  Filtro rápido de lentas: `jsonPayload.duration_ms > 1000`.
- Perf probe: Actions → **Perf probe** → Run workflow. Mede p50/p95/max de
  `/live`, `/health`, `/api/v1/health` e `/api/v1/clients` (401 sem token,
  passa por todos os middlewares sem tocar no banco), mais TTFB e tamanho do
  HTML do front. Para ver o cold start, rode depois de ~15 min sem tráfego.
- Better Stack: monitor HTTP em `<URL do Cloud Run>/ready`. Com a instância
  desligando sem uso, o primeiro acesso leva alguns segundos; configure o
  timeout do monitor para 30 s.

## Quando houver clientes

1. Supabase Pro (backup diário gerenciado, sem pausa).
2. Cloud Run com `--min-instances 1` no workflow (sem partida a frio).
3. Resend Pro quando passar de 100 e-mails por dia.
