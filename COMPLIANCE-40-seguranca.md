# COMPLIANCE-40 — Segurança (Bloco A) — FiscWise

Auditoria de 21/11/2026 sobre a `main` em `7f77852`. Frente de segurança: itens
1, 4 a 10, 32 a 34, 36 a 40. Os itens 2, 3, 18 e 31 (banco) e os blocos B e C
(jurídico) são de outras frentes; o que vi sobre eles está na seção 6.

## 1. Perfil: **P2+**

- **Stack:** FastAPI (Python 3.12) + SQLAlchemy 2 async + Alembic; Postgres no
  Supabase com RLS forçado por escritório; Redis opcional; Supabase Storage.
  Frontend React 18 + Vite + TS no Cloudflare Pages. API no Google Cloud Run
  (`*.run.app`, segredos no Secret Manager). CI no GitHub Actions.
- **Uso:** B2B (escritórios de contabilidade), em produção, com cobrança real
  (Mercado Pago, `PAGAMENTOS_GO_LIVE=true` desde 13/11/2026).
- **Dados:** nome, e-mail, CPF de responsáveis e sócios, IP (auditoria e portal),
  dados fiscais das empresas clientes. O FiscWise é **operador** dos dados dos
  clientes dos escritórios. Sem dado sensível do art. 5º II.
- **Segredos críticos:** cofre de certificado A1 (chave e senha), tokens de
  integração, chave da OpenAI (IA fiscal e classificação de documentos).
- **Multi-tenant:** sim. **Cookies não essenciais:** não (só Cloudflare Web
  Analytics, sem cookie).

## 2. Vereditos

| nº | item | veredito | evidência ou o que foi feito | arquivo/commit |
|---|---|---|---|---|
| 1 | Autenticação segura | ✅ ATENDE | JWT HS256 de 30 min (`config.py:129`), `algorithms` fixo em todo `jwt.decode`, revogação por `tokens_valid_after`, 2FA (TOTP e e-mail), Google com `email_verified`. Em produção o boot **aborta** sem segredo ou com segredo fraco (`main.py`, `weak_production_secrets`). Token do dispositivo offline com teto de 180 dias. | `app/core/security.py`, `app/core/deps.py:281` |
| 4 | HTTPS/TLS | ✅ ATENDE | Frontend: HSTS 1 ano em `frontend/public/_headers` (e `vercel.json`). API: domínio `.app` está inteiro na lista de preload HSTS dos navegadores e o Cloud Run só serve HTTPS. Não deu para confirmar o redirect HTTP→HTTPS do domínio `fiscwise.com.br` daqui (sem acesso de rede à produção, e nada foi rodado contra ela). | `frontend/public/_headers` |
| 5 | Hashing de senhas | ✅ ATENDE (+ ajuste) | bcrypt direto, recusa > 72 bytes. Ajuste: `change-password` devolvia **500** para senha nova > 72 bytes; agora 400, como a redefinição. | `88f1db6` |
| 6 | SQL injection | ✅ ATENDE | ORM em tudo. Único SQL montado com f-string (`exclusao_dados.py:214`) usa nome de tabela vindo do `information_schema`, entre aspas, e o valor como parâmetro. Bandit B608 é falso positivo. | `app/services/exclusao_dados.py` |
| 7 | XSS/CSRF | ✅ ATENDE / 🔒 CSP | Sem `dangerouslySetInnerHTML`. O único `innerHTML` (`precos.ts`) passa tudo por `escapeHtml`. CSRF ➖ N/A: auth por Bearer no header, não por cookie. **Ponto de atenção:** o token fica no `localStorage`, então XSS é o risco que importa, e a CSP está só em `Report-Only`. Ativar é mudança de config de deploy: 🔒 (ver seção 4). | `frontend/src/precos.ts`, `_headers` |
| 8 | Rate limiting | ✅ ATENDE (+ 🔧) | Login, cadastro, Google, OTP, reset (pedido e confirmação), portal: limitador próprio (`auth_rate_limiter`, IP pela última entrada do `X-Forwarded-For`). Global 300/min por usuário e 120/min anônimo. IA: cota mensal por plano (`check_chat_quota`, `ai_classification_allowed`). **Faltava:** `change-password` e `2fa/disable` conferiam a senha atual sem limite próprio; um token roubado podia testar senhas para tomar a conta. Aplicado, com teste. | `88f1db6`, `tests/test_current_password_rate_limit.py` |
| 9 | Proteção de APIs | ✅ ATENDE | CORS com lista fixa e sem localhost em produção (`config.py:310`), Pydantic em todas as entradas, `/docs` desligado em produção, webhooks com segredo (fail closed), `/internal/tick` com `CRON_SECRET` em `compare_digest`. | `app/main.py`, `app/core/config.py` |
| 10 | Dependências | 🔧 APLICADO / 🔒 | `follow-redirects` 1.16.1 → 1.16.3 (alto, patch). Restante na seção 4 e 5. | `5f67cfc` |
| 32 | Logs seguros | ✅ ATENDE (+ 🔧) | Log por requisição sem query string, corpo, token, e-mail ou CPF (`request_log.py`); OTP sempre `[code redacted]`; Sentry com `send_default_pii=False`. Ajuste: `.claude/settings.local.json` versionado com um comando de cadastro com senha de teste (localhost) saiu do git. Observação: alguns `logger.info` de 2FA e reset gravam o e-mail do usuário (aceitável, mas dá para trocar por `user_id` depois). | `b6aa1a9` |
| 33 | Monitoramento/alertas | ✅ ATENDE | Sentry no backend e no frontend, Cloud Logging estruturado (DEPLOY.md §12). Nada novo criado. | `DEPLOY.md` |
| 34 | Plano de resposta a incidente | 🔧 APLICADO | `RUNBOOK-INCIDENTE.md` de 1 página com conter, registrar e comunicar (inclui o fluxo do #35, ANPD em 3 dias úteis). | `RUNBOOK-INCIDENTE.md` |
| 36, 37, 39 | Revisão contínua / testes de segurança / pentest | ✅ ATENDE | Semgrep (`p/security-audit` + `p/secrets`) em todo PR (`security-review.yml`), testes de isolamento entre escritórios e RLS no Postgres do CI. Pentest ativo não foi feito (não há `strix-review` e nada roda contra produção). Sugestão sem processo novo: incluir `pip-audit` e `npm audit --omit=dev` no mesmo workflow. | `.github/workflows/` |
| 38 | Privilégios administrativos | ✅ ATENDE (+ 🔧) | Rotas `/admin` desligadas por padrão (`ADMIN_OPERATIONS_ALLOWED`), token em `compare_digest`, limite 10/min; diagnóstico atrás de flag e só `owner`. Sem usuário ou senha padrão no código. **Corrigido:** (a) `admin._get_client_ip` lia a primeira entrada do `X-Forwarded-For` (forjável) nos alertas; (b) `backend/create_gisele.py` criava um OWNER **clonando o hash de senha de outro usuário**, com e-mails pessoais versionados. Script removido. | `bf3e5fd`, `be8d5e5`, `tests/test_admin_client_ip.py` |
| 40 | Auditoria formal | ⏭️ EXCESSO | Sem exigência contratual conhecida. | — |

## 3. Aplicado (branch `claude/project-thread-gv7n6b`)

| commit | item | teste |
|---|---|---|
| `88f1db6` | #8 limite na conferência da senha atual; #5 senha > 72 bytes vira 400 | `tests/test_current_password_rate_limit.py` (falha sem a correção) |
| `5f67cfc` | #10 follow-redirects 1.16.3 | `npm audit --omit=dev` sem o aviso |
| `bf3e5fd` | #38 IP confiável nos alertas de admin | `tests/test_admin_client_ip.py` |
| `be8d5e5` | #38 remove `create_gisele.py` | — (remoção; nada importava o script) |
| `b6aa1a9` | #32 `.claude/settings.local.json` fora do git | — |
| (este) | #34 runbook e este relatório | — |

Ao puxar a `main`, o git apaga `backend/create_gisele.py` e
`.claude/settings.local.json` da cópia local. Se quiser manter a sua cópia do
segundo: `git show 7f77852:.claude/settings.local.json > .claude/settings.local.json`
(o `.gitignore` já impede que volte para o repositório).

## 4. 🔒 Bloqueados (precisam de você)

> **Atualização 21/11/2026:** os itens 1, 2 e 3 abaixo foram resolvidos a pedido do dono (senha expirada na conta com hash copiado, `380f0d3`; CSP bloqueante, `d4dd598`; react-router 7 e zod 4, `fe63d5a` e `df58f0e`). Ver COMPLIANCE-40.md §4.

1. **Conta criada pelo `create_gisele.py`.** Se o script já rodou em produção, a
   conta `contabil_gisele@…` é OWNER com **a mesma senha** da sua conta
   principal. Passo: entrar com ela e trocar a senha (ou desativar esse usuário), e ligar 2FA
   nas duas contas.
2. **CSP em modo bloqueante.** Em `frontend/public/_headers`, depois de conferir
   no console de produção que não há violação, trocar
   `Content-Security-Policy-Report-Only` por `Content-Security-Policy` e
   publicar. É config de deploy e pode quebrar o login Google se faltar algum
   host.
3. **Upgrades major com aviso de segurança** (trava de upgrade major):
   - `zod` 3 → 4 (alto: consumo de memória ao validar coleções enormes). Só roda
     no navegador do próprio usuário, então o impacto real é baixo.
   - `react-router-dom` 6 → 7 (moderado: open redirect com barra invertida em
     `<Link>`/`useNavigate`). O app não navega para destinos vindos da URL
     (`?next=`, `?redirect=`), então hoje não é explorável.
4. **Segredo de teste no histórico.** A senha do `settings.local.json` só valia
   para um cadastro em localhost; não há o que rotacionar em produção. O
   histórico não foi reescrito (proibido pelo CLAUDE.md).

## 5. Dependências sem correção disponível (avaliadas, não exploráveis aqui)

- `python-jose` 3.5.0 (PYSEC-2026-4298): forja de HS256 com chave pública. Não
  se aplica: todo `jwt.decode` fixa `algorithms=[HS256]` e a chave é um segredo
  aleatório, nunca uma chave pública. Migrar para PyJWT fica como melhoria
  futura.
- `ecdsa` 0.19.2 (Minerva, assinatura P-256): vem do `python-jose` e o FiscWise
  não assina com ECDSA.
- `pytest` 8.3.3 (diretório em `/tmp`): só ambiente de desenvolvimento; a
  correção (9.0.3) é major e exige subir o `pytest-asyncio` junto.
- gitleaks (91 commits): 3 achados, todos falsos positivos (segredo de CI de
  teste, senha de fixture, exemplo `fw_live_...` na tela de API).
- bandit (`-ll`): 5 médios, todos falsos positivos (`/dev/shm` usado de
  propósito para o PEM do mTLS com `0o600`, `0.0.0.0` do uvicorn, o SQL do #6).

## 6. Achados para as outras frentes

- **#2 (banco):** RLS forçado por escritório (`u7w8forcerls`), testes de IDOR
  (`test_multitenant_isolation`, `test_cross_tenant_client_ref`,
  `test_invoice_cross_tenant`, `test_rls_postgres`). Não revisei rota a rota.
- **#3 (banco):** existe cofre A1 (`app/domain/certificados/cofre.py`) com chave
  de cifra própria; não revisei o algoritmo.
- **#31 (banco):** backup diário criptografado (age) para o R2, fora do
  Supabase, com restauração documentada (DEPLOY.md §11).
- **#18 (banco):** exclusão automática 60 dias após vencimento
  (`exclusao_dados.py`), com aviso de 72 h.
- **Jurídico (#30, #20):** dados vão para a OpenAI (classificação de documentos e
  assistente). A política precisa citar o provedor e a finalidade, e o DPA com
  os escritórios precisa listar a OpenAI como suboperador.

## 7. O que falta no próprio documento de 40 requisitos

1. **Ataque com token roubado.** O item 8 lista login, cadastro e reset, mas não
   as rotas que conferem a senha atual (troca de senha, desligar 2FA). Foi aqui
   que estava a falha.
2. **IP atrás de proxy.** O documento não pede para conferir de onde vem o IP do
   rate limit. Em Cloud Run, Cloudflare ou Vercel, ler a primeira entrada do
   `X-Forwarded-For` anula o limite por IP.
3. **Onde fica o token no navegador.** O item 7 diz que CSRF só importa com
   cookie, mas não diz o lado oposto: token no `localStorage` torna a CSP
   obrigatória. Falta um item "CSP ativa, não só report-only".
4. **Scripts soltos e arquivos locais versionados** (scripts de "criar usuário",
   `settings.local.json`, `.env`) não entram em nenhum item; o gitleaks não
   pega script que clona senha.
5. **CVE sem correção.** O item 10 só fala de upgrade. Falta o caminho "sem fix:
   avaliar se é explorável no uso real e registrar".
6. **`strix-review` não existe** neste ambiente; o documento depende dele para
   os itens 36, 37 e 39.
7. **Merge automático e travas.** A Fase 3 manda criar `compliance/40-requisitos`,
   mas não diz o que fazer quando o repositório tem regra própria de git (aqui,
   fast-forward only no CLAUDE.md) ou quando várias frentes mesclam na mesma
   `main` em paralelo.

## 8. Status

Suíte local: ver PR. Merge na `main` por fast-forward só com tudo verde;
itens 🔒 ficam fora.
