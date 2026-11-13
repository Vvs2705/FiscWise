# Homologação do Mercado Pago (sandbox)

Objetivo: provar, com contas de teste do Mercado Pago, que assinar, pagar,
renovar e cancelar funcionam de ponta a ponta **antes** de ligar
`PAGAMENTOS_GO_LIVE` em produção. Produção continua com `PAGAMENTOS_GO_LIVE: "false"`
durante todo este roteiro.

## 0. Preparar (uma vez)

1. Painel do MP → **Suas integrações** → criar a aplicação "FiscWise"
   (produto Checkout Pro / Assinaturas).
2. **Contas de teste**: criar duas — um *vendedor* e um *comprador*. Todo o
   teste usa as credenciais do vendedor de teste e o comprador paga com o
   e-mail dele (o MP recusa pagador igual ao vendedor).
3. Entrar no painel com o vendedor de teste e copiar o **Access Token** e a
   **Public Key** (começam com `APP_USR-` ou `TEST-`).
4. Subir o backend no PC com as credenciais de teste e a cobrança ligada **só
   ali** (arquivo `backend/.env`, nunca versionado):

   ```
   ENVIRONMENT=development
   PAGAMENTOS_GO_LIVE=true
   MERCADO_PAGO_ACCESS_TOKEN=<token do vendedor de teste>
   MERCADO_PAGO_PUBLIC_KEY=<public key do vendedor de teste>
   MERCADO_PAGO_WEBHOOK_SECRET=<passo 6>
   PUBLIC_URL=<URL do túnel, passo 5>
   APP_URL=http://localhost:5173
   ```

   Com `MERCADO_PAGO_WEBHOOK_SECRET` preenchido, a assinatura do webhook é
   sempre conferida, igual à produção. Não deixe esse campo vazio: em
   `development` sem segredo o webhook aceita qualquer coisa.
5. Túnel público para o webhook chegar no PC:
   `cloudflared tunnel --url http://localhost:8000` (grátis, sem conta). Anote a
   URL `https://<algo>.trycloudflare.com` e ponha em `PUBLIC_URL`.
6. Painel do MP → aplicação → **Webhooks** → aba **Modo de teste**:
   URL `https://<algo>.trycloudflare.com/api/v1/billing/webhook/mercadopago`,
   eventos **Pagamentos** e **Planos e assinaturas** (assinatura e pagamento
   recorrente). Salvar e copiar a **assinatura secreta** para
   `MERCADO_PAGO_WEBHOOK_SECRET`. Reiniciar o backend.
7. Frontend local (`npm run dev`) apontando para `http://localhost:8000`.
   Entrar com um escritório de teste cujo dono usa o **e-mail do comprador de
   teste**.

Para cada caso abaixo, anote: horário, id do pagamento/assinatura no MP e o
resultado. Os itens marcados **[banco]** se conferem na tabela
`tenant_subscriptions` (e o evento em `billing_webhook_events`).

## 1. Webhook assinado

| # | Passo | Esperado |
|---|---|---|
| 1.1 | Painel → Webhooks → **Simular notificação** (tipo `payment`) | Log do backend sem 401; resposta 200 no painel |
| 1.2 | `curl -X POST <túnel>/api/v1/billing/webhook/mercadopago -H 'content-type: application/json' -d '{"type":"payment","data":{"id":"1"}}'` (sem `x-signature`) | **401 Assinatura inválida** |
| 1.3 | Reenviar a mesma notificação pelo painel | 200 `already_processed` (não processa duas vezes) |

## 2. Assinatura mensal (cartão, recorrente)

| # | Passo | Esperado |
|---|---|---|
| 2.1 | Configurações → Assinar plano Premium, ciclo **mensal** | Redireciona para o checkout do MP |
| 2.2 | Pagar com cartão de teste aprovado (Mastercard `5031 4332 1540 6351`, CVV `123`, validade futura, titular `APRO`) | Volta para `/configuracoes?assinatura=ok` |
| 2.3 | Esperar o webhook `subscription_preapproval` | **[banco]** `status=active`, `current_period_end` ≈ hoje + 30 dias, plano Premium liberado na tela |
| 2.4 | Esperar o webhook `subscription_authorized_payment` (1ª cobrança) | **[banco]** `current_period_end` continua ≈ hoje + 30 (não vira 60) |
| 2.5 | Repetir 2.1–2.2 com titular `OTHE` (recusado) num segundo escritório | Plano **não** é liberado |

## 3. Avulso Pix (ciclo pré-pago)

| # | Passo | Esperado |
|---|---|---|
| 3.1 | Assinar ciclo **trimestral**, método **Pix** | Checkout do MP só com Pix, valor com 15% de desconto |
| 3.2 | Pagar o Pix de teste (no sandbox o QR se aprova pelo painel do comprador de teste ou fica pendente; anotar qual) | Webhook `payment` com `approved` |
| 3.3 | Conferir | **[banco]** `status=active`, `billing_cycle=trimestral`, `current_period_end` ≈ hoje + 90 dias |
| 3.4 | Pix vencido/não pago | Plano **não** é liberado |
| 3.5 | (Opcional) Estornar o pagamento no painel do vendedor | Webhook `payment` `refunded` → **[banco]** `status=suspended` |

## 4. Cancelamento mantendo o período pago

| # | Passo | Esperado |
|---|---|---|
| 4.1 | No escritório do caso 2, Configurações → **Cancelar assinatura** | Tela confirma; acesso Premium continua |
| 4.2 | Painel do MP (comprador) → assinatura | Status **cancelada** (cartão não será mais cobrado) |
| 4.3 | Webhook `subscription_preapproval` com `cancelled` | **[banco]** `status` segue `active`, `cancelled_at` preenchido, `current_period_end` igual ao de antes |
| 4.4 | Simular o fim do período: `update tenant_subscriptions set current_period_end = now() - interval '1 minute' where id = '<id>'` | Ao recarregar, plano volta para **Gratuito** |
| 4.5 | Cancelar de novo | Resposta igual, sem erro (idempotente) |

## 5. Critério para ligar em produção

Todos os itens 1–4 OK, com prints/ids anotados. Então, em produção:

1. Criar no Secret Manager os três segredos com as credenciais **de produção**
   (DEPLOY.md, passo 10).
2. Cadastrar no painel (aba **Modo produtivo**) a URL
   `https://fiscwise-api-45ckqevl6a-rj.a.run.app/api/v1/billing/webhook/mercadopago`
   e trocar `MERCADO_PAGO_WEBHOOK_SECRET` pela assinatura secreta de produção.
3. Só então mudar `PAGAMENTOS_GO_LIVE: "true"` em `cloudrun.env.yaml` (decisão
   do dono). O deploy falha de propósito se algum dos três segredos faltar.
4. Fazer uma assinatura real de valor baixo e cancelar em seguida (caso 4).
