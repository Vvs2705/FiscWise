# FiscWise — Equipe Antigravyti
## Produto operacional, frontend, fluxos fiscais, QA e experiência de sistema real

**Objetivo:** transformar o FiscWise em uma central operacional fiscal usável no dia a dia, não em um dashboard bonito.

**Escopo da equipe:** frontend, navegação, experiência de uso, fluxos fiscais, rotas, componentes, estados, validações, portal, relatórios, QA, E2E, linguagem de produto e integração com endpoints da Equipe Claude.

**Regra:** nenhuma tela deve ser feita apenas para parecer completa. Toda tela deve resolver uma operação real do contador.

---

# 1. Revisão visual da limpeza do repositório

Após a Equipe Claude limpar o repositório, validar:

```txt
README.md
docs/SECURITY_CORRECTIONS.md
frontend/
public/
src/
```

## 1.1 README

O README deve ser institucional e técnico, sem cara de diário de projeto.

Estrutura:

```md
# FiscWise

Sistema operacional fiscal para contadores autônomos e escritórios contábeis em evolução.

## O que o produto faz
## Stack
## Arquitetura resumida
## Setup local
## Variáveis de ambiente
## Testes
## Segurança
```

Remover:

- histórico de commits;
- checklist antigo;
- roadmap antigo;
- links para Swagger em produção;
- menção a ContaFlow;
- promessas não implementadas;
- prints antigos;
- textos de MVP.

## 1.2 Memória local

Criar localmente:

```txt
FISCWISE_MEMORIA_LOCAL.md
```

Modelo:

```md
# FiscWise — Memória Local de Execução

## Última atualização
## Equipe
## Branch
## Concluído hoje
## Pendências
## Bugs encontrados
## Decisões de produto
## Rotas/telas alteradas
## Contratos aguardando backend
## Próxima execução
```

Regra:

```txt
NUNCA COMMITAR.
NUNCA ENVIAR PARA O GITHUB.
NUNCA USAR COMO DOCUMENTAÇÃO OFICIAL.
```

Validar:

```bash
git check-ignore -v FISCWISE_MEMORIA_LOCAL.md
```

---

# 2. Reposicionamento funcional do produto

A interface deve responder diariamente:

```txt
o que está pendente?
o que vence hoje?
o que foi emitido?
o que foi pago?
o que está irregular?
o que depende do cliente?
o que depende do contador?
o que depende de certificado/procuração?
o que já está comprovado?
```

Substituir linguagem genérica:

```txt
Dashboard → Painel
Produtividade → Foco de Hoje / Esteira Operacional
Agenda → Agenda Fiscal
DAS Mensal → Guias e Pagamentos
Admin → Configurações / Operação
```

---

# 3. Menu principal

Implementar nova navegação:

```txt
Painel
Foco de Hoje
Clientes
Fechamento Mensal
Notas Fiscais
Central Receita/e-CAC
Guias e Pagamentos
Obrigações
Documentos
Caixa Postal Fiscal
Procurações
Certificados
Financeiro
WhatsApp
Portal do Cliente
Relatórios
Aprender
Configurações
```

Preparar expansão futura para escritórios maiores:

```txt
Responsáveis
Times
Filas de trabalho
Permissões por módulo
Carteiras de clientes
SLA interno
Aprovação de emissão/cancelamento
Auditoria por usuário
```

Esses itens podem ficar por feature flag/plano, mas a arquitetura visual deve comportar a evolução.

---

# 4. Rotas frontend

Criar ou ajustar:

```txt
/painel
/foco

/clientes
/clientes/:id

/fechamento
/fechamento/:id
/fechamento/:id/dossie

/notas-fiscais
/notas-fiscais/nova
/notas-fiscais/:id
/notas-fiscais/:id/eventos
/notas-fiscais/configuracoes

/ecac
/ecac/clientes
/ecac/clientes/:id
/ecac/clientes/:id/situacao-fiscal
/ecac/clientes/:id/caixa-postal
/ecac/clientes/:id/guias

/guias
/guias/:id

/obrigacoes
/documentos

/caixa-postal-fiscal
/caixa-postal-fiscal/:id

/procuracoes
/procuracoes/nova
/procuracoes/:id

/certificados
/certificados/novo
/certificados/:id

/financeiro
/whatsapp
/portal
/relatorios
/aprender
/configuracoes
```

Usar lazy loading nas páginas novas.

---

# 5. Design system operacional

Criar/expandir:

```txt
src/components/ui/PageHeader.tsx
src/components/ui/SectionHeader.tsx
src/components/ui/DataTable.tsx
src/components/ui/StatusBadge.tsx
src/components/ui/RiskBadge.tsx
src/components/ui/Timeline.tsx
src/components/ui/AuditTimeline.tsx
src/components/ui/EntityDrawer.tsx
src/components/ui/ConfirmDialog.tsx
src/components/ui/PermissionGate.tsx
src/components/ui/FeatureGate.tsx
src/components/ui/SignedFileLink.tsx
src/components/ui/CopyButton.tsx
src/components/ui/Stepper.tsx
src/components/ui/EmptyState.tsx
src/components/ui/ErrorState.tsx
src/components/ui/LoadingState.tsx
src/components/ui/SkeletonTable.tsx
src/components/ui/MetricCard.tsx
src/components/ui/ActionCard.tsx
src/components/ui/WarningPanel.tsx
```

## 5.1 Status globais

Notas:

```txt
draft
validating
ready_to_issue
issuing
processing
issued
rejected
cancel_requested
cancelled
failed
```

Guias:

```txt
draft
generated
sent_to_customer
awaiting_payment
paid
overdue
cancelled
divergent
```

Procurações:

```txt
pending
active
expired
revoked
invalid
unknown
```

Certificados:

```txt
valid
expiring
expired
revoked
invalid
```

Fechamento:

```txt
not_started
in_progress
blocked
ready_for_review
completed
reopened
```

## 5.2 Estados vazios

Notas fiscais:

```txt
Nenhuma nota emitida nesta competência.
Comece emitindo uma NFS-e de honorários ou configure o emissor fiscal.
```

Central Receita/e-CAC:

```txt
Nenhum cliente conectado à Central Receita/e-CAC.
Cadastre certificado e procuração para iniciar consultas oficiais.
```

Fechamento:

```txt
Nenhum fechamento aberto para esta competência.
Gere a rotina mensal para montar obrigações, guias, notas e pendências.
```

---

# 6. Painel e Foco de Hoje

## 6.1 Painel

Exibir estado real da operação:

```txt
Obrigações vencendo hoje
Notas rejeitadas
Notas aguardando emissão
Guias vencidas
Guias aguardando pagamento
Clientes com pendência e-CAC
Certificados vencendo
Procurações vencendo
Mensagens fiscais críticas
Fechamentos bloqueados
Documentos aguardando cliente
Honorários em atraso
```

## 6.2 Foco de Hoje

Criar tela:

```txt
/foco
```

Agrupar por:

```txt
Crítico
Hoje
Esta semana
Aguardando cliente
Aguardando órgão/provedor
```

Cada item deve conter:

```txt
tipo
cliente
competência
prazo
risco
ação principal
ação secundária
status
responsável
```

Ações rápidas:

```txt
Emitir NFS-e
Consultar situação fiscal
Gerar guia
Enviar cobrança
Solicitar documento
Abrir fechamento
Enviar WhatsApp
Baixar dossiê
```

---

# 7. Cliente 360

Expandir:

```txt
/clientes/:id
```

Abas:

```txt
Resumo
Documentos
Obrigações
Notas Fiscais
Guias
e-CAC
Caixa Postal
Procurações
Certificados
Financeiro
Fechamentos
Histórico
```

Resumo deve mostrar:

```txt
saúde fiscal
pendências críticas
próximo vencimento
última nota emitida
última guia paga
última consulta e-CAC
documentos pendentes
honorários em aberto
```

Ações rápidas:

```txt
emitir nota
consultar e-CAC
gerar guia
solicitar documento
abrir fechamento
enviar WhatsApp
criar cobrança
```

---

# 8. Módulo Notas Fiscais

## 8.1 Arquivos

```txt
src/pages/invoices/InvoicesPage.tsx
src/pages/invoices/NewInvoicePage.tsx
src/pages/invoices/InvoiceDetailPage.tsx
src/pages/invoices/InvoiceEventsPage.tsx
src/pages/invoices/IssuerSettingsPage.tsx

src/features/invoices/api.ts
src/features/invoices/types.ts
src/features/invoices/hooks.ts
```

Componentes:

```txt
src/features/invoices/components/InvoiceStatusBadge.tsx
src/features/invoices/components/InvoiceForm.tsx
src/features/invoices/components/InvoiceIssuerCard.tsx
src/features/invoices/components/InvoiceServiceProfileSelect.tsx
src/features/invoices/components/InvoiceTotalsBox.tsx
src/features/invoices/components/InvoiceValidationPanel.tsx
src/features/invoices/components/InvoiceFilesPanel.tsx
src/features/invoices/components/InvoiceTimeline.tsx
src/features/invoices/components/InvoiceCustomerCard.tsx
```

## 8.2 Fluxo de emissão

Stepper:

```txt
1. Emissor
2. Tomador
3. Serviço
4. Valores e retenções
5. Revisão fiscal
6. Emitir
7. Resultado
```

## 8.3 Listagem

Filtros:

```txt
competência
cliente
emissor
status
tipo
valor
data de emissão
rejeitadas
canceladas
sem XML
sem PDF
```

Colunas:

```txt
número
cliente/tomador
emissor
competência
serviço
valor
status
emissão
ações
```

Ações:

```txt
ver detalhes
emitir
cancelar
baixar XML
baixar PDF/DANFSe
enviar ao cliente
vincular cobrança
vincular fechamento
```

## 8.4 Detalhe da nota

Seções:

```txt
Resumo
Tomador
Serviço
Valores
Retenções
Arquivos
Eventos
Auditoria
Cobrança vinculada
Fechamento vinculado
```

## 8.5 Rejeição

Exibir:

```txt
motivo técnico
motivo amigável
campo afetado
ação recomendada
botão corrigir e reenviar
```

Nunca exibir payload bruto por padrão.

---

# 9. Central Receita/e-CAC

## 9.1 Arquivos

```txt
src/pages/ecac/EcacPage.tsx
src/pages/ecac/EcacSubjectPage.tsx
src/pages/ecac/TaxStatusPage.tsx
src/pages/ecac/EcacMailboxPage.tsx
src/pages/ecac/EcacGuidesPage.tsx

src/features/ecac/api.ts
src/features/ecac/types.ts
src/features/ecac/hooks.ts
```

## 9.2 Tela principal

Mostrar:

```txt
clientes conectados
clientes sem procuração
clientes com certificado vencido
pendências fiscais
consultas recentes
falhas de autorização
serviços disponíveis
fila de sincronização
```

## 9.3 Detalhe por cliente

Abas:

```txt
Situação fiscal
Pendências
Guias
Caixa postal
Procurações
Certificados
Histórico de consultas
```

Botões:

```txt
Sincronizar agora
Ver pendências
Gerar guia
Atualizar procuração
Atualizar certificado
Criar tarefa
```

## 9.4 Erros operacionais

Traduzir erros técnicos para ação:

```txt
certificado vencido → atualizar certificado
procuração inexistente → cadastrar procuração
procuração expirada → renovar procuração
serviço não autorizado → revisar poderes
provider indisponível → tentar novamente
quota excedida → aguardar/upgrade
dados fiscais incompletos → completar cadastro
```

---

# 10. Procurações

Arquivos:

```txt
src/pages/powers/PowersOfAttorneyPage.tsx
src/pages/powers/NewPowerOfAttorneyPage.tsx
src/pages/powers/PowerOfAttorneyDetailPage.tsx
src/features/powers/api.ts
src/features/powers/types.ts
```

Campos:

```txt
cliente
CPF/CNPJ outorgante
CPF/CNPJ procurador
serviços autorizados
validade
status
provider
última verificação
observações
```

Alertas:

```txt
procuração vencendo em 30 dias
procuração vencida
serviço necessário não autorizado
cliente sem procuração
```

Usar em bloqueios/alertas de:

```txt
consulta e-CAC
geração de DAS/DARF
consulta caixa postal
emissão em nome de cliente
```

---

# 11. Certificados

Arquivos:

```txt
src/pages/certificates/CertificatesPage.tsx
src/pages/certificates/NewCertificatePage.tsx
src/pages/certificates/CertificateDetailPage.tsx
src/features/certificates/api.ts
src/features/certificates/types.ts
```

Campos:

```txt
dono
CPF/CNPJ
tipo A1/A3/cloud
validade
status
vínculos
último uso
ações dependentes
```

UX de segurança para A1:

- upload claro;
- senha nunca exibida;
- aviso de armazenamento seguro;
- confirmação explícita;
- auditoria de uso.

Alertas:

```txt
certificado vence em 60 dias
certificado vence em 30 dias
certificado vence em 15 dias
certificado vence em 7 dias
certificado vencido
certificado inválido
certificado sem vínculo
```

---

# 12. Guias e Pagamentos

Arquivos:

```txt
src/pages/guides/FiscalGuidesPage.tsx
src/pages/guides/FiscalGuideDetailPage.tsx
src/features/guides/api.ts
src/features/guides/types.ts
```

Colunas:

```txt
cliente
tipo
competência
vencimento
valor
status
pagamento
comprovante
ações
```

Ações:

```txt
baixar guia
enviar ao cliente
anexar comprovante
marcar como paga
ver divergência
vincular fechamento
```

Divergência:

```txt
valor esperado
valor comprovado
data de pagamento
diferença
risco
ação recomendada
```

---

# 13. Caixa Postal Fiscal

Arquivos:

```txt
src/pages/fiscal-mailbox/FiscalMailboxPage.tsx
src/pages/fiscal-mailbox/FiscalMailboxMessagePage.tsx
src/features/fiscal-mailbox/api.ts
src/features/fiscal-mailbox/types.ts
```

Filtros:

```txt
cliente
risco
prazo
status
órgão
lida/não lida
com tarefa criada
```

Detalhe:

```txt
Resumo
Mensagem
Cliente afetado
Prazo
Risco
Ações
Histórico
```

Ações:

```txt
criar tarefa
marcar como resolvida
vincular obrigação
notificar cliente
baixar evidência
```

---

# 14. Fechamento Mensal

Arquivos:

```txt
src/pages/monthly-closing/MonthlyClosingsPage.tsx
src/pages/monthly-closing/MonthlyClosingDetailPage.tsx
src/pages/monthly-closing/FiscalDossierPage.tsx
src/features/monthly-closing/api.ts
src/features/monthly-closing/types.ts
```

## 14.1 Listagem

Colunas:

```txt
cliente
competência
status
score
documentos
notas
guias
obrigações
e-CAC
bloqueios
ações
```

## 14.2 Detalhe

Blocos:

```txt
Resumo
Checklist operacional
Documentos
Notas fiscais
Guias
Obrigações
Pendências e-CAC
Caixa postal
Comprovantes
Eventos
Dossiê
```

## 14.3 Score

```txt
100 completo
80-99 pequenas pendências
50-79 atenção
0-49 crítico
```

Fatores:

```txt
documentos faltando
obrigações atrasadas
guias vencidas
notas rejeitadas
pendências e-CAC
certificado/procuração vencida
comprovante ausente
```

## 14.4 Dossiê

Ações:

```txt
gerar dossiê
baixar PDF
baixar ZIP
enviar ao cliente
ver histórico de geração
```

---

# 15. Portal do Cliente

Expandir portal para reduzir trabalho manual do contador.

Funcionalidades:

```txt
enviar documentos
ver solicitações
ver guias enviadas
anexar comprovantes
baixar notas fiscais recebidas
responder pendências
ver status do fechamento
```

Cliente nunca deve ver:

```txt
outros clientes
dados internos do contador
payload técnico
credenciais fiscais
certificados
audit log técnico
```

---

# 16. Financeiro conectado à nota fiscal

Fluxos:

```txt
honorário recorrente → cobrança → nota fiscal → envio → recebimento → dossiê
serviço avulso → lançamento → nota fiscal → cobrança → recebimento
inadimplência → aviso → WhatsApp/e-mail → bloqueio opcional
```

Adicionar ao financeiro:

```txt
notas vinculadas
cobranças sem nota
notas sem cobrança
honorários vencidos
emissão em lote
```

Indicadores:

```txt
receita faturada
receita recebida
notas emitidas
notas rejeitadas
cobranças sem nota
clientes inadimplentes
```

---

# 17. Relatórios e BI

Relatórios obrigatórios:

```txt
Clientes por risco fiscal
Obrigações por status
Notas fiscais por competência
Guias em aberto
Guias pagas
Procurações vencendo
Certificados vencendo
Fechamentos por competência
Receita por cliente
Inadimplência
Pendências e-CAC
Mensagens fiscais críticas
```

Exportações:

```txt
CSV
XLSX
PDF
ZIP do dossiê
```

Permissões financeiras apenas para:

```txt
owner
admin
financeiro, quando existir
```

---

# 18. Feature flags e planos

Implementar gates:

```txt
feature_nfse
feature_ecac
feature_certificates
feature_powers_of_attorney
feature_fiscal_guides
feature_fiscal_mailbox
feature_monthly_closing
feature_fiscal_dossier
feature_whatsapp
feature_public_api
```

Planos sugeridos:

```txt
Starter
  clientes limitados
  documentos
  obrigações básicas
  financeiro simples

Professional
  NFS-e própria
  fechamento mensal
  portal do cliente
  WhatsApp
  guias

Business
  e-CAC/Integra Contador
  emissão para clientes
  procurações
  caixa postal fiscal
  dossiê fiscal
  API pública

Enterprise
  times
  múltiplas carteiras
  auditoria avançada
  permissões granulares
  SLA
  integrações customizadas
```

---

# 19. Integração frontend com API

Criar services:

```txt
src/features/invoices/api.ts
src/features/ecac/api.ts
src/features/certificates/api.ts
src/features/powers/api.ts
src/features/guides/api.ts
src/features/fiscal-mailbox/api.ts
src/features/monthly-closing/api.ts
```

Query keys:

```txt
['invoices', filters]
['invoice', id]
['ecac-subjects']
['tax-status', subjectId]
['certificates']
['powers-of-attorney']
['fiscal-guides', filters]
['fiscal-mailbox', filters]
['monthly-closings', competence]
['monthly-closing', id]
```

Mutations:

```txt
createInvoice
issueInvoice
cancelInvoice
syncEcacSubject
createCertificate
createPowerOfAttorney
sendGuideToCustomer
uploadPaymentProof
generateFiscalDossier
```

Erros padrão:

```txt
CERTIFICATE_EXPIRED
POWER_OF_ATTORNEY_MISSING
PROVIDER_UNAVAILABLE
INVOICE_REJECTED
TENANT_LIMIT_EXCEEDED
FEATURE_NOT_AVAILABLE
STORAGE_FILE_BLOCKED
RATE_LIMITED
```

---

# 20. QA visual e funcional

Criar E2E:

```txt
frontend/e2e/auth.spec.ts
frontend/e2e/client-360.spec.ts
frontend/e2e/invoices.spec.ts
frontend/e2e/ecac.spec.ts
frontend/e2e/guides.spec.ts
frontend/e2e/monthly-closing.spec.ts
frontend/e2e/portal-client.spec.ts
```

Fluxos mínimos:

```txt
login
2FA
criar cliente
configurar certificado
configurar procuração
emitir nota mock
nota rejeitada
nota emitida
gerar guia
anexar comprovante
abrir fechamento
gerar dossiê
portal envia documento
portal anexa comprovante
```

Estados obrigatórios em todas as telas:

```txt
loading
empty
error
success
permission denied
feature locked
data stale
provider unavailable
```

Responsividade:

```txt
desktop 1440
desktop 1280
tablet
mobile
```

---

# 21. Padrão de implementação

Cada página nova deve conter:

```txt
Page
├── header
├── filters
├── primary action
├── main table/list
├── drawer/detail
├── empty/error/loading states
├── permission gate
├── feature gate
└── audit/event timeline quando aplicável
```

Cada PR deve conter:

```txt
print ou vídeo curto da tela
rotas alteradas
componentes criados
estados tratados
permissões consideradas
impacto em mobile
testes executados
```

---

# 22. Ordem de execução

```txt
1. Validar limpeza do README e docs.
2. Validar memória local ignorada.
3. Ajustar navegação principal.
4. Criar design components operacionais.
5. Criar FeatureGate e PermissionGate robustos.
6. Criar Foco de Hoje.
7. Expandir Cliente 360.
8. Criar Notas Fiscais frontend com provider mock.
9. Criar Certificados.
10. Criar Procurações.
11. Criar Central Receita/e-CAC.
12. Criar Guias e Pagamentos.
13. Criar Caixa Postal Fiscal.
14. Criar Fechamento Mensal.
15. Criar Dossiê Fiscal.
16. Integrar Financeiro com notas e cobranças.
17. Atualizar Portal do Cliente.
18. Criar Relatórios fiscais.
19. Criar E2E.
20. Validar staging completo.
```

---

# 23. Definition of Done

Um item da Equipe Antigravyti só está concluído quando:

```txt
rota criada
componente funcional
integração com API ou mock contract
permissões aplicadas
feature flag aplicada
loading/empty/error tratados
layout responsivo mínimo
textos claros
ações principais disponíveis
erro técnico traduzido para ação
teste E2E ou componente quando aplicável
build frontend passando
staging validado
memória local atualizada sem commit
```

---

# 24. Cadastros externos necessários

A equipe deve preparar telas, variáveis, campos e fluxos para estes serviços. As credenciais reais devem ser criadas pelo responsável do negócio.

## 24.1 SERPRO / Integra Contador

Necessário para automações fiscais ligadas à Receita Federal/e-CAC.

Requisitos esperados:

```txt
conta na Loja SERPRO
contratação do Integra Contador
CNPJ responsável
certificado digital e-CNPJ
credenciais de API
procurações digitais dos clientes quando necessário
ambiente de homologação/produção, quando aplicável
```

Variáveis prováveis:

```env
SERPRO_CLIENT_ID=
SERPRO_CLIENT_SECRET=
SERPRO_BASE_URL=
SERPRO_CERTIFICATE_ID=
```

## 24.2 Portal Nacional NFS-e

Necessário para emissão/gestão de NFS-e quando usar o padrão nacional.

Requisitos esperados:

```txt
acesso ao Portal de Gestão NFS-e
cadastro do emissor
certificado digital ou gov.br quando aplicável
configuração fiscal do prestador
código de serviço municipal/nacional
ambiente restrito/testes, quando disponível
```

Variáveis prováveis:

```env
NFSE_PROVIDER=
NFSE_NACIONAL_BASE_URL=
NFSE_ENVIRONMENT=
```

## 24.3 Certificado digital

Necessário para NFS-e, e-CAC e Integra Contador.

Itens:

```txt
e-CNPJ A1 para automação server-side
e-CNPJ/e-CPF A3 para operação manual/híbrida
política de armazenamento
senha de certificado em cofre seguro
responsável jurídico pela autorização
```

## 24.4 Asaas

Já existe integração de billing. Revisar para nota fiscal e webhooks.

Necessário:

```txt
conta Asaas
API key sandbox/prod
webhook token
eventos de cobrança
eventos de assinatura
eventos de nota fiscal, se usado
```

Variáveis:

```env
ASAAS_API_KEY=
ASAAS_WEBHOOK_TOKEN=
ASAAS_ENVIRONMENT=
```

## 24.5 Meta Developers / WhatsApp Business Platform

Necessário para WhatsApp oficial.

Requisitos:

```txt
Meta Business Manager
app Meta Developers
WhatsApp Business Account
número aprovado
templates aprovados
webhook configurado
token permanente ou system user token
verificação de empresa, se exigida
```

Variáveis:

```env
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_VERIFY_TOKEN=
WHATSAPP_APP_SECRET=
```

## 24.6 Supabase

Necessário:

```txt
projeto produção
projeto staging
buckets privados
RLS revisada
service role apenas backend
anon key apenas frontend se necessário
backups
política de retenção
```

Variáveis:

```env
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
```

## 24.7 Fly.io

Necessário:

```txt
app produção
app staging
secrets por ambiente
readiness check
logs
escala mínima
região
```

## 24.8 Vercel

Necessário:

```txt
projeto produção
preview deployments
env vars por ambiente
domínios finais
bloqueio de previews sensíveis, se necessário
```

## 24.9 Sentry

Necessário:

```txt
projeto backend
projeto frontend
DSN por ambiente
PII desativado por padrão
release tracking
alertas 5xx
alertas frontend
```

## 24.10 OpenAI ou provider LLM

Necessário:

```txt
API key
limites por plano
mascaramento de dados
logs sem PII
fallback quando indisponível
```

## 24.11 E-mail transacional

Opções:

```txt
Resend
SendGrid
Amazon SES
Postmark
```

Variáveis:

```env
EMAIL_PROVIDER=
EMAIL_API_KEY=
EMAIL_FROM=
```

## 24.12 Antivírus / segurança de arquivos

Opções:

```txt
ClamAV próprio
serviço externo de malware scan
pipeline assíncrono por fila
```

## 24.13 Domínio e DNS

Necessário:

```txt
fiscwise.com.br
app.fiscwise.com.br
api.fiscwise.com.br
staging.fiscwise.com.br
SPF
DKIM
DMARC
CNAME Vercel
DNS Fly/API
```

---

# 25. Resultado esperado

Ao final deste plano, o FiscWise deve operar como:

```txt
central diária do contador
emissor de NFS-e
central Receita/e-CAC
gestor de procurações
gestor de certificados
gerador/controlador de guias
esteira de fechamento mensal
portal de documentos e comprovantes
base de auditoria fiscal
sistema pronto para escalar para escritórios maiores
```

A interface deve vender operação real. Beleza visual é consequência, não proposta central.
