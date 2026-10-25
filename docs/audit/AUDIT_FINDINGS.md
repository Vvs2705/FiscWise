# Auditoria FiscWise — achados (25/10/2026)

Fonte única dos achados da auditoria pedida em `PROMPT_MESTRE_FISCWISE_AUDITORIA_E_LANCAMENTO.md`.
Decisão de lançamento: [RELEASE_READINESS.md](RELEASE_READINESS.md).

## Baseline

| Item | Valor |
|---|---|
| Commit auditado | `4247d00` (`main`, 01/09/2026) |
| Branch das correções | `fix/auditoria-seguranca-p0-p1` |
| Backend antes | `pytest`: 288 passaram (Python 3.14 local, sem `hiredis`) |
| Backend depois | `pytest`: 302 passaram (14 testes novos de regressão) |
| Frontend | `lint`, `type-check`, `build` e `vitest` passam antes e depois |
| `npm audit` | 21 avisos (12 high) → 6 (1 high: `zod` 3) |
| `pip-audit` | 26 avisos → 3, todos sem correção disponível ou só de teste (ver `ci.yml`) |
| Banco | Testes usam SQLite: RLS do PostgreSQL **nunca é exercida** pela suíte |
| Produção | Não auditada. Só a configuração versionada (sem acesso a Cloud Run, Cloudflare, Supabase) |

Método: leitura estática por domínio (auth/segredos, multi-tenant, banco/regras, deploy/frontend), cada achado conferido no código; os corrigidos ganharam teste que falha antes e passa depois.

Estados: **corrigido** (neste PR, com teste), **pendente**, **não verificado** (falta acesso), **encerrado**.

## P0 — bloqueiam lançamento

| ID | Achado | Evidência | Estado |
|---|---|---|---|
| SEC-1 | Connection string do Supabase com senha em `.mcp.json`, versionada em repo **público** desde 01/09 | `.mcp.json:9` | **Encerrado**: o projeto `lkgmgbieottygodrdubi` não existe mais (DNS não resolve, conferido em 25/10). Arquivo removido no PR #52 e ignorado no `.gitignore`. A senha continua no histórico, mas não abre nada |
| TEN-1 | Usuário do portal (papel CLIENT) usava o mesmo JWT nas rotas do escritório e via/alterava dados de **todos** os clientes do escritório | `app/core/deps.py` `get_current_user` sem checagem de papel | **Corrigido**: CLIENT só alcança `/auth/*` e `/portal/my-data`. Teste `tests/test_client_role_isolation.py` |
| UX-2 | e-CAC sempre simulado (`MockEcacIntegrationProvider` fixo), tela mostrava "regular" e certidões como consulta real | `endpoints/ecac.py:27` | **Corrigido na tela** (aviso de demonstração). Integração real pendente |
| UX-3 | NFS-e sempre simulada (`MockNfseProvider`, protocolo `MOCK-…`), sem aviso | `endpoints/invoices.py:33,117` | **Corrigido na tela**. Integração real pendente |

Nenhum vazamento entre escritórios diferentes (A lendo B) foi encontrado: todas as rotas com ID filtram pelo `tenant_id` do usuário, e o `X-Tenant-ID` é conferido contra o usuário e o JWT (`deps.py`).

## P1

| ID | Achado | Evidência | Estado |
|---|---|---|---|
| SEC-2 | Webhook do WhatsApp público sem autenticação: quem sabe o UUID do escritório injeta mensagens e tarefas | `endpoints/whatsapp.py` | **Corrigido**: exige `X-Webhook-Secret` (`WHATSAPP_WEBHOOK_SECRET`); sem segredo responde 503 em produção. Teste `test_webhook_fail_closed.py` |
| SEC-3 | Webhook Mercado Pago aceitava tudo sem secret, inclusive em produção | `services/mercadopago.py` | **Corrigido**: fail-closed fora de dev, igual ao Asaas |
| SEC-5 | Falha na consulta ao MP gravava o evento; o reenvio caía em `already_processed` e o plano nunca ativava | `endpoints/billing.py` | **Corrigido**: rollback + 503 para o MP reenviar. Teste `test_mp_webhook_retry.py` |
| SEC-4 | Rate limit de login por IP driblável trocando o `X-Forwarded-For` | `core/auth_rate_limiter.py` | **Corrigido** (usa a última entrada do XFF, que o Cloud Run acrescenta; `Fly-Client-IP` ignorado). Teste `tests/unit/test_client_ip.py`. **Pendente**: limiter é em memória (não vale com 2+ máquinas) e não cobre `/onboarding/register`, `/auth/google`, `resend-2fa`, `2fa/confirm-email` |
| SEC-14 | Gates de segurança do CI com `continue-on-error` (por isso o SEC-1 passou) | `.github/workflows/ci.yml` | **Corrigido**: Gitleaks e pip-audit bloqueiam; npm audit bloqueia em critical; Bandit rotulado informativo; `permissions: contents: read` |
| DEP-1 | `python-multipart` 0.0.12 (14 avisos, parsing de upload), `python-jose` 3.3.0, `python-dotenv` 1.0.1, 12 avisos high no npm | `requirements.txt`, `package-lock.json` | **Corrigido** (atualizações sem quebra, suíte verde) |
| UX-4 | WhatsApp marca mensagem como enviada sem provedor | `services/whatsapp_service.py:99` | **Corrigido na tela** (aviso). Status "enviada" no backend pendente |
| OPS-2 | `fly.toml` documentava `SUPABASE_SERVICE_KEY`; o código lê `SUPABASE_SECRET_KEY` (upload ficaria desligado) | `fly.toml:43` | **Encerrado**: o `fly.toml` saiu com a stack nova (PR #54); `DEPLOY.md` usa `SUPABASE_SECRET_KEY` |
| OPS-5 | Frontend sem headers de segurança | `vercel.json` | **Corrigido parcialmente**: HSTS, `X-Frame-Options`, nosniff, Referrer-Policy, Permissions-Policy. **Pendente**: CSP (precisa testar com a URL final da API) |
| TEN-3 | RLS provavelmente inócua: sem `FORCE ROW LEVEL SECURITY` e a app tende a conectar como `postgres` (BYPASSRLS) | `alembic/versions/20260525i/j` | **Não verificado** (sem banco). Isolamento hoje depende só dos filtros da aplicação |
| UX-1 | JWT em `localStorage`: qualquer XSS rouba a sessão | `frontend/src/lib/auth.ts` | Pendente (mitigar com CSP; depois cookie httpOnly) |
| DB-1 | `audit_log()` dos domínios financeiros é stub (só `logger.debug`): guias, notas, fechamento não são auditados | `app/core/audit.py` | Pendente |
| DB-2 | Scheduler sem trava entre máquinas: com 2+ instâncias, cobrança e lembretes rodam em dobro | `services/scheduler.py` | Pendente (hoje 1 máquina, não duplica) |
| DB-3 | Lembretes de cobrança não enviam nada e contam como enviados | `services/scheduler.py:239` | Pendente |
| DB-4 | CNPJ/CPF sem unicidade por escritório | `models/operations.py:54` | Pendente (precisa deduplicar antes da constraint) |

## P2

| ID | Achado | Evidência | Estado |
|---|---|---|---|
| SEC-6 | Boot em produção só falha se `DATABASE_URL`/`JWT_SECRET_KEY` faltarem; valor fraco/placeholder só gera log | `main.py:65`, `config.py:142` | Pendente (`ENVIRONMENT=production` está no `fly.toml`) |
| SEC-7 | OTP de e-mail em memória por processo; `/2fa/confirm-email` sem limite de tentativas | `endpoints/auth.py:59,634` | Pendente |
| SEC-8 | JWT sem `iss`/`aud`/revogação; logout no-op; troca de senha não invalida token | `core/security.py` | Pendente |
| SEC-12 | Cadastro revela se o e-mail já existe | `endpoints/onboarding.py:63` | Pendente |
| SEC-13 | Convite do portal usa só o UUID como segredo; aceite não atômico; `portal_user_id` lido antes do flush | `endpoints/portal.py:134-264` | Pendente |
| TEN-4 | Contexto de RLS (`set_config` local) some após `commit`; policies com `OR … IS NULL` liberam tudo nesse intervalo | `deps.py:131`, `20260525j` | Pendente |
| TEN-5 | Upload de documentos sem limite de tamanho/MIME e com URL pública do bucket | `endpoints/operations.py:1071` | Pendente |
| TEN-6 | `POST /clients/{id}/documents` grava URL placeholder e não guarda o arquivo | `operations.py:1609` | Pendente |
| TEN-7 | `client_id` do payload não validado contra o escritório em guias, e-CAC, notas, obrigações | vários `domain/*/service.py` | Pendente (UUID v4 torna exploração impraticável) |
| DB-5/6/7 | Idempotência de cobrança por `LIKE`; datas em UTC/naive (job do dia 1 roda dia 30/31 no horário de Brasília); prazos sem dia útil/feriado | `scheduler.py`, `obligation_engine.py` | Pendente — **validar com contador** |
| DB-8 | Preço de plano e conversão para centavos em `float` | `core/pricing.py:47`, `mercadopago.py` | Pendente (models usam `Numeric`) |
| OPS-1 | Domínios divergentes: `api.fiscwise.com.br` no código, `fiscwise.fly.dev` no frontend; CORS inclui `frontend-v-stack-solution.vercel.app` | `config.py:160`, `api.ts:5`, `fly.toml:20` | Pendente (depende da stack nova) |
| OPS-3/4 | README dizia Python 3.14+ e linkava arquivo local `file:///` | `README.md` | **Corrigido** |
| UX-5/6 | URL inventada `fiscwise.storage` na CND; toast "Lembrete enviado" sem envio | `ClientDetailCockpit.tsx:1599`, `ModoFocoModal.tsx:161` | Toast **corrigido**; URL pendente |

P3 e observações: `backend/create_gisele.py` com e-mails pessoais versionado; Google OAuth não exige `email_verified`; migration `0f0c2c42addb` apaga 4 colunas de certificados no `upgrade`; `print` em `ecac.py`; grafo Alembic linear com 1 head (ok).

## Não verificado (falta de acesso)

Produção (secrets reais, máquinas, DNS de `fiscwise.com.br`), role do banco e BYPASSRLS, bucket público ou privado, backups e restore, carga/desempenho, DAST, UX com usuários reais. Nada disso foi alegado como funcionando.
