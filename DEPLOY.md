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

### 3. Upstash

Banco Redis na região **São Paulo (sa-east-1)**. Copiar a URL `rediss://...`
para `REDIS_URL`.

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
for ROLE in roles/run.admin roles/artifactregistry.writer; do
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
`REDIS_URL` (sem ele o rate limit por Redis fica desligado e vale só o limite em memória do login), `OPENAI_API_KEY`, `SENTRY_DSN`, `RESEND_API_KEY`, `MERCADO_PAGO_ACCESS_TOKEN`,
`MERCADO_PAGO_WEBHOOK_SECRET`, `WHATSAPP_WEBHOOK_SECRET`.

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

### 10. Domínio da API (opcional, depois)

O mapeamento de domínio nativo do Cloud Run não existe em São Paulo. Enquanto
não houver clientes, use a URL `*.run.app`. Quando quiser `api.fiscwise.com.br`,
as opções gratuitas são um Cloudflare Worker que repassa as requisições para a
URL do Cloud Run, ou Firebase Hosting com rewrite para o serviço. Depois,
atualize `VITE_API_URL` e o `PUBLIC_URL` do `cloudrun.env.yaml`.

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

- Sentry: criar projeto Python e React; `SENTRY_DSN` no Secret Manager.
- Better Stack: monitor HTTP em `<URL do Cloud Run>/ready`. Com a instância
  desligando sem uso, o primeiro acesso leva alguns segundos; configure o
  timeout do monitor para 30 s.

## Quando houver clientes

1. Supabase Pro (backup diário gerenciado, sem pausa).
2. Cloud Run com `--min-instances 1` no workflow (sem partida a frio).
3. Resend Pro quando passar de 100 e-mails por dia.
