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
| Multi-tenant (banco) | RLS efetiva com role sem BYPASSRLS | Produção conecta como `fiscwise_app` (sem superusuário nem BYPASSRLS), dono das 49 tabelas. Migração `u7w8forcerls` (13/11): FORCE ROW LEVEL SECURITY nas 44 tabelas com RLS e exceção `current_app_tenant_id() IS NULL` nas policies — requisição autenticada só vê/grava o próprio escritório no banco; rotinas do sistema sem contexto seguem vendo tudo. Testado com dono sem poderes: API, 7 rotinas, webhook, ida e volta da migração; `test_rls_postgres.py` no CI; backup com `--enable-row-security` | OK | Endurecer depois: trocar a exceção 'sem contexto' por um sinal explícito de rotina do sistema |
| Pagamento | Assinatura do webhook, idempotência, trava | Código pronto (`billing.py`, `services/mercadopago.py`); `PAGAMENTOS_GO_LIVE=true` desde 13/11 (revisão `fiscwise-api-00035-2g2`). Webhook na URL `run.app` (DEPLOY.md §10) | **OK** | Cobrança real ligada pelo dono em 13/11. Aplicação "FiscWise" (nº 391216691873495) e webhook de produção criados em 13/11. Os 3 segredos estão no Secret Manager e montados no Cloud Run; o webhook de produção aceita a assinatura do MP. Homologação no sandbox em 13/11: assinatura mensal, pagamento avulso trimestral, aviso repetido e cancelamento OK; falta só o cartão recusado (opcional): [HOMOLOGACAO_MERCADO_PAGO.md](HOMOLOGACAO_MERCADO_PAGO.md) |
| Teste grátis | Sem plano gratuito permanente | Desde 13/11: todo cadastro ganha 14 dias do Premium sem cartão; **um teste por CNPJ/CPF** (documento obrigatório e validado, duplicado recusado mesmo com máscara); vencido = só leitura (402 `ACESSO_EXPIRADO`), exportar/assinar liberados; avisos D-3, D-1, D0 e vencido; **oferta de reconquista** 5 dias depois de vencer (15% no 1º mês do mensal ou anual com 25%, válida 7 dias, lembrete, descadastro), homologada no sandbox com a subida automática para o preço cheio; Termos v1.3 (`test_teste_gratis.py`, `test_teste_por_documento.py`, `test_oferta_reconquista.py`) | OK | Exclusão dos dados 60 dias após vencer ainda é manual |
| Auth | Rate limit, OTP, revogação | Rate limit por usuário em toda a API (`7d29043`); contador em memória (1 instância) | OK | `REDIS_URL` só quando passar de 1 instância |
| Cadastro | Aceite dos termos gravado | Google grava `terms_accepted_at` e `terms_version`; 403 `SIGNUP_INCOMPLETE` até `/concluir-cadastro` | OK | Testar o botão Google em produção |
| CI | Gates de segurança bloqueiam | `ci.yml` e `security-review.yml` verdes | OK | E2E é opcional (`continue-on-error`) |
| Funcionalidades honestas | Nada simulado parece real | Avisos em e-CAC, NFS-e, WhatsApp e cobrança | OK | Integrações reais exigem custo (abaixo) |
| Regras fiscais | Prazos com dia útil/feriado, validados por contador | `business_days.py`: nacionais, Carnaval, Corpus Christi, 22 UFs, 7 capitais | **Parcial** | Faltam 24/12 e 31/12, ES/GO/MG/MT/SC, municipais fora das capitais; **revisão por contador** |
| Backup e restore | Backup diário e restore testado | `db-backup.yml` diário 03:00 (Brasília), `pg_dump` criptografado com `age` (privada com o dono) no R2 `fiscwise-backups`, regra `expira-30d`; token R2 `fiscwise-backups-github` só para esse bucket. 1º backup em 13/11 (`fiscwise-20261113T1931Z.dump.age`, 236 KB) restaurado num PostgreSQL 17 limpo: 49 tabelas, dados e versão `t6v7oferta` | **OK** | Arquivos do Storage (Supabase) ainda não são copiados |
| Hospedagem | Domínio canônico | Cloud Run SP + Cloudflare Pages + Supabase; regra de redirecionamento 301 `fiscwise.com.br/*` → `https://www.fiscwise.com.br/${1}` com query string (13/11) | OK | — |
| Segurança do front | CSP ativa | `_headers` em Report-Only; hashes dos scripts embutidos agora gerados no build (o do tema estava desatualizado); cache `fiscwise-api` do SW guarda dados pessoais sem cifra por 7 dias | **Parcial** | Conferir console e ativar a CSP; rever o cache da API |
| Observabilidade | Erros capturados | Sentry `fiscwise-api` e `fiscwise-web` criados; `SENTRY_DSN` no `cloudrun.env.yaml`; `VITE_SENTRY_DSN` e `VITE_CF_BEACON_TOKEN` no Pages (13/11) | **Parcial** | Conferir o primeiro evento no Sentry e as visitas no Web Analytics depois do deploy; Search Console |
| LGPD | Mapa de dados, incidente, direitos do titular | `/account/export` (todos os dados do escritório em JSON, desde 13/11; arquivos pelas telas) e `/account/delete` (só registra o pedido) | **Parcial** | Mapa de dados e plano de incidente (jurídico); export completo; rotina de exclusão |
| Marketing | Claims comprováveis | `docs/marketing/` | **Não verificado** | Só depois da cobrança no ar |

## Código que falta (não depende do dono)

1. LCP do `/login` em 6,1 s (meta 2,5 s). Em 13/11: arquivos da tela baixam em paralelo com a entrada (preload), motor offline, Dexie e sonner fora da entrada. Falta medir de novo e, se preciso, dividir o CSS ([DIAGNOSTICO_A0_PERFORMANCE.md](DIAGNOSTICO_A0_PERFORMANCE.md)).
2. ~~`RegisterPage.tsx` tem preços fixos~~ — resolvido: o cadastro não mostra mais preços (só o teste grátis).
3. Sync: disparar o webhook `client.created` para clientes criados pelo push.
4. Tela de Sincronização usando `GET/POST /sync/conflicts`.
5. E2E offline (depende de backend de preview).
6. `tailwind-merge` 3 (exige Tailwind v4).
7. Mercado Pago: o painel avisa que a **API de Preferences será descontinuada**. O código usa `/checkout/preferences` (ciclos pré-pagos) e `/preapproval` (mensal); planejar a migração para a API de Orders.

## Custos futuros (nada contratado)

| Item | Custo estimado | Até lá |
|---|---|---|
| Certificado A1 para emitir NFS-e | ~R$ 150–250/ano | emissão fica em rascunho |
| SERPRO (consultas e-CAC) | por consulta | tela avisa que não está disponível |
| Provedor de WhatsApp | por mensagem | envio desligado com aviso |
| Assinatura do instalador Windows (Tauri) | ~US$ 200–400/ano | PWA instalável |
| Registro do software e da marca no INPI | taxa baixa | — |
