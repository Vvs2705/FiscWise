---
projeto: FiscWise
repo: Vvs2705/FiscWise
conferido_em: 2026-11-22
---

# ESTADO — FiscWise

## Onde paramos
- A auditoria de segurança, LGPD e consumidor (40 itens) foi aplicada e está na `main`; o redesign do login, do menu e do painel (PR #131) também entrou hoje.
- Pagamento real pelo Mercado Pago, backup diário do banco e teste grátis de 14 dias estão configurados e documentados.
- Emissão de nota (NFS-e), e-CAC e WhatsApp oficial ainda dependem de contrato ou homologação externa: o sistema não finge que são oficiais.
- Em aberto: 8 PRs automáticos de atualização de dependências, sem ninguém olhando ainda.
- Próximo passo: decidir quais atualizações aceitar e fechar as pendências manuais da seção 4 do `COMPLIANCE-40.md`.
- Depende de você: essas pendências manuais, a revisão dos textos legais por advogado e liberar merges que mexem em `backend/` (disparam deploy).

## Stack
- Backend: Python 3.12, FastAPI, SQLAlchemy 2 async + asyncpg, Alembic, Pydantic v2, pytest. Em `backend/`.
- Banco e arquivos: Supabase (Postgres + Storage), com RLS forçada. Redis (Upstash) só para rate limit.
- Frontend: React 18, TypeScript, Vite 6, Tailwind 3, TanStack Query, Zustand, React Hook Form + Zod 4, PWA offline (Dexie). Em `frontend/`.
- Testes: pytest (backend), vitest, Playwright e2e e checagem de contraste (frontend).
- Hospedagem: API no Google Cloud Run (São Paulo), front no Cloudflare Pages, e-mail Resend, erros no Sentry.
- CI em `.github/workflows/`: `ci.yml`, `deploy-cloudrun.yml`, `db-backup.yml`, `perf-probe.yml`, `security-review.yml`.

## Rodar e publicar
- Local, variáveis e testes: [README.md](README.md) seções 5 a 7. Banco, Redis e API juntos: `docker compose up` (usa `docker-compose.yml`).
- Backend: `cd backend && uvicorn app.main:app --reload --port 8000` e `pytest`.
- Frontend: `cd frontend && npm run dev`; antes de subir: `npm run lint`, `npm run type-check`, `npm test`, `npm run e2e`.
- Publicar, segredos, Cloud Scheduler, Cloudflare e backup: [DEPLOY.md](DEPLOY.md).
- Incidente (inclui aviso à ANPD): [RUNBOOK-INCIDENTE.md](RUNBOOK-INCIDENTE.md).
- Auditoria dos 40 itens, pendências do dono e lacunas: [COMPLIANCE-40.md](COMPLIANCE-40.md).
- Mais notas: `docs/arquitetura/OFFLINE_SYNC.md` e `docs/audit/` (prontidão de release, homologação do Mercado Pago, sistema de design).

## Em andamento
- PRs #117, #118, #119: atualização de GitHub Actions (checkout/upload-artifact, auth e setup-gcloud do Google). Abertos pelo Dependabot.
- PRs #120, #124: backend, `pydantic >= 2.14.3` e `google-auth 2.62.2`. Dependabot.
- PRs #121, #122, #123: frontend, `framer-motion` 12 para 14 (salto de versão maior), `postcss` e `react-hook-form`. Dependabot.
- Branch `docs/estado-md`: este arquivo.
- Há dezenas de branches antigas `claude/*`, `fix/*` e `feat/*` no remoto; ver Armadilhas antes de apagar.

## Decisões
- Trabalho entra na `main` só por fast-forward, na pasta central, sem worktree nem clone paralelo (regra do `CLAUDE.md`).
- Sem Redis de fila nem worker fixo: trabalho em segundo plano vai para uma tabela no Postgres e o relógio vem de um tick externo (custo ocioso zero).
- Nunca mostrar dado governamental simulado como oficial; módulos dependentes de contrato externo ficam marcados como roadmap no README.
- Arrependimento com devolução integral em 7 dias para todo novo contratante (termos v1.6); a devolução é feita à mão no Mercado Pago.
- Teste grátis de 14 dias no lugar do plano Gratuito; 1 teste por CNPJ/CPF.
- Dados de exemplo no login e na landing são aceitos se estiverem rotulados como exemplo (decisão do dono, `docs/audit/SISTEMA_DE_DESIGN.md`).
- Textos legais foram gerados por IA e precisam de revisão de advogado antes de valerem como definitivos.
- Dependências com CVE alto sobem na hora; salto de versão maior só com o build e os testes passando.

## Armadilhas
- Push na `main` que toque `backend/**` ou `cloudrun.env.yaml` dispara deploy no Cloud Run. Mudança só de docs ou de `frontend/` não dispara o deploy do backend.
- No Cloud Run a instância desliga: APScheduler interno e `BackgroundTasks` não servem; use `SCHEDULER_MODE=external` e a fila `background_jobs` (DEPLOY.md).
- O tick horário também impede o Supabase Free de pausar por inatividade.
- A API não tem domínio próprio ainda (DEPLOY.md seção 10); não presumir `api.fiscwise.com.br`.
- `CERT_ENCRYPTION_KEY` não pode ser trocada: invalida os certificados A1 e os segredos de 2FA cifrados (não há recifragem pronta).
- Testes de RLS só rodam num Postgres real com `RUN_PG_RLS=1`; o CI cobre.
- README está parcialmente desatualizado (diz React Router 6 e cofre de certificado inexistente; o código já usa v7 e tem cofre A1). Confie no `package.json`, no `DEPLOY.md` e no código.
- Existe um segundo clone local (`FiscWise`) além deste; edite só a pasta central e não apague branch antes de `git merge-base --is-ancestor`.
- Nunca commitar `.claude/settings.local.json`, `.env` nem chaves; o repositório é público.

## Melhorias replicáveis
- Fila de trabalho em Postgres sem worker (`SKIP LOCKED`, retry 1/5/25 min, chave de idempotência) · `2a9155b` · `backend/app/services/job_queue.py`, `job_handlers.py`, `models/background_job.py`, `api/v1/endpoints/jobs.py`, `backend/tests/test_job_queue.py`
- Scheduler externo por tick (Cloud Scheduler chama endpoint interno com segredo; rotinas devidas por hora) · `1b0fe9a` · `services/scheduler.py`, `api/v1/endpoints/internal.py`, `backend/tests/test_scheduler_tick.py`
- Backup diário criptografado com `age` para R2, conferido antes de cifrar, com restauração documentada · `f164647` · `.github/workflows/db-backup.yml`, `DEPLOY.md` seção 11
- Rate limit por usuário em toda a API (Redis) · `7d29043` · `backend/app/core/rate_limit.py`, `backend/tests/test_rate_limit_api.py`
- Webhook de saída com assinatura HMAC verificável, sessão própria e retry · `d13981b` · `services/webhook_service.py`, `backend/tests/test_webhook_delivery.py`
- Billing Mercado Pago idempotente (aviso em dobro aplica uma vez, checkout não sobrescreve o pago) e roteiro de homologação · `d393789`, `028e41a` · `api/v1/endpoints/billing.py`, `services/mercadopago.py`, `backend/tests/test_mp_troca_e_duplicados.py`, `docs/audit/HOMOLOGACAO_MERCADO_PAGO.md`
- RLS que vale também para o dono das tabelas (`FORCE`), testada em Postgres real · `2d24f9d` · `backend/alembic/versions/u7w8forcerls_rls_vale_para_o_dono.py`, `backend/tests/test_rls_postgres.py`
- Log JSON por requisição, Web Vitals, e2e mobile (Pixel 5, 4G lento) e sonda de latência · `36b5595` · `backend/app/core/request_log.py`, `.github/workflows/perf-probe.yml`, `frontend/e2e/fixtures.ts`
- Campo sensível cifrado no banco (segredo do 2FA) · `10e9c40` · `backend/app/core/campo_cifrado.py`, `backend/tests/test_totp_cifrado.py`
- App offline-first: sincronização, dispositivos e PWA · `9cd1d3e`, `d8e6544` · `backend/app/api/v1/endpoints/sync.py`, `backend/app/models/sync.py`, `docs/arquitetura/OFFLINE_SYNC.md`

delta: git log --oneline $(git log -1 --format=%H -- ESTADO.md)..HEAD
