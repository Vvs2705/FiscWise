# COMPLIANCE-40 — Frente jurídica (LGPD e CDC)

> Auditoria de 21/11/2026, blocos B (LGPD) e C (consumidor/comercial) do documento
> "40 requisitos". Os blocos A (segurança) e de banco foram feitos por outras frentes.
> **Os textos legais foram gerados e revisados por IA. Revisar com advogado antes de considerar definitivos.**

## 1. Perfil

**P2+.** SaaS B2B para escritórios contábeis, em produção, com cobrança recorrente pelo Mercado Pago
desde 13/11/2026. Multi-tenant com RLS. O FiscWise é **controlador** dos dados dos usuários e da cobrança
e **operador** dos dados da carteira de cada escritório (empresas, sócios, CPF de responsáveis,
documentos, notas, guias e certificados A1). Tem um Portal do Cliente para o cliente final do escritório.
Usa a OpenAI na Calculadora Fiscal e no assistente, com CPF e CNPJ mascarados antes do envio
(`backend/app/services/ai_fiscal.py:51`). Não trata dado sensível do art. 5º, II. Analytics só
Cloudflare Web Analytics, sem cookie.

O projeto já estava bem adiantado: política e termos publicados (v1.4), aceite no cadastro com
versão gravada, exportação de dados, pedido de exclusão, exclusão automática com aviso, cancelamento
pelo próprio sistema. A maior parte do trabalho foi **corrigir contradições e lacunas** nos textos, não criar coisa nova.

## 2. Vereditos

| Nº | Item | Veredito | Evidência ou o que foi feito |
|---|---|---|---|
| 11 | Política de privacidade | 🔧 APLICADO | Já existia (`/privacidade`). Reescrita para v1.5: papéis de controlador e operador, tabela dado → finalidade → base legal, seção de IA, integrações com órgãos públicos, retenção por tipo de dado. `frontend/src/pages/PrivacyPage.tsx` |
| 12 | Bases legais | 🔧 APLICADO | Tabela já existia; agora cada dado tem a sua base, incluindo Marco Civil para logs e "definida pelo controlador" para os dados da carteira. Consentimento só para marketing (opt-in), sem inventar consentimento |
| 13 | Minimização | ✅ ATENDE (sinalizado) | Campos coletados são usados. `responsible_address`/`responsible_phone` (`models/operations.py:89-90`) são opcionais e de uso do escritório; não removidos (seria migração, fora do escopo) |
| 14 | Finalidades documentadas | 🔧 APLICADO | Tabela "dado → finalidade" na seção 2 da política |
| 15 | Consentimento | ➖ N/A | Não há cookie não essencial; marketing já é opt-in. Nenhum sistema de consentimento criado |
| 16 | Política de cookies | ➖ N/A | Só armazenamento local do login e Cloudflare Web Analytics sem cookie. Seção 8 da política explica por que não há banner |
| 17 | Direitos dos titulares | ✅ ATENDE | Tela em Configurações → Perfil → Privacidade e dados (exportar e pedir exclusão) + e-mail `privacidade@`. **Corrigido o prazo**: dizia "15 dias úteis", a LGPD (art. 19, II) fala em 15 dias. Corrigido na política, na tela, na resposta da API e no e-mail |
| 18 | Exclusão de dados | ✅ ATENDE | `POST /account/delete` (pedido, `account.py:190`) e exclusão automática de conta vencida com aviso de 72 h (`services/exclusao_dados.py`). Ver lacuna L3 sobre o processamento manual do pedido |
| 19 | Retenção | 🔧 APLICADO | Prazos por tipo de dado na política. **Corrigida contradição**: a v1.4 dizia "dados de conta por até 5 anos após o encerramento", mas o código apaga a carteira em 60 dias. Agora: carteira 60 dias, registro do escritório e cobrança pelo prazo tributário, logs 6 meses, backups 30 dias |
| 20 | Contratos com operadores (DPA) | 🔧 APLICADO | Novo **Acordo de Tratamento de Dados** em `/dpa` (`frontend/src/pages/DpaPage.tsx`), incorporado aos Termos (seção 9), com suboperadores, aviso de incidente em 48 h, devolução e eliminação ao fim. Fornecedores (Google, Supabase, Cloudflare, Resend, Sentry, OpenAI, Mercado Pago) listados com referência ao DPA padrão de cada um |
| 30 | Transparência sobre IA | 🔧 APLICADO | Seção 3 da política lista os 4 usos da OpenAI, incluindo a **classificação automática de todo documento enviado** (a v1.4 dizia "só quando você usa", o que era falso), o que vai em cada um, mascaramento de CPF/CNPJ e que nomes não são mascarados. OpenAI listada como suboperadora no DPA. Correção de código: o nome do arquivo ia para a OpenAI sem máscara (`ai_fiscal.py`), agora mascarado, com teste. Termos seção 8: resposta da IA é apoio |
| 35 | Notificação de incidentes | 🔧 APLICADO | `RUNBOOK-INCIDENTE.md` (1 página) com fluxo ANPD e titulares em 3 dias úteis (Res. CD/ANPD 15/2024) e aviso de operador ao escritório em 48 h. Política seção 6 menciona o compromisso |
| — | Dados sensíveis | ➖ N/A | Nenhum dado do art. 5º, II no modelo. O DPA proíbe o escritório de cadastrá-los. Certificado A1 e senha (segredo crítico, não dado sensível) já ficam cifrados no cofre |
| 21 | Termos de uso | 🔧 APLICADO | Já existiam. v1.5: descrição fiel dos recursos, DPA, direito de arrependimento, aviso da IA, ressalva de foro do consumidor. `TERMS_VERSION` passou a `v1.5` (`onboarding.py`) |
| 22 | Transparência de preços | ✅ ATENDE | `/precos` mostra preço, ciclo, limites e como cancelar; preços vêm do banco (`precosHtml.ts`). Nada alterado (TRAVA) |
| 23 | Cobranças transparentes | ✅ ATENDE (com lacuna L2) | Recibo do Mercado Pago discrimina a cobrança. Ver L2 sobre a nota fiscal da própria VStack |
| 24 | Cancelamento | ✅ ATENDE | Botão "Cancelar assinatura" em Configurações → Plano (`SettingsPage.tsx:807`), sem e-mail. **Corrigido texto enganoso** no diálogo: dizia "seus clientes e documentos ficam guardados", sem avisar que são excluídos 60 dias depois |
| 25 | Arrependimento 7 dias | 🔧 APLICADO | Antes só aparecia dentro da cláusula de ofertas. Agora há cláusula geral nos Termos (seção 4) com o mínimo legal: consumidor, 7 dias do pagamento, devolução integral. Estender a todo cliente B2B é decisão comercial (ver 🔒) |
| 26 | Identificação do fornecedor | 🔧 APLICADO | Rodapé do app (`LoginShell.tsx`) e de `/precos` passam a mostrar CNPJ e cidade (Decreto 7.962/2013). Endereço completo pendente (`{{PREENCHER}}`, seção 5) |
| 27 | Publicidade | 🔧 APLICADO | Os Termos v1.4 diziam "emissão de DAS/DARF", mas o README diz que o sistema **não** gera guias. Corrigido, e os Termos agora avisam que NFS-e, e-CAC, Caixa Postal e WhatsApp dependem de homologação/contrato |
| 28 | Depoimentos | ✅ ATENDE | A landing é explícita: "sem depoimentos, números ou métricas" (`LandingPage.tsx:29`) |
| 29 | Licenças | ✅ ATENDE | Sem GPL/AGPL. npm: só MPL-2.0 em dependência de dev (axe-core). Python: `fpdf2` LGPL-3.0 usado sem modificação no servidor, `certifi` MPL-2.0: compatíveis |

## 3. Aplicado neste PR

- Política de Privacidade v1.5 e Termos de Uso v1.5 (aviso "revisar com advogado" em comentário no topo de cada arquivo).
- Nova página pública `/dpa` (rota, título, descrição e sitemap).
- `RUNBOOK-INCIDENTE.md`.
- Prazo LGPD de 15 dias corrigido em 4 lugares; texto de retenção alinhado ao código em 4 lugares.
- Diálogo de cancelamento sem promessa falsa de guarda dos dados.
- CNPJ e cidade no rodapé.
- Nome do arquivo mascarado antes de ir para a OpenAI (`backend/app/services/ai_fiscal.py`, teste em `tests/unit/test_ai_fiscal_documents.py`).
- Caminhos de menu errados nos textos legais (citavam "Configurações → Conta", que não existe) corrigidos para "Configurações → Perfil".

## 4. 🔒 Bloqueados (precisam do dono)

1. **Avisar os usuários atuais da mudança dos Termos.** A seção 11 dos Termos promete aviso por e-mail com 30 dias de
   antecedência para alterações materiais (15 dias na política). Enviar o e-mail é ação para fora do projeto. Passo: mandar
   e-mail aos donos dos escritórios ativos com link para `/termos`, `/privacidade` e `/dpa`, informando a vigência em 21/12/2026.
2. **Arrependimento para todo cliente.** Hoje a cláusula cobre só o consumidor (mínimo do CDC) e as ofertas. Se quiser
   devolver em 7 dias para qualquer escritório, é mudança de regra de cobrança: decidir e trocar o parágrafo nos Termos seção 4.

## 5. `{{PREENCHER}}` pendentes

- Endereço completo da sede (rua, número, CEP) para o rodapé e os Termos. Hoje só aparece "Caieiras/SP".
- Telefone/contato de plantão para incidentes (`RUNBOOK-INCIDENTE.md`).
- Nome da pessoa natural do encarregado, se quiser nomear alguém (hoje é a própria VStack, permitido pela Res. CD/ANPD 18/2024).
- Confirmar que as caixas `privacidade@fiscwise.com.br` e `juridico@fiscwise.com.br` existem e são lidas.

## 6. Lacunas do documento "40 requisitos" (o que ele não cobre e deveria)

- **L1. NF-e, NFS-e e SEFAZ.** O documento não fala de documento fiscal. O FiscWise guarda XMLs de notas e
  certificados A1 que assinam documentos com validade jurídica. Isso pede: registro de cada uso do certificado (já existe),
  bloqueio pelo escritório (já existe) e menção na política e no DPA (feito).
- **L2. Nota fiscal da própria VStack.** O documento só pede que a "fatura discrimine" (item 23). Como empresa, a VStack
  precisa emitir NFS-e de cada mensalidade recebida pelo Mercado Pago. Não há automação para isso no código. Verificar com o
  contador se as notas estão sendo emitidas.
- **L3. Retenção fiscal de 5 anos tem dois donos.** O documento trata "dados fiscais" como se a retenção fosse do sistema.
  Na verdade: a guarda de livros e documentos dos clientes (CTN art. 195) é do escritório e do cliente; a do FiscWise é só
  da própria cobrança. Os textos agora dizem isso e avisam o escritório para exportar antes da exclusão. O pedido de exclusão
  LGPD (`deletion_requested_at`) é tratado à mão e não há tela de admin para isso: vale um script/rota admin no futuro.
- **L4. Papel de operador e Portal do Cliente.** O documento menciona DPA mas não o fluxo de pedidos de titular que são
  clientes do escritório. Resolvido no DPA (repasse ao controlador em 5 dias úteis).
- **L5. Marco Civil da Internet.** O documento não cita a guarda obrigatória de registros de acesso por 6 meses (art. 15).
  A política já dizia 6 meses; agora cita a base legal. Conferir com a frente de banco/segurança se os logs do Cloud Run
  realmente ficam 6 meses (o padrão do Cloud Logging é 30 dias).
- **L6. Decreto 7.962/2013 (comércio eletrônico).** O item 26 cobre a identificação, mas o decreto também exige resumo do
  contrato antes da compra e confirmação imediata do pedido. O e-mail de boas-vindas da assinatura já cobre isso
  (`email_service.py:366`).
- **L7. Contador autônomo como consumidor.** O documento trata B2B como fora do CDC. A jurisprudência (teoria finalista
  mitigada) pode tratar o contador autônomo ou o MEI como consumidor vulnerável. Por isso a cláusula de arrependimento e a
  ressalva de foro foram incluídas.

## 7. Status

PR aberto e mesclado na `main` por fast-forward depois da suíte verde (link no thread).
