# Runbook de incidente — FiscWise

Uma página, para a hora do susto. Detalhes de infraestrutura ficam no
[DEPLOY.md](DEPLOY.md) (§11 backup, §12 monitoramento). Base legal: LGPD art. 48 e
Resolução CD/ANPD nº 15/2024. Texto jurídico revisado por IA: revisar com advogado.

**Encarregado (DPO):** VStack Solutions, privacidade@fiscwise.com.br · **Contato de plantão:** `{{PREENCHER}}`

## 1. Detectar (o que já existe)

- **Sentry** (backend `fiscwise-api` e frontend): erro novo chega por e-mail.
- **Cloud Logging**: log JSON de cada requisição (sem corpo, query string nem
  tokens, ver `app/core/request_log.py`). Alertas descritos no DEPLOY.md §12.
- **Avisos de terceiros**: Google Cloud, Supabase, Mercado Pago, Cloudflare,
  GitHub (secret scanning) e OpenAI mandam e-mail ao dono da conta; escritórios clientes avisam pelo suporte.

## 2. Conter (primeiros 30 minutos, sem apagar evidência)

| Situação | Ação |
|---|---|
| Deploy quebrou ou abriu falha | Cloud Run → serviço `fiscwise-api` → Revisões → mandar 100% do tráfego para a revisão anterior. |
| Segredo vazou (JWT, Supabase, Mercado Pago, OpenAI, cofre) | Gerar novo valor, criar versão nova no Secret Manager e publicar de novo. Trocar `JWT_SECRET_KEY` desloga todo mundo (esperado). |
| Certificado A1 de cliente exposto | Bloquear o certificado no cofre e avisar o escritório para revogar na autoridade certificadora. |
| Conta de usuário comprometida | Redefinir a senha dela (`tokens_valid_after` derruba as sessões abertas) e revisar o `audit_log` do escritório. |
| Abuso ou ataque de volume | Ligar `RATE_LIMIT_STRICT=true` com Redis, ou regra de bloqueio no Cloudflare. |
| Dados corrompidos ou apagados | Restaurar o último dump do R2 em um banco **novo** (DEPLOY.md §11), comparar e só então migrar. Nunca restaurar por cima da produção sem cópia. |
| Cobrança indevida em massa | `PAGAMENTOS_GO_LIVE=false` em `cloudrun.env.yaml` e publicar. |

## 3. Registrar (sempre, mesmo sem comunicar; guardar por 5 anos)

Criar `docs/audit/INCIDENTE-AAAA-MM-DD.md` com: data e hora do incidente e de quando se soube; como foi
descoberto; dados e titulares afetados (tipo e quantidade, quais escritórios); papel do FiscWise
(controlador ou operador); avaliação de risco e por quê; medidas com horário; comunicações feitas
(data, protocolo da ANPD, meio); causa raiz e PR da correção.

## 4. Avaliar e comunicar

**Há risco ou dano relevante?** Sim, se envolver dado sensível, financeiro, de autenticação (senha,
certificado), protegido por sigilo (fiscal), muitos titulares, ou puder gerar fraude ou discriminação.
Dado criptografado com a chave segura, em regra, não. Se não houver risco: só o registro da seção 3.

| Papel do FiscWise | Quem avisa quem | Prazo |
|---|---|---|
| **Operador** (dados da carteira dos escritórios) | FiscWise → **escritório afetado**, por e-mail ao dono, com o que se sabe até ali. O escritório (controlador) comunica a ANPD e os titulares dele, com a nossa ajuda | até **48 h** da confirmação (prometido no DPA, `/dpa`) |
| **Controlador** (usuários do sistema e cobrança) | FiscWise → **ANPD**, pelo formulário de comunicação de incidente em gov.br/anpd | até **3 dias úteis** da ciência |
| **Controlador** | FiscWise → **titulares afetados**, por e-mail, em linguagem simples | até **3 dias úteis** da ciência |

A comunicação diz: o que aconteceu e quando; quais dados e quantos titulares; riscos prováveis; o que já
foi feito e o que a pessoa deve fazer (ex.: trocar a senha, revogar o certificado); contato do encarregado.
Faltou informação? Comunicar o que se sabe no prazo e **complementar em até 20 dias úteis**.

## 5. Depois

Corrigir a causa com teste que prove a correção, rodar a revisão de segurança (`security-review`) antes de
fechar o incidente e ajustar este runbook se algum passo falhou.
