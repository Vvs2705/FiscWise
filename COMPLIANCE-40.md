# COMPLIANCE-40 — FiscWise (relatório consolidado)

Auditoria dos 40 requisitos (segurança, LGPD e CDC) feita em 21/11/2026 por
três frentes em paralelo e fechada por uma frente de QA e revisão. Este arquivo
é o consolidado pedido na seção 5 do documento. Os detalhes de cada frente
continuam nos relatórios parciais, que não foram alterados:

- [COMPLIANCE-40-seguranca.md](COMPLIANCE-40-seguranca.md): bloco A (1, 4–10, 32–34, 36–40)
- [COMPLIANCE-40-banco.md](COMPLIANCE-40-banco.md): itens 2, 3, 18, 31 e migrações
- [COMPLIANCE-40-juridico.md](COMPLIANCE-40-juridico.md): blocos B e C (11–30, 35)
- [RUNBOOK-INCIDENTE.md](RUNBOOK-INCIDENTE.md): resposta a incidente e aviso à ANPD

> Os textos legais (política, termos, DPA, runbook) foram gerados e revisados por
> IA. Revisar com advogado antes de considerar definitivos.

## 1. Perfil: **P2+**

1. SaaS **B2B** para escritórios contábeis, **em produção**, com **cobrança real** pelo Mercado Pago desde 13/11/2026.
2. Stack: FastAPI + SQLAlchemy async + Alembic no Cloud Run; Postgres e Storage no Supabase, com RLS forçada por escritório; React + Vite no Cloudflare Pages; CI no GitHub Actions.
3. **Multi-tenant**. O FiscWise é **controlador** dos dados dos usuários e da cobrança e **operador** dos dados fiscais da carteira de cada escritório.
4. Segredos críticos: cofre de **certificado A1** (AES-256-GCM), segredo TOTP do 2FA, tokens de integração (Secret Manager).
5. Usa a **OpenAI** (classificação de documentos, calculadora e assistente) com CPF/CNPJ mascarados. Sem dado sensível do art. 5º, II. Sem cookie não essencial.

## 2. Tabela dos 40 itens

Legenda: ✅ atende · 🔧 aplicado · ➖ não se aplica · ⏭️ excesso · 🔒 precisa do dono.
Os commits são os da `main` (os hashes citados no relatório de banco são de
antes do rebase; a correspondência está na seção 3).

| nº | item | veredito | evidência ou o que foi feito | arquivo/commit |
|---|---|---|---|---|
| 1 | Autenticação segura | ✅ | JWT HS256 de 30 min com `algorithms` fixo, revogação por `tokens_valid_after`, 2FA, boot de produção aborta com segredo fraco | `app/core/security.py`, `app/core/deps.py` |
| 2 | Controle de acesso / IDOR | 🔧 | RLS com FORCE já existia. Varredura nova (40 rotas) achou 2 falhas reais de "id de outro escritório gravado como referência": certificado A1 no emissor e perfil fiscal do cliente. Corrigidas com teste, e trava no CI para tabela nova sem RLS | `f4c8562`, `tests/test_idor_cross_tenant.py`, `tests/test_rls_postgres.py` |
| 3 | Criptografia de campo | 🔧 | A1 e senha já cifrados (AES-256-GCM com AAD). Faltava o **segredo TOTP**, em texto puro: agora cifrado com a mesma chave, legado lido e recifrado no próximo login com 2FA | `10e9c40`, `app/core/campo_cifrado.py`, migração `y1b2totpcifrado` |
| 4 | HTTPS/TLS | ✅ | HSTS de 1 ano em `frontend/public/_headers`; API em `*.run.app` (domínio `.app` na lista de preload) | `frontend/public/_headers` |
| 5 | Hashing de senhas | ✅ + 🔧 | bcrypt. Ajuste: senha nova > 72 bytes na troca de senha dava 500, agora 400 | `88f1db6` |
| 6 | SQL injection | ✅ | ORM em tudo; o único SQL montado (`exclusao_dados.py`) usa nome de tabela do `information_schema` e valor como parâmetro | `app/services/exclusao_dados.py` |
| 7 | XSS/CSRF | ✅ / 🔒 | Sem `dangerouslySetInnerHTML`; o único `innerHTML` escapa tudo. CSRF ➖ (Bearer, sem cookie). Token no `localStorage` + CSP só em Report-Only → ativar a CSP é 🔒 | `frontend/src/precos.ts`, `_headers` |
| 8 | Rate limiting | ✅ + 🔧 | Login, cadastro, OTP, reset e IA já limitados. Faltava limite na conferência da senha atual (troca de senha e desligar 2FA) | `88f1db6`, `tests/test_current_password_rate_limit.py` |
| 9 | Proteção de APIs | ✅ | CORS fixo, Pydantic em todas as entradas, `/docs` desligado em produção, webhooks com segredo | `app/main.py`, `app/core/config.py` |
| 10 | Dependências | 🔧 / 🔒 | `follow-redirects` 1.16.1 → 1.16.3. zod 4 e react-router 7 são major (🔒). `python-jose`, `ecdsa` e `pytest` sem fix aplicável, avaliados como não exploráveis | `5f67cfc` |
| 11 | Política de privacidade | 🔧 | v1.5: controlador × operador, tabela dado → finalidade → base legal, IA, retenção por tipo | `fd05c33`, `frontend/src/pages/PrivacyPage.tsx` |
| 12 | Bases legais | 🔧 | Uma base por dado, Marco Civil para logs, consentimento só para marketing | `fd05c33` |
| 13 | Minimização | ✅ | Campos usados; `responsible_address/phone` opcionais, só sinalizados | `models/operations.py` |
| 14 | Finalidades | 🔧 | Tabela na seção 2 da política | `fd05c33` |
| 15 | Consentimento | ➖ | Sem cookie não essencial; marketing já é opt-in | — |
| 16 | Política de cookies | ➖ | Só armazenamento do login e Cloudflare Web Analytics sem cookie (explicado na seção 8 da política) | — |
| 17 | Direitos dos titulares | ✅ + 🔧 | Tela de exportar e pedir exclusão já existia. Corrigido o prazo ("15 dias úteis" → 15 dias, art. 19, II) em 4 lugares | `5f12250` |
| 18 | Exclusão de dados | 🔧 | Exclusão automática já existia. Faltava: executar o pedido LGPD do dono (`POST /admin/lgpd/exclusao`, com prévia), guardar registros de acesso por 6 meses e incluir os documentos fiscais na exportação | `b5a673f`, `tests/test_exclusao_lgpd.py` |
| 19 | Retenção | 🔧 | Prazos alinhados ao código (a v1.4 prometia 5 anos e o código apaga em 60 dias) | `fd05c33` |
| 20 | Contratos com operadores (DPA) | 🔧 | Novo `/dpa` com suboperadores (inclui OpenAI), aviso de incidente em 48 h, devolução e eliminação | `9e62160`, `frontend/src/pages/DpaPage.tsx` |
| 21 | Termos de uso | 🔧 | v1.6 (`TERMS_VERSION`), recursos descritos como são, DPA incorporado, foro do consumidor | `2f96ce6` |
| 22 | Transparência de preços | ✅ | `/precos` com preço, ciclo, limites e cancelamento, vindos do banco | `frontend/src/precosHtml.ts` |
| 23 | Cobranças transparentes | ✅ | Recibo do Mercado Pago discrimina. Ver lacuna sobre a NFS-e da própria VStack | — |
| 24 | Cancelamento | ✅ + 🔧 | Botão próprio já existia. Corrigido o texto que prometia guardar os dados sem citar a exclusão em 60 dias | `5f12250`, `SettingsPage.tsx` |
| 25 | Arrependimento 7 dias | 🔧 | Termos v1.6: qualquer contratante desiste em até 7 dias do primeiro pagamento, com devolução integral (decisão do dono). Também em `/precos` e na landing | `2f96ce6`, PR de ajustes |
| 26 | Identificação do fornecedor | 🔧 | CNPJ e cidade no rodapé do app e de `/precos`. Faltam endereço e razão social (`{{PREENCHER}}`) | `b6b1147` |
| 27 | Publicidade | 🔧 | Termos diziam "emissão de DAS/DARF", que o sistema não faz. Corrigido, com aviso das integrações que dependem de homologação | `2f96ce6` |
| 28 | Depoimentos | ✅ | Landing sem depoimentos nem números | `LandingPage.tsx` |
| 29 | Licenças | ✅ | Sem GPL/AGPL; `fpdf2` (LGPL) e `certifi`/axe-core (MPL) compatíveis | — |
| 30 | Transparência sobre IA | 🔧 | Política lista os 4 usos da OpenAI, incluindo a classificação de todo documento enviado. Código: o nome do arquivo ia sem máscara para a OpenAI | `fd05c33`, `e88d169`, `56e1628` |
| 31 | Backups | 🔧 / 🔒 | `pg_dump` diário cifrado já existia. Agora o dump é conferido antes de cifrar, a restauração tem roteiro e o Storage ganhou passo de backup (desligado até criar as chaves, 🔒) | `f164647`, `.github/workflows/db-backup.yml`, `DEPLOY.md` §11 |
| 32 | Logs seguros | ✅ + 🔧 | Log sem corpo, query, token ou CPF; Sentry sem PII. `.claude/settings.local.json` (comando com senha de teste) saiu do git | `b6aa1a9` |
| 33 | Monitoramento | ✅ | Sentry no backend e frontend, Cloud Logging. Nada novo | `DEPLOY.md` §12 |
| 34 | Plano de incidente | 🔧 | Runbook de 1 página | `4baeb11`, `50dbf2a` |
| 35 | Notificação de incidentes | 🔧 | Fluxo ANPD e titulares em 3 dias úteis (Res. CD/ANPD 15/2024) e aviso de operador ao escritório em 48 h, no mesmo runbook | `843a5e1`, `50dbf2a` |
| 36 | Revisão contínua | ✅ | Semgrep em todo PR; pip-audit e npm audit já rodam no `ci.yml` | `.github/workflows/security-review.yml`, `ci.yml` |
| 37 | Testes de segurança | ✅ | Testes de isolamento e RLS no Postgres do CI | `backend/tests/` |
| 38 | Privilégios administrativos | ✅ + 🔧 | Admin desligado por padrão, token em `compare_digest`. Corrigido o IP forjável nos alertas e removido `create_gisele.py`, que criava OWNER clonando a senha de outro usuário | `bf3e5fd`, `be8d5e5`, `tests/test_admin_client_ip.py` |
| 39 | Pentest | ✅ (parcial) | Coberto por 36 e 37. Pentest ativo não foi feito: `strix-review` não existe aqui e nada roda contra produção | — |
| 40 | Auditoria formal | ⏭️ | Sem exigência contratual conhecida | — |

**Contagem:** ✅ 14 · 🔧 aplicado (no todo ou em parte) 24 · ➖ 2 · ⏭️ 1 · itens com parte 🔒: 7, 10, 31.
(Itens com "✅ + 🔧" entram como aplicados.)

## 3. O que foi aplicado

| commit na `main` | item | frente |
|---|---|---|
| `88f1db6` | #8 limite na senha atual; #5 senha > 72 bytes | segurança |
| `5f67cfc` | #10 follow-redirects 1.16.3 | segurança |
| `bf3e5fd` | #38 IP confiável nos alertas de admin | segurança |
| `be8d5e5` | #38 remove `create_gisele.py` | segurança |
| `b6aa1a9` | #32 `.claude/settings.local.json` fora do git | segurança |
| `4baeb11` | #33 #34 runbook | segurança |
| `8130167` | relatório de segurança (PR #125) | segurança |
| `fd05c33` | #11 #12 #14 #19 #30 política v1.5 | jurídico |
| `9e62160` | #20 DPA em `/dpa` | jurídico |
| `2f96ce6` | #21 #25 #27 termos v1.5 | jurídico |
| `b6b1147` | #26 CNPJ e cidade no rodapé | jurídico |
| `5f12250` | #17 #24 prazo LGPD e aviso ao cancelar | jurídico |
| `843a5e1`, `50dbf2a` | #35 fluxo ANPD, runbook unificado | jurídico |
| `a469f31` | relatório jurídico (PR #126) | jurídico |
| `e88d169`, `56e1628` | #30 nome do arquivo mascarado; política e DPA citam a classificação | jurídico |
| `f4c8562` (era `167325e`) | #2 isolamento no A1 e no perfil fiscal | banco |
| `10e9c40` (era `77b35cf`) | #3 TOTP cifrado | banco |
| `b5a673f` (era `96adf50`) | #18 pedido LGPD, registros de acesso, exportação fiscal | banco |
| `f164647` (era `5844c1a`) | #31 backup conferido, Storage, restauração | banco |
| `5087471` | relatório de banco | banco |

## 4. 🔒 Bloqueados: o passo exato para você

| # | O quê | Passo |
|---|---|---|
| 1 | Conta criada pelo `create_gisele.py` (OWNER com a mesma senha da sua conta) | Se o script rodou em produção: entrar com `contabil_gisele@…`, trocar a senha ou desativar o usuário, e ligar 2FA nas duas contas |
| 2 | CSP em modo bloqueante | Conferir no console de produção que não há violação; em `frontend/public/_headers` trocar `Content-Security-Policy-Report-Only` por `Content-Security-Policy` e publicar. Testar o login Google logo depois |
| 3 | Upgrades major | `zod` 3 → 4 e `react-router-dom` 6 → 7, numa tarefa própria com a suíte e o E2E. Impacto atual baixo (ver relatório de segurança §4) |
| 4 | ~~Avisar os usuários dos Termos~~ | **Resolvido (21/11/2026):** ainda não há usuários reais, então não há a quem avisar |
| 5 | ~~Arrependimento para todo cliente B2B~~ | **Resolvido (21/11/2026):** o dono decidiu que vale para todo novo contratante; Termos v1.6. A devolução é feita à mão no Mercado Pago |
| 6 | Backup do Storage | Supabase → Storage → S3 Connection: gerar chaves. GitHub Variables `SUPABASE_S3_ENDPOINT` e `SUPABASE_S3_REGION`; Secrets `SUPABASE_S3_ACCESS_KEY_ID` e `SUPABASE_S3_SECRET_ACCESS_KEY`. Depois, Actions → Database backup → Run workflow |
| 7 | Pedidos LGPD pendentes | `SELECT id, name, deletion_requested_at FROM tenants WHERE deletion_requested_at IS NOT NULL AND dados_excluidos_em IS NULL;` e, para cada um, depois de conferir que exportou: `POST /api/v1/admin/lgpd/exclusao` com `{"tenant_id": "...", "confirmar_nome": "<nome exato>"}` (prévia) e de novo com `"executar": true` |
| 8 | `CERT_ENCRYPTION_KEY` | Confirmar que está no Secret Manager. **Não trocar**: invalida os A1 e os 2FA TOTP cifrados (não há recifragem pronta) |
| 9 | Retenção dos logs (Marco Civil, 6 meses) | `gcloud logging buckets update _Default --location=global --retention-days=180` (tem custo) |
| 10 | Chave `age` dos backups | Guardar uma segunda cópia offline |
| 11 | Supabase Pro / PITR | Decisão de custo; hoje o RPO é de 24 h pelo backup no R2 |
| 12 | `NOT NULL` em 13 colunas divergentes | Só depois de conferir em produção que não há nulos. Baixa prioridade |
| 13 | NFS-e da própria VStack | Confirmar com o contador que cada mensalidade recebida pelo Mercado Pago gera nota |
| 14 | Redirect HTTP → HTTPS do domínio | Conferir uma vez: `curl -I http://fiscwise.com.br` deve responder 301/308 para `https://` |

## 5. `{{PREENCHER}}` pendentes

- **Razão social** para o rodapé e os textos legais. A empresa é empresário individual, e a razão social de um EI é o nome civil do titular; hoje aparece só o nome fantasia "VStack Solutions" (`frontend/src/lib/company.ts`). *(achado da revisão final)*
- CEP da sede (endereço Rua Vicente Lisa, 119, Caieiras/SP já aplicado no rodapé e nos textos legais).
- Contato de plantão para incidentes (`RUNBOOK-INCIDENTE.md`).
- Nome do encarregado, se quiser nomear uma pessoa (hoje é a própria VStack).
- Confirmar que `privacidade@fiscwise.com.br` e `juridico@fiscwise.com.br` existem e são lidas.
- Plano atual do Supabase (para a decisão do item 11 acima).

## 6. Revisão final (QA): diff mínimo e overengineering

Diff acumulado sobre `7f77852`: 42 arquivos, +1.921 / −233, dos quais cerca de
um terço são os relatórios e os textos legais.

- **Sem overengineering.** Nada de SIEM, WAF, painel de consentimento ou processo
  novo. As peças novas são pequenas e reaproveitam o que existia: a cifra do
  TOTP usa a chave e o algoritmo do cofre A1 (79 linhas), a rota de exclusão
  LGPD chama a mesma função da exclusão automática, o backup do Storage é um
  passo no workflow que já existia.
- **Sem dependência nova** no backend ou no frontend (só o patch do `follow-redirects`).
- **Migração não destrutiva** (`VARCHAR(64)` → `VARCHAR(255)`); downgrade no-op de propósito.
- **Fora de escopo, mas aceitável:** `verify-2fa` passou a converter o `user_id`
  do token para UUID antes da consulta (no mesmo commit do #3). É defensivo e tem
  teste; mantido.
- **Correção a um relatório parcial:** o de segurança sugere incluir `pip-audit` e
  `npm audit` no CI. Os dois já rodam em `.github/workflows/ci.yml`.
- **Desvio deliberado do documento:** a Fase 3 pede "Gerado automaticamente —
  revisar com advogado" **no topo** dos documentos legais. A frente jurídica pôs
  o aviso em comentário no código, não na página pública, porque são páginas de
  produção que os clientes aceitam. Mantido assim; o aviso está neste relatório.
- **Riscos residuais anotados:** (a) segredos TOTP legados só são cifrados no
  próximo login com 2FA; quem não entrar continua em texto puro até lá.
  (b) O backup do banco exige pelo menos 40 tabelas com dados no dump; se o
  esquema encolher, o número precisa acompanhar.

## 7. Lacunas do documento original

O que as quatro frentes apontaram que o documento "40 requisitos" não cobre ou
cobre errado para um sistema como o FiscWise:

**Segurança**
1. **Ataque com token roubado.** O item 8 lista login, cadastro e reset, mas não as rotas que conferem a senha atual. Foi onde estava a falha.
2. **IP atrás de proxy.** Não pede para conferir de onde vem o IP do rate limit; ler a primeira entrada do `X-Forwarded-For` anula o limite.
3. **Token no `localStorage` exige CSP ativa.** O item 7 só trata do caso do cookie. Falta "CSP bloqueante, não só Report-Only".
4. **Scripts soltos e arquivos locais versionados** (criar usuário, `settings.local.json`, `.env`) não entram em nenhum item.
5. **CVE sem correção.** O item 10 só fala de upgrade; falta "avaliar se é explorável e registrar".
6. **`strix-review` não existe** neste ambiente, e os itens 36, 37 e 39 dependem dele.

**Banco**
7. **IDOR de escrita.** O item 2 só fala em "toda query filtra por tenant". As falhas reais foram de id de outro escritório **gravado como referência**: a checagem de FK do Postgres não passa pela RLS.
8. **RLS aberta sem contexto.** As policies liberam tudo quando não há escritório no contexto (agendador, webhooks, backup). O documento não pede para conferir que toda rota fixa o contexto.
9. **Segredos de autenticação no banco.** O item 3 lista A1 e tokens, mas esquece o segredo TOTP, onde estava a lacuna.
10. **Backup só do Postgres.** O item 31 ignora os arquivos no Storage, a conferência do dump, a custódia da chave e o RPO.
11. **Migrações não têm item**, embora a distribuição de agentes as cite.

**Jurídico**
12. **Documento fiscal (NF-e, NFS-e, SEFAZ) e uso do A1** não aparecem no documento.
13. **NFS-e da própria empresa.** O item 23 só pede fatura discriminada; a VStack precisa emitir nota de cada mensalidade.
14. **Retenção fiscal tem dois donos.** A guarda por 5 anos (CTN) é do escritório; o dever do operador é devolver e excluir (LGPD art. 16). O documento trata como se fosse do sistema.
15. **Pedidos de titular via Portal do Cliente** (titular é cliente do escritório, não do FiscWise): resolvido no DPA com repasse ao controlador.
16. **Marco Civil (art. 15):** guarda de registros de acesso por 6 meses não é citada.
17. **Decreto 7.962/2013:** além da identificação, exige resumo do contrato antes da compra e confirmação do pedido.
18. **Contador autônomo ou MEI como consumidor** (finalismo mitigado): B2B não afasta o CDC em todos os casos.
19. **Razão social de empresário individual.** O item 26 pede "razão social/nome", mas não avisa que, no EI, é o nome civil do titular. *(revisão final)*

**Processo**
20. **Regra de git do repositório.** A Fase 3 manda criar `compliance/40-requisitos`, mas aqui o CLAUDE.md exige fast-forward only e as sessões em nuvem só podem dar push na própria branch `claude/...`. As frentes seguiram o CLAUDE.md.
21. **Várias frentes mesclando na mesma `main` em paralelo** não está previsto; exigiu rebase e unificação do runbook.
22. **"Merge só com suíte verde" não segura o deploy.** O workflow `deploy-cloudrun.yml` publica o backend em produção a cada push na `main` que toque `backend/**`, sem esperar o CI. Na prática, o merge automático já é deploy em produção. Fazer o deploy esperar o CI é mudança de config de deploy (🔒); fica como sugestão. *(revisão final)*

## 8. Status

**Mesclado na `main` por fast-forward** em 21/11/2026, sem PR aberto (merge
automático autorizado pelo dono, regra do CLAUDE.md).

Suíte conferida na `main` em `5087471`, antes deste relatório:

- Backend: migrações do zero até o head num PostgreSQL 16 vazio e `pytest` com
  `RUN_PG_RLS=1`: **796 passaram, 0 falhas**.
- Frontend: `npm run lint` (0 erros, 3 avisos de fast refresh antigos),
  `npm run type-check` limpo, `npm test` **154/154**, `npm run build` ok.
- GitHub Actions: CI da `main` em `5087471` **verde**
  ([run 319](https://github.com/Vvs2705/FiscWise/actions/runs/44931748572)).

Este commit só acrescenta este arquivo (não dispara o deploy do backend). Os
itens 🔒 da seção 4 continuam com o dono.
