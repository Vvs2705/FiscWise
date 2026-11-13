# Prontidão para lançamento — FiscWise (atualizado em 13/11/2026)

## Resultado: **NO-GO**

O código está quase todo pronto. O que segura o lançamento é configuração de
painel, homologação da cobrança, backup e validação profissional. Achados da
auditoria original: [AUDIT_FINDINGS.md](AUDIT_FINDINGS.md). Este documento é a
lista única do que falta (substitui o antigo `RELATORIO_NOTURNO_FISCWISE.md`).

| Gate | Critério | Evidência | Status | O que falta |
|---|---|---|---|---|
| Segredos | Nenhum segredo válido no repositório | `.mcp.json` removido; o banco daquela credencial foi excluído. Secrets sem uso do GitHub apagados em 13/11 | OK | — |
| Multi-tenant (código) | Nenhum vazamento entre escritórios nem do portal | `test_client_role_isolation.py` | OK | — |
| Multi-tenant (banco) | RLS efetiva com role sem BYPASSRLS | `test_rls_postgres.py` roda no CI (só `accounting_clients`, só SELECT); produção conecta como dono | **Parcial** | Role da aplicação sem bypass no Supabase e usar na `DATABASE_URL`; testar INSERT/UPDATE e as outras tabelas |
| Pagamento | Assinatura do webhook, idempotência, trava | Código pronto (`billing.py`, `services/mercadopago.py`); `PAGAMENTOS_GO_LIVE=false`; tela avisa "Pagamentos em ativação". Webhook na URL `run.app` (DEPLOY.md §10) | **Parcial** | Aplicação no painel do MP, 3 segredos no Secret Manager, homologação: [HOMOLOGACAO_MERCADO_PAGO.md](HOMOLOGACAO_MERCADO_PAGO.md) |
| Auth | Rate limit, OTP, revogação | Rate limit por usuário em toda a API (`7d29043`); contador em memória (1 instância) | OK | `REDIS_URL` só quando passar de 1 instância |
| Cadastro | Aceite dos termos gravado | Google grava `terms_accepted_at` e `terms_version`; 403 `SIGNUP_INCOMPLETE` até `/concluir-cadastro` | OK | Testar o botão Google em produção |
| CI | Gates de segurança bloqueiam | `ci.yml` e `security-review.yml` verdes | OK | E2E é opcional (`continue-on-error`) |
| Funcionalidades honestas | Nada simulado parece real | Avisos em e-CAC, NFS-e, WhatsApp e cobrança | OK | Integrações reais exigem custo (abaixo) |
| Regras fiscais | Prazos com dia útil/feriado, validados por contador | `business_days.py`: nacionais, Carnaval, Corpus Christi, 22 UFs, 7 capitais | **Parcial** | Faltam 24/12 e 31/12, ES/GO/MG/MT/SC, municipais fora das capitais; **revisão por contador** |
| Backup e restore | Backup diário e restore testado | `db-backup.yml` existe mas é **pulado todo dia** (sem `BACKUP_AGE_RECIPIENT`) | **Não feito** | Chave `age`, token R2 (`R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`), rodar e testar restore; Storage não é copiado |
| Hospedagem | Domínio canônico | Cloud Run SP + Cloudflare Pages + Supabase | **Parcial** | Redirect 301 de `fiscwise.com.br` para `www` |
| Segurança do front | CSP ativa | `_headers` em Report-Only; cache `fiscwise-api` do SW guarda dados pessoais sem cifra por 7 dias | **Parcial** | Conferir console e ativar a CSP; rever o cache da API |
| Observabilidade | Erros capturados | Código do Sentry e do Cloudflare Web Analytics pronto | **Não feito** | `SENTRY_DSN`, `VITE_SENTRY_DSN`, `VITE_CF_BEACON_TOKEN`; Search Console |
| LGPD | Mapa de dados, incidente, direitos do titular | `/account/export` (só contagens) e `/account/delete` (só registra o pedido) | **Parcial** | Mapa de dados e plano de incidente (jurídico); export completo; rotina de exclusão |
| Marketing | Claims comprováveis | `docs/marketing/` | **Não verificado** | Só depois da cobrança no ar |

## Código que falta (não depende do dono)

1. LCP do `/login` em 6,1 s (meta 2,5 s): dividir o CSS e tirar `vendor-react`/`vendor-form` do caminho crítico ([DIAGNOSTICO_A0_PERFORMANCE.md](DIAGNOSTICO_A0_PERFORMANCE.md)).
2. `RegisterPage.tsx` tem preços fixos; devem vir de `/api/v1/subscription/plans`.
3. Sync: disparar o webhook `client.created` para clientes criados pelo push.
4. Tela de Sincronização usando `GET/POST /sync/conflicts`.
5. E2E offline (depende de backend de preview).
6. `tailwind-merge` 3 (exige Tailwind v4).

## Custos futuros (nada contratado)

| Item | Custo estimado | Até lá |
|---|---|---|
| Certificado A1 para emitir NFS-e | ~R$ 150–250/ano | emissão fica em rascunho |
| SERPRO (consultas e-CAC) | por consulta | tela avisa que não está disponível |
| Provedor de WhatsApp | por mensagem | envio desligado com aviso |
| Assinatura do instalador Windows (Tauri) | ~US$ 200–400/ano | PWA instalável |
| Registro do software e da marca no INPI | taxa baixa | — |
