# RUNBOOK — Incidente de segurança com dados pessoais

> Uma página. Gerado na auditoria COMPLIANCE-40 (21/11/2026). Revisar com advogado.
> Base: LGPD art. 48 e Resolução CD/ANPD nº 15/2024 (Regulamento de Comunicação de Incidente).

**Quem decide:** o dono da VStack Solutions (encarregado: privacidade@fiscwise.com.br).
**Telefone e contato de plantão:** `{{PREENCHER}}`

## 1. Primeira hora: conter

1. Confirmar o incidente: alerta do Sentry ou Better Stack, log do Cloud Run, aviso de cliente ou de fornecedor.
2. Conter sem apagar evidência:
   - credencial vazada → revogar e trocar (Secret Manager do GCP, Supabase, GitHub, Mercado Pago, Resend, OpenAI);
   - sessão comprometida → invalidar tokens do usuário (`users.tokens_valid_after`);
   - certificado A1 exposto → bloquear o certificado no cofre e avisar o escritório para revogar na AC;
   - falha no código → rollback para a revisão anterior no Cloud Run.
3. Abrir o registro do incidente (modelo na seção 4) com data e hora em que se soube.

## 2. Até 2 dias úteis: avaliar

Responder por escrito:

- Quais dados? Comuns (nome, e-mail, CPF, CNPJ) ou sensíveis? Certificados digitais e senhas? Dados fiscais ou financeiros?
- Quantos titulares e quantos escritórios? Há menores de idade?
- O dado estava criptografado e a chave ficou segura?
- O incidente **pode causar risco ou dano relevante** aos titulares? (art. 5º da Res. 15/2024: dado sensível,
  financeiro, de autenticação, protegido por sigilo, em larga escala, ou que pode gerar fraude ou discriminação).

Se **não** houver risco relevante: só registrar (seção 4) e guardar por 5 anos. Fim.

## 3. Até 3 dias úteis da ciência: comunicar

| Papel do FiscWise | Quem avisa quem | Prazo |
|---|---|---|
| **Operador** (dados da carteira do escritório) | FiscWise → **escritório afetado** (e-mail ao dono). O escritório é quem comunica a ANPD e os titulares, com a nossa ajuda | até **48 h** da confirmação (prazo do DPA, `/dpa`) |
| **Controlador** (dados dos nossos usuários e da cobrança) | FiscWise → **ANPD** pelo formulário de comunicação de incidente no site gov.br/anpd | até **3 dias úteis** |
| **Controlador** | FiscWise → **titulares afetados**, por e-mail, em linguagem simples | até **3 dias úteis** |

A comunicação à ANPD e aos titulares deve dizer: o que aconteceu e quando; quais dados e quantos titulares;
riscos prováveis; medidas tomadas e as que o titular pode tomar (ex.: trocar senha, revogar certificado);
contato do encarregado. Se faltar informação, comunicar o que se sabe no prazo e **complementar em até 20 dias úteis**.

## 4. Registro (guardar por 5 anos, mesmo sem comunicar)

```
Data/hora da ciência:            Data/hora do incidente:
Como foi descoberto:
Dados e titulares afetados (tipo e quantidade):
Papel do FiscWise: controlador | operador (escritórios: ...)
Avaliação de risco e justificativa:
Medidas de contenção (com horário):
Comunicação ANPD: data / protocolo        Titulares: data / meio        Escritórios: data
Causa raiz e correção definitiva (commit/PR):
```

## 5. Depois

- Corrigir a causa raiz com teste automatizado, em PR.
- Se houve restauração, seguir DEPLOY.md seção 11 (backup no R2, chave `age` no cofre).
- Revisar este runbook se algum passo falhou.
