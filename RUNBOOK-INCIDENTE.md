# Runbook de incidente — FiscWise

Uma página, para a hora do susto. Detalhes de infraestrutura ficam no
[DEPLOY.md](DEPLOY.md) (§11 backup, §12 monitoramento).

## 1. Detectar (o que já existe)

- **Sentry** (backend `fiscwise-api` e frontend): erro novo chega por e-mail.
- **Cloud Logging**: log JSON de cada requisição (sem corpo, query string nem
  tokens, ver `app/core/request_log.py`). Alertas descritos no DEPLOY.md §12.
- **Avisos de terceiros**: Google Cloud, Supabase, Mercado Pago, Cloudflare,
  GitHub (secret scanning) e OpenAI mandam e-mail ao dono da conta.

## 2. Conter (primeiros 30 minutos)

| Situação | Ação |
|---|---|
| Deploy quebrou ou abriu falha | Cloud Run → serviço `fiscwise-api` → Revisões → mandar 100% do tráfego para a revisão anterior. |
| Segredo vazou (JWT, Supabase, Mercado Pago, OpenAI, cofre) | Gerar novo valor, criar versão nova no Secret Manager e publicar de novo. Trocar `JWT_SECRET_KEY` desloga todo mundo (esperado). |
| Conta de usuário comprometida | Redefinir a senha dela (`tokens_valid_after` derruba as sessões abertas) e revisar o `audit_log` do escritório. |
| Abuso ou ataque de volume | Ligar `RATE_LIMIT_STRICT=true` com Redis, ou regra de bloqueio no Cloudflare. |
| Dados corrompidos ou apagados | Restaurar o último dump do R2 em um banco **novo** (DEPLOY.md §11), comparar e só então migrar. Nunca restaurar por cima da produção sem cópia. |
| Cobrança indevida em massa | `PAGAMENTOS_GO_LIVE=false` em `cloudrun.env.yaml` e publicar. |

## 3. Registrar

Anotar em um arquivo `docs/audit/INCIDENTE-AAAA-MM-DD.md`: quando começou,
quando foi percebido, o que foi afetado (quais escritórios e quais dados), o que
foi feito e quando terminou. Esse registro é obrigatório pela LGPD (art. 48) e
serve de prova mesmo que o incidente não precise ser comunicado.

## 4. Comunicar (LGPD, art. 48 e Resolução CD/ANPD nº 15/2024)

Se houve acesso, vazamento ou perda de **dados pessoais** que possa causar
risco ou dano relevante aos titulares:

1. **Escritórios clientes** (o FiscWise é operador dos dados dos clientes
   deles): avisar o escritório afetado **imediatamente**, por e-mail, com o que
   se sabe até ali. O escritório é o controlador e decide a comunicação aos
   titulares dele.
2. **ANPD**: em até **3 dias úteis** do conhecimento do incidente, pelo
   formulário de comunicação de incidente no site da ANPD (gov.br/anpd), quando
   o FiscWise for o controlador (dados dos próprios usuários do sistema).
3. **Titulares**: no mesmo prazo, em linguagem simples: o que aconteceu, quais
   dados, o que já foi feito e o que a pessoa deve fazer (ex.: trocar a senha).

Contato do encarregado (DPO): `{{PREENCHER}}`.

## 5. Depois

Corrigir a causa com teste que prove a correção, e rodar a revisão de segurança
(`security-review`) antes de fechar o incidente.
