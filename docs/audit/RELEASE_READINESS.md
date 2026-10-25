# Prontidão para lançamento — FiscWise (25/10/2026)

## Resultado: **NO-GO**

O produto não pode ser vendido ainda. Os dois riscos críticos de código (cliente do portal vendo dados de todo o escritório e telas simuladas parecendo reais) estão corrigidos neste PR, mas faltam gates obrigatórios que dependem de ambiente, de decisão do dono e de validação profissional. Detalhes de cada item: [AUDIT_FINDINGS.md](AUDIT_FINDINGS.md).

| Gate | Critério | Evidência | Status | Bloqueio |
|---|---|---|---|---|
| Segredos | Nenhum segredo válido no repositório | `.mcp.json` removido (PR #52); projeto do banco já excluído | OK | Merge do PR #52 |
| Multi-tenant (código) | Nenhum vazamento entre escritórios nem do portal para o escritório | Leitura de todas as rotas com ID; `test_client_role_isolation.py` | OK no código | — |
| Multi-tenant (banco) | RLS efetiva com role sem BYPASSRLS, testada em PostgreSQL real | Suíte usa SQLite | **Falha** | Banco novo + teste de RLS |
| Webhooks e pagamento | Assinatura obrigatória, idempotência, sem perda de evento | Testes novos; `PAGAMENTOS_GO_LIVE=false` devolve 503 | OK (sandbox não testado) | Homologação no sandbox do MP |
| Auth | Rate limit distribuído, OTP compartilhado, revogação de token | Limiter e OTP no Redis com `REDIS_URL` (leva 3); troca de senha invalida tokens (leva 4) | **Parcial** | Configurar `REDIS_URL` em produção |
| CI | Gates de segurança bloqueiam | `ci.yml` alterado | OK após merge | — |
| Funcionalidades honestas | Nada simulado apresentado como real | Avisos em e-CAC, NFS-e, WhatsApp | OK na tela | Integrações reais ou remover do plano |
| Regras fiscais | Prazos com dia útil/feriado e fuso de Brasília, validados por contador | Jobs e prioridade no fuso de Brasília; motor com dia útil e feriados nacionais/estaduais/capitais | **Parcial** | Validação profissional das regras |
| Auditoria de ações | Ações financeiras registradas | `audit_log` grava em `audit_events` (leva 2) | OK | — |
| Backup e restore | Restore testado | Sem acesso | **Não verificado** | Stack nova |
| Hospedagem | Plano permite uso comercial; domínio canônico definido | Vercel Hobby não permite uso comercial; domínios divergentes | **Falha** | Decisão de stack |
| Privacidade/LGPD | Mapa de dados, termos, resposta a incidente revisados | Não feito nesta rodada | **Não verificado** | Próxima rodada + jurídico |
| Marketing | Claims comprováveis | Não feito nesta rodada | **Não verificado** | Próxima rodada |

## O que pode ser mostrado hoje (como beta/demonstração)

Cadastro de escritório e clientes, documentos, obrigações, financeiro/contas a receber, fechamento mensal com PDF, relatórios e portal do cliente — "operacionais" segundo o README, não testados ponta a ponta em ambiente real nesta auditoria.

## O que não pode ser anunciado como pronto

Consulta e-CAC/Receita, emissão de NFS-e, envio por WhatsApp, caixa postal fiscal, cobrança automática por Mercado Pago, e-mail transacional (desligado por padrão), lembretes automáticos de cobrança.

## Próximos passos priorizados

1. Merge do PR #52 e deste PR (dono).
2. Definir a stack nova (banco, backend, frontend com plano comercial, Redis, e-mail, monitoramento) — conversa separada.
3. No banco novo: role da aplicação sem BYPASSRLS, `FORCE ROW LEVEL SECURITY` e testes de RLS em PostgreSQL real no CI.
4. Configurar `REDIS_URL` (Upstash) em produção.
5. Lembretes de cobrança com envio real, unicidade de CNPJ por escritório, idempotência da cobrança mensal (o `audit_log` real, o `RUN_SCHEDULER` e o fuso de Brasília entraram na leva 2).
6. Dia útil e feriados no motor de obrigações, revisado por contador.
7. LGPD, termos, plano de incidente, catálogo comercial e marketing.
