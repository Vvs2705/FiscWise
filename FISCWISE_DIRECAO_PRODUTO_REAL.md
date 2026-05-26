# FiscWise — Direção de Produto Real, Limpeza do Repositório e Execução Agressiva

**Status:** documento de comando para evolução do FiscWise  
**Objetivo:** transformar o FiscWise em um sistema fiscal/contábil competitivo, operacional e vendável  
**Postura:** produto real, segurança fechada, funcionalidades que resolvem dor, sem roadmap cosmético  
**Público inicial:** contadores autônomos  
**Direção futura:** escritórios pequenos, médios e grandes, BPO financeiro/contábil e operações fiscais com alto volume  

---

## 1. Decisão estratégica

O FiscWise não será apenas um organizador bonito de clientes, documentos, prazos e IA.

O mercado já está cheio de SaaS com dashboard bonito, assistente de IA, checklist, kanban, automação rasa e promessa genérica. Isso não vende por muito tempo. O FiscWise precisa ser uma ferramenta que entra na rotina fiscal real, reduz trabalho manual e substitui planilhas, pastas, portais isolados, controles paralelos e retrabalho.

A nova direção é:

> **FiscWise será um sistema operacional fiscal e contábil para contadores, começando por autônomos e evoluindo para operações maiores.**

A métrica não é “ficou bonito”.  
A métrica é:

- O contador consegue emitir nota?
- O contador consegue consultar dados fiscais?
- O contador consegue controlar procurações?
- O contador consegue acompanhar obrigações reais?
- O contador consegue cobrar, emitir, armazenar e comprovar?
- O contador consegue atender mais clientes com menos caos?
- O sistema reduz risco fiscal?
- O sistema gera dinheiro ou economiza horas todos os meses?

Se a resposta for não, a funcionalidade é secundária.

---

## 2. Posicionamento agressivo

### 2.1 Posicionamento principal

> **FiscWise é a central fiscal do contador moderno: clientes, documentos, obrigações, e-CAC, notas fiscais, cobranças, guias, certificados e inteligência operacional em um único sistema.**

### 2.2 O que o FiscWise precisa deixar de ser

- Um dashboard bonito.
- Um organizador de prazos.
- Um gerenciador de documentos.
- Um CRUD de clientes.
- Um SaaS com IA decorativa.
- Um projeto que parece estar sempre em planejamento.

### 2.3 O que o FiscWise deve se tornar

- Um produto fiscal operacional.
- Um hub de execução contábil.
- Um sistema que emite, consulta, acompanha, alerta, armazena e comprova.
- Uma central de trabalho diário para o contador.
- Uma plataforma preparada para escalar de autônomo para escritório e depois para operação de médio/grande porte.

---

## 3. Limpeza obrigatória do repositório

O repositório precisa parecer produto, não caderno de obra.

Documentos de plano, progresso, passo a passo antigo, status de implementação, ideias soltas e arquivos temporários devem sair do repositório. O histórico do que foi feito já existe no Git. O repositório deve mostrar código, documentação essencial e segurança.

### 3.1 Manter no repositório

Estrutura desejada:

```txt
FiscWise/
  backend/
  frontend/
  docs/
    SECURITY_CORRECTIONS.md
  .github/
  .dockerignore
  .gitignore
  docker-compose.yml
  fly.toml
  fly.staging.toml
  vercel.json
  README.md
```

### 3.2 Remover da raiz

Remover arquivos de plano, progresso, status e rascunhos semelhantes a:

```txt
BACKEND_FEATURES_IMPLEMENTATION_PLAN.md
CLIENT_SECRETS_TEMPLATE.md
DEPLOYMENT_SUMMARY.md
FEATURE_IMPLEMENTATION_STATUS.md
LOGIN_LAYOUT_CORRECOES.md
PRODUCTION_STATUS.md
PROGRESSO.md
ROADMAP.md
Evolução seguinte.md
FiscWise_Analise_Pre_Lancamento.md
FISCWISE_REDESIGN_MASTERPLAN.md
```

Remover também pastas de ideias ou planejamento solto:

```txt
ideia e melhorias/
rascunhos/
planos/
roadmaps/
progresso/
```

### 3.3 Limpar a pasta docs

Manter somente:

```txt
docs/SECURITY_CORRECTIONS.md
```

Tudo que for auditoria, plano de correção, staging, validação, progresso ou roadmap deve ser consolidado nesse arquivo ou removido.

Remover arquivos como:

```txt
docs/AUDITORIA_COMPLETA_FISCWISE.md
docs/PLANO_CORRECOES_PRIORIZADO.md
docs/STAGING_AND_OBSERVABILITY.md
docs/VALIDACAO_ONLINE_FISCWISE.md
```

### 3.4 README

O README deve ser enxuto, comercial e técnico.

Deve conter:

- O que é o FiscWise.
- Para quem é.
- Principais módulos.
- Stack.
- Como rodar localmente.
- Variáveis de ambiente via `.env.example`.
- Como rodar testes.
- Como fazer deploy.
- Link para segurança: `docs/SECURITY_CORRECTIONS.md`.

Não deve conter:

- Histórico de fases.
- Lista longa de commits.
- Promessas antigas.
- Planos internos.
- Links de documentação pública de produção.
- Trechos que pareçam “produto ainda em construção”.

### 3.5 Comando sugerido de limpeza

```bash
git checkout -b chore/repository-cleanup

mkdir -p docs

# Consolidar manualmente o conteúdo útil em:
# docs/SECURITY_CORRECTIONS.md

rm -f BACKEND_FEATURES_IMPLEMENTATION_PLAN.md
rm -f CLIENT_SECRETS_TEMPLATE.md
rm -f DEPLOYMENT_SUMMARY.md
rm -f FEATURE_IMPLEMENTATION_STATUS.md
rm -f LOGIN_LAYOUT_CORRECOES.md
rm -f PRODUCTION_STATUS.md
rm -f PROGRESSO.md
rm -f ROADMAP.md
rm -f "Evolução seguinte.md"
rm -f FiscWise_Analise_Pre_Lancamento.md
rm -f FISCWISE_REDESIGN_MASTERPLAN.md

rm -rf "ideia e melhorias"
rm -rf rascunhos
rm -rf planos
rm -rf roadmaps
rm -rf progresso

rm -f docs/AUDITORIA_COMPLETA_FISCWISE.md
rm -f docs/PLANO_CORRECOES_PRIORIZADO.md
rm -f docs/STAGING_AND_OBSERVABILITY.md
rm -f docs/VALIDACAO_ONLINE_FISCWISE.md

git status
git add .
git commit -m "chore: limpa documentacao obsoleta e consolida seguranca"
```

---

## 4. Arquivo de memória local obrigatório

O projeto precisa continuar tendo memória de execução, mas essa memória não deve subir para o GitHub.

A memória é útil para registrar:

- O que foi feito.
- O que quebrou.
- O que foi corrigido.
- Quais decisões foram tomadas.
- Quais comandos foram usados.
- Quais variáveis mudaram.
- Quais pendências ficaram.
- O que precisa ser testado depois.

Mas isso não é documentação pública do produto. É diário operacional local.

### 4.1 Nome recomendado

Criar localmente:

```txt
.local/FISCWISE_MEMORIA_LOCAL.md
```

ou:

```txt
FISCWISE_MEMORIA_LOCAL.md
```

### 4.2 Regra absoluta

> **Esse arquivo jamais deve subir para o repositório.**

Ele é memória local de execução. Não é documentação oficial. Não é roadmap público. Não é material de produto. Não é para GitHub.

### 4.3 Atualizar `.gitignore`

Adicionar ao `.gitignore`:

```gitignore
# Memória local de execução — nunca versionar
.local/
FISCWISE_MEMORIA_LOCAL.md
MEMORIA_LOCAL.md
*_MEMORIA_LOCAL.md

# Rascunhos locais
rascunhos-locais/
.local-notes/
```

### 4.4 Template do arquivo local

Criar localmente:

```md
# FiscWise — Memória Local de Execução

> Este arquivo é local. Nunca subir para o GitHub.

## Data
AAAA-MM-DD

## Objetivo do ciclo
Descrever objetivo real do ciclo.

## O que foi feito
- Item 1
- Item 2

## Arquivos alterados
- backend/...
- frontend/...

## Migrations
- Nome da migration
- O que muda
- Como testar rollback, se aplicável

## Variáveis de ambiente alteradas
- NOME_DA_VARIAVEL
- Ambiente afetado: local/staging/prod

## Testes executados
```bash
pytest
npm run build
npm run lint
```

## Resultado dos testes
- Passou
- Falhou
- Corrigido

## Bugs encontrados
- Bug
- Causa
- Correção

## Pendências reais
- Pendência
- Impacto
- Próximo responsável

## Decisões tomadas
- Decisão
- Motivo

## Próximo ciclo
- Ação 1
- Ação 2
```

---

## 5. Segurança: fechar as portas antes de acelerar

A postura agora é simples:

> Segurança não é freio. Segurança é blindagem para vender.

Um sistema fiscal sem segurança forte não escala. Escritórios e empresas maiores não compram produto que vaza documento, expõe API, permite brute force ou não prova isolamento por tenant.

### 5.1 Correções obrigatórias

Estas correções devem ser tratadas como portas abertas:

1. Desabilitar `/docs`, `/redoc` e `/openapi.json` em produção.
2. Remover `localhost` do CORS de produção.
3. Parar de logar qualquer pedaço de `DATABASE_URL`.
4. Produção e staging devem falhar no startup sem secrets obrigatórios.
5. Criar `/live` e `/ready`.
6. Fly.io deve usar `/ready` para readiness.
7. Redis obrigatório em produção se houver rate limit.
8. Rate limit estrito em login, 2FA, registro, portal, upload, billing webhook e admin.
9. Storage privado para documentos.
10. URLs assinadas com TTL curto.
11. MIME sniffing real.
12. Limite de tamanho por plano e por endpoint.
13. Antivírus/scan assíncrono para upload.
14. Testes cross-tenant em todos os fluxos sensíveis.
15. Admin token estático deve ser substituído por usuário admin real, MFA, RBAC, IP allowlist e auditoria.
16. Docker rodando como usuário não-root.
17. Secret scanning no CI.
18. Dependency scan no CI.
19. SAST básico no CI.
20. Backups e restore testado.
21. Logs estruturados sem PII sensível.
22. Redaction de secrets no Sentry.
23. Auditoria obrigatória para operações fiscais, documentos, certificados, notas e billing.

### 5.2 Critério de aceite de segurança

Não basta “implementar”.

Cada item deve ter:

- teste automatizado quando aplicável;
- log de auditoria quando envolver ação sensível;
- validação em staging;
- evidência registrada no arquivo local de memória;
- atualização em `docs/SECURITY_CORRECTIONS.md` somente quando for uma correção oficial e permanente.

---

## 6. Funcionalidades que realmente vendem

A prioridade não é inventar mais tela. É atacar dor real.

### 6.1 Camadas do produto competitivo

O FiscWise precisa cobrir estas camadas:

```txt
1. Base de clientes e documentos
2. Certificados e procurações
3. e-CAC e dados fiscais
4. Obrigações e calendário fiscal real
5. Emissão fiscal: NFS-e, depois NF-e/NFC-e/CT-e quando fizer sentido
6. Cobrança, recebíveis, Pix, boleto e inadimplência
7. Guias, impostos e comprovantes
8. Portal do cliente
9. Comunicação: WhatsApp, e-mail e notificações
10. BI fiscal e operacional
11. Auditoria, compliance e segurança
12. API pública e integrações
```

---

## 7. Módulo Notas Fiscais

Notas fiscais são centrais. Não são extra.

### 7.1 Começar por NFS-e

A primeira entrega de emissão deve ser NFS-e porque o público inicial é contador autônomo e prestadores de serviços.

Além disso, a NFS-e nacional já possui portal, ambiente nacional e documentação técnica. A regra publicada pelo Portal Nacional da NFS-e informa que empresas optantes pelo Simples Nacional deverão emitir NFS-e pelo Emissor Nacional a partir de 01/09/2026, e que a emissão pode ocorrer por portal web ou por software ERP integrado via API com a SEFIN Nacional.

### 7.2 Módulo no menu

Adicionar:

```txt
Notas Fiscais
```

Subáreas:

```txt
Visão geral
Emitir NFS-e
Rascunhos
Emitidas
Rejeitadas
Canceladas
Clientes emissores
Configurações fiscais
```

### 7.3 Fluxo 1 — contador emitindo nota dos próprios honorários

Este fluxo vende imediatamente.

```txt
Cliente → Honorário mensal/avulso → Cobrança → NFS-e → PDF/XML → Envio ao cliente → Recebível → Comprovante
```

Funcionalidades:

- emissão de NFS-e para honorários mensais;
- emissão avulsa;
- recorrência;
- rascunho automático a partir da cobrança;
- vínculo com cliente;
- vínculo com competência;
- envio por e-mail/WhatsApp;
- armazenamento seguro do XML/PDF;
- status financeiro vinculado;
- cancelamento/substituição quando permitido;
- histórico e auditoria.

### 7.4 Fluxo 2 — contador emitindo NFS-e para clientes

Este fluxo torna o produto mais forte.

```txt
Cliente prestador → Perfil fiscal → Procuração/certificado → Serviço → NFS-e → XML/PDF → Competência → Obrigações
```

Funcionalidades:

- cadastro fiscal do cliente emissor;
- município;
- inscrição municipal;
- regime tributário;
- código de serviço;
- retenções;
- natureza da operação;
- ISS;
- tomador;
- intermediário quando aplicável;
- configuração por cliente;
- lote/individual;
- consulta de status;
- reemissão de PDF;
- histórico de rejeições;
- auditoria por emissão.

### 7.5 Fluxo 3 — importação e conciliação de notas

Mesmo antes de emitir tudo, o sistema deve importar e organizar.

Funcionalidades:

- upload de XML;
- leitura de XML;
- classificação por cliente;
- competência;
- valor;
- tomador/prestador;
- status;
- vínculo com financeiro;
- conciliação com recebíveis;
- alerta de nota sem cobrança;
- alerta de cobrança sem nota;
- alerta de nota emitida fora da competência.

### 7.6 Arquitetura recomendada

Criar domínio próprio:

```txt
backend/app/domain/invoices/
  models.py
  schemas.py
  service.py
  repository.py
  validators.py
  events.py
  providers/
    base.py
    nfse_nacional.py
    municipal.py
    mock.py
```

Frontend:

```txt
frontend/src/features/invoices/
  pages/
  components/
  hooks/
  services/
  schemas/
```

### 7.7 Tabelas essenciais

```sql
invoice_issuers
invoice_service_profiles
invoices
invoice_events
invoice_provider_credentials
invoice_artifacts
invoice_taxes
invoice_rejections
invoice_customer_profiles
```

### 7.8 Status de nota

```txt
draft
validating
queued
processing
issued
rejected
cancel_requested
cancelled
replaced
failed
```

### 7.9 Critérios de aceite

Uma NFS-e só é considerada pronta quando o sistema conseguir:

- criar rascunho;
- validar dados mínimos;
- enviar para provedor/API;
- receber status;
- armazenar XML;
- armazenar PDF/DANFSe quando disponível;
- registrar auditoria;
- vincular com cobrança/recebível;
- enviar para cliente;
- exibir rejeição com motivo;
- permitir correção;
- impedir acesso cross-tenant.

---

## 8. Módulo e-CAC / Receita Federal

Este módulo é um dos maiores saltos competitivos.

O contador vive entrando em portal, consultando pendência, situação fiscal, procuração, certidão, declarações, débitos e guias. O FiscWise precisa virar a tela onde isso aparece.

### 8.1 Direção

Criar:

```txt
Central e-CAC
```

Subáreas:

```txt
Situação Fiscal
Procurações
Certidões
DCTFWeb
Caixa Postal
Pendências
Débitos
Pagamentos
Relatórios por cliente
```

### 8.2 Integração oficial

Usar integração oficial via Integra Contador/Serpro quando aplicável.

A Receita Federal e o Serpro disponibilizam o Integra Contador para automatizar processos contábeis e fiscais. Serviços que exigem procuração precisam de permissão via sistema de procurações eletrônicas do e-CAC. A autenticação envolve certificado digital e autorização do titular/procurador, conforme documentação oficial.

Regra do produto:

> Não construir automação frágil de navegador como base do produto. A integração deve priorizar API oficial, certificado, procuração e trilha de auditoria.

### 8.3 Cadastro de procurações

Criar módulo:

```txt
Procurações
```

Campos:

- cliente;
- outorgante;
- procurador;
- tipo;
- serviços autorizados;
- data de início;
- validade;
- status;
- certificado vinculado;
- fonte de consulta;
- última verificação;
- alertas de vencimento.

Funcionalidades:

- importar procurações;
- consultar status;
- alertar vencimento;
- mostrar clientes sem procuração;
- bloquear rotinas que exigem procuração;
- checklist para regularização.

### 8.4 Situação Fiscal

Funcionalidades:

- consulta por cliente;
- status geral;
- pendências;
- débitos;
- certidão;
- alertas;
- histórico;
- score de risco fiscal;
- prioridade automática no cockpit.

### 8.5 Caixa Postal / mensagens

Funcionalidades:

- capturar mensagens oficiais quando permitido;
- classificar por cliente;
- marcar como lida;
- gerar tarefa;
- alertar urgência;
- vincular a obrigação.

### 8.6 Critério de aceite

A Central e-CAC só vale se gerar ação.

Não basta mostrar dado. Precisa transformar dado em trabalho:

```txt
Pendência encontrada → alerta → tarefa → responsável → prazo → resolução → evidência
```

---

## 9. Certificados digitais

Certificado é infraestrutura do contador.

### 9.1 Módulo atual deve evoluir para cofre operacional

Funcionalidades:

- cadastro de A1/A3;
- vencimento;
- entidade vinculada;
- cliente vinculado;
- tipo;
- status;
- alertas;
- uso autorizado;
- trilha de uso;
- senha nunca exposta;
- armazenamento criptografado;
- rotação;
- expiração;
- bloqueio por plano/perfil.

### 9.2 Certificado como requisito de módulos

Certificado deve se conectar com:

- e-CAC;
- NFS-e;
- NF-e;
- EFD-Reinf;
- DCTFWeb quando aplicável;
- procurações;
- assinatura de XML;
- integrações oficiais.

---

## 10. Obrigações fiscais reais

O motor de obrigações não pode ser apenas calendário.

Ele precisa virar motor fiscal operacional.

### 10.1 Evoluir regras

Adicionar regras para:

- DAS;
- DEFIS;
- DCTFWeb;
- EFD-Reinf;
- eSocial;
- EFD-Contribuições;
- EFD-ICMS/IPI;
- ECD;
- ECF;
- PGDAS-D;
- ISS municipal;
- parcelamentos;
- certidões;
- obrigações estaduais por UF;
- obrigações municipais por cidade;
- rotinas de fechamento mensal;
- obrigações por CNAE;
- obrigações por regime tributário.

### 10.2 Regras com contexto

Cada obrigação deve considerar:

- regime tributário;
- município;
- UF;
- CNAE;
- inscrição estadual;
- inscrição municipal;
- funcionários;
- faturamento;
- tipo de atividade;
- retenções;
- certificado;
- procuração;
- perfil do cliente.

### 10.3 Saída do motor

O motor deve gerar:

- obrigação;
- checklist;
- documentos necessários;
- responsável;
- vencimento;
- prioridade;
- alerta;
- status;
- evidência exigida;
- consequência se atrasar.

---

## 11. Guias, impostos e comprovantes

O produto precisa controlar mais do que tarefa.

### 11.1 Módulo Guias

Subáreas:

```txt
DAS
DARF
GPS
ISS
Parcelamentos
Comprovantes
Pendências
```

Funcionalidades:

- registrar guia;
- importar guia;
- anexar PDF;
- vencimento;
- valor;
- competência;
- status de pagamento;
- envio ao cliente;
- comprovante;
- cobrança;
- alerta de atraso;
- conciliação com financeiro;
- histórico por cliente;
- indicador “guia enviada, mas sem comprovante”.

### 11.2 Dor real

Contador sofre com:

- cliente que não paga guia;
- cliente que não envia comprovante;
- prazo perdido;
- mensagem perdida no WhatsApp;
- guia enviada duas vezes;
- comprovante salvo em pasta errada.

O FiscWise deve atacar isso sem pedir desculpa.

---

## 12. Financeiro forte

O financeiro precisa deixar de ser acessório.

### 12.1 Para o contador

- honorários mensais;
- avulsos;
- inadimplência;
- recorrência;
- reajuste anual;
- Pix;
- boleto;
- link de pagamento;
- conciliação;
- nota fiscal do honorário;
- cobrança automática;
- régua de cobrança;
- bloqueio de serviço por inadimplência;
- relatório de receita por cliente;
- margem por carteira.

### 12.2 Para os clientes do contador

- contas a receber;
- pagamentos de guias;
- comprovantes;
- notas emitidas;
- obrigações financeiras fiscais;
- integração futura com bancos/Open Finance.

### 12.3 Integração fiscal-financeira

Fluxo obrigatório:

```txt
Honorário → Cobrança → NFS-e → Recebível → Pagamento → Baixa → Histórico
```

---

## 13. Portal do cliente que resolve, não enfeita

Portal precisa ser instrumento de coleta e execução.

### 13.1 Funcionalidades

- envio de documentos;
- checklist mensal;
- comprovantes;
- guias;
- notas fiscais;
- mensagens;
- solicitações;
- pendências;
- aceite de termos;
- assinatura de autorização;
- histórico;
- status de atendimento;
- notificações.

### 13.2 Cliente entra e vê

```txt
O que preciso enviar?
O que preciso pagar?
O que está atrasado?
O que meu contador já resolveu?
Quais documentos estão disponíveis?
Quais notas foram emitidas?
```

---

## 14. WhatsApp e comunicação

WhatsApp não é enfeite. É onde o contador trabalha.

### 14.1 O FiscWise precisa capturar a operação

Funcionalidades:

- mensagens por cliente;
- templates;
- lembretes;
- cobrança de documentos;
- cobrança de guias;
- envio de nota;
- envio de comprovante;
- envio de link do portal;
- histórico por cliente;
- conversas ligadas a tarefas;
- transformação de mensagem em pendência;
- resposta rápida;
- trilha de envio e leitura quando disponível.

### 14.2 Régua de cobrança

Criar regras:

```txt
D-7: lembrar documento
D-3: lembrar documento
D0: vencimento hoje
D+1: atraso leve
D+3: atraso crítico
D+7: escalar cobrança
```

---

## 15. BI operacional e fiscal

Dashboard bonito não basta. Cockpit precisa mandar na operação.

### 15.1 Indicadores obrigatórios

- clientes em risco;
- obrigações atrasadas;
- documentos pendentes;
- guias sem comprovante;
- notas rejeitadas;
- notas a emitir;
- clientes sem procuração;
- certificados vencendo;
- inadimplência;
- faturamento por cliente;
- esforço por cliente;
- tempo médio de resolução;
- pendências por canal;
- gargalos por tipo de obrigação.

### 15.2 Score de carteira

Criar score real:

```txt
Score = obrigações + documentos + guias + notas + procurações + certificados + inadimplência
```

Classificação:

```txt
90-100: saudável
75-89: atenção
50-74: risco
0-49: crítico
```

---

## 16. IA útil, não decorativa

IA precisa trabalhar para o contador.

### 16.1 Usos fortes

- classificar documentos;
- extrair vencimento/valor/competência;
- resumir situação de cliente;
- sugerir pendências;
- explicar rejeição de nota fiscal;
- transformar mensagem em tarefa;
- gerar checklist fiscal;
- identificar risco de atraso;
- responder dúvidas com base de conhecimento fiscal;
- sugerir priorização diária.

### 16.2 Regras

- mascarar dados sensíveis quando possível;
- não enviar certificado, segredo ou senha;
- registrar uso;
- quota por plano;
- fallback sem IA;
- explicabilidade mínima;
- sempre permitir revisão humana.

---

## 17. API pública e integrações

Produto sério precisa se integrar.

### 17.1 API pública

Manter e evoluir:

- API keys por tenant;
- escopos;
- webhooks;
- logs de entrega;
- retry;
- assinatura HMAC;
- rate limit por chave;
- documentação privada para clientes autorizados.

### 17.2 Webhooks obrigatórios

Eventos:

```txt
client.created
document.uploaded
obligation.created
obligation.overdue
invoice.issued
invoice.rejected
invoice.cancelled
payment.received
payment.overdue
certificate.expiring
ecac.pending_issue_detected
```

---

## 18. Caminho para médio e grande porte

Começamos com contador autônomo, mas a arquitetura não pode nascer pequena.

### 18.1 Preparar desde já

- múltiplas unidades;
- múltiplos usuários;
- times;
- carteira por responsável;
- permissões granulares;
- aprovação dupla;
- auditoria completa;
- trilha de alteração;
- SLA interno;
- filas;
- importação em massa;
- exportação;
- API;
- webhooks;
- integrações;
- ambientes separados;
- observabilidade;
- relatórios gerenciais;
- controle por filial;
- centros de custo;
- LGPD avançada.

### 18.2 Recursos enterprise futuros

- SSO/SAML;
- SCIM;
- IP allowlist;
- logs exportáveis;
- retenção configurável;
- aprovação de operações críticas;
- segregação por times;
- planos customizados;
- SLA contratual;
- suporte prioritário;
- ambientes dedicados;
- BI avançado;
- integração com ERPs;
- integração contábil externa.

---

## 19. Cronograma agressivo por ondas

Não chamar de MVP.  
Chamar de ondas de entrega do produto real.

### Onda 0 — Repositório limpo e portas fechadas

Objetivo: deixar a casa limpa e segura para acelerar.

Entregas:

- limpeza do repositório;
- `docs/SECURITY_CORRECTIONS.md` consolidado;
- memória local fora do Git;
- README refeito;
- docs públicas desativadas em produção;
- CORS corrigido;
- secrets fail-closed;
- logs sem segredo;
- `/live` e `/ready`;
- rate limit sério;
- storage privado;
- signed URLs;
- testes cross-tenant;
- Docker hardening;
- CI com secret/dependency scan.

### Onda 1 — Notas fiscais e financeiro integrado

Objetivo: vender com funcionalidade forte.

Entregas:

- domínio `invoices`;
- cadastro fiscal do emissor;
- NFS-e de honorários;
- emissão avulsa;
- emissão recorrente;
- XML/PDF;
- vínculo com cobrança;
- envio ao cliente;
- rejeições;
- auditoria;
- tela de Notas Fiscais;
- notas por cliente;
- conciliação nota/cobrança.

### Onda 2 — e-CAC, procurações e situação fiscal

Objetivo: tirar o contador do portal manual.

Entregas:

- Central e-CAC;
- cadastro de procurações;
- status de procuração;
- clientes sem procuração;
- situação fiscal;
- certidões;
- pendências;
- débitos;
- caixa postal quando disponível;
- tarefas automáticas a partir de pendências.

### Onda 3 — Motor fiscal robusto

Objetivo: transformar o FiscWise em agenda fiscal inteligente.

Entregas:

- obrigações por regime/CNAE/UF/município;
- checklist mensal inteligente;
- documentos exigidos por obrigação;
- guias;
- comprovantes;
- alertas;
- score de carteira;
- cockpit operacional real.

### Onda 4 — Portal do cliente e WhatsApp operacional

Objetivo: reduzir caos de comunicação.

Entregas:

- portal completo;
- checklist mensal;
- envio de documentos;
- comprovantes;
- notas fiscais;
- guias;
- régua WhatsApp/e-mail;
- templates;
- histórico por cliente;
- mensagem vira tarefa.

### Onda 5 — Escala, API e empresas maiores

Objetivo: preparar expansão.

Entregas:

- times;
- permissões granulares;
- aprovação dupla;
- API pública avançada;
- webhooks;
- BI;
- integrações;
- importação/exportação;
- SSO futuro;
- logs enterprise;
- relatórios de produtividade;
- automação multi-carteira.

---

## 20. Matriz do que vende vs. o que é cosmético

### 20.1 Vende

- emitir NFS-e;
- consultar e-CAC;
- controlar procurações;
- gerenciar certificados;
- controlar guias;
- cobrar cliente;
- enviar nota;
- reduzir atraso;
- portal do cliente;
- WhatsApp integrado;
- motor de obrigações real;
- alertas de pendência fiscal;
- relatórios por cliente;
- trilha de auditoria;
- segurança forte;
- API e integrações.

### 20.2 Não sustenta venda sozinho

- dashboard bonito;
- animação;
- IA genérica;
- cards;
- dark mode;
- CRUD de cliente;
- upload simples;
- calendário manual;
- gráficos decorativos;
- checklist manual.

Essas coisas ajudam, mas não são o núcleo competitivo.

---

## 21. Arquitetura de produto desejada

O FiscWise deve ser organizado por domínios, não por arquivos gigantes.

```txt
backend/app/domain/
  clients/
  documents/
  obligations/
  invoices/
  ecac/
  certificates/
  billing/
  payments/
  notifications/
  portal/
  audit/
  ai/
  integrations/
  webhooks/
```

Cada domínio deve ter:

```txt
models.py
schemas.py
repository.py
service.py
permissions.py
events.py
tests/
```

Rotas devem ser finas.  
Regra de negócio deve ficar em service.  
Banco deve ficar em repository.  
Eventos devem permitir automações.

---

## 22. Eventos internos

Tudo que importa deve gerar evento.

Exemplos:

```txt
document.uploaded
document.classified
obligation.generated
obligation.overdue
invoice.draft_created
invoice.issued
invoice.rejected
invoice.cancelled
payment.created
payment.overdue
certificate.expiring
ecac.situation_changed
proxy.expiring
client.risk_score_changed
```

Eventos alimentam:

- notificações;
- auditoria;
- webhooks;
- BI;
- cockpit;
- IA;
- histórico.

---

## 23. Qualidade de entrega

Toda funcionalidade forte precisa sair completa.

Definição de pronto:

- migration;
- models;
- schemas;
- service;
- repository;
- endpoint;
- permissões;
- audit log;
- RLS;
- teste unitário;
- teste de API;
- teste cross-tenant;
- frontend;
- estado vazio;
- estado de erro;
- loading;
- log estruturado;
- documentação mínima no README se for instalação/configuração;
- registro na memória local.

---

## 24. Mensagem para os devs

Este projeto não está mais em fase de enfeite.

A partir deste documento:

- não subir plano antigo;
- não subir progresso local;
- não criar tela sem resolver dor;
- não criar endpoint sem permissão;
- não criar integração sem auditoria;
- não criar upload sem segurança;
- não criar emissão fiscal sem XML/PDF/status/rejeição;
- não criar automação que não gere ação;
- não deixar rota crítica sem teste cross-tenant;
- não empurrar segredo para log;
- não usar IA como desculpa para falta de produto.

A ordem é:

```txt
Limpar.
Blindar.
Emitir.
Consultar.
Cobrar.
Comprovar.
Automatizar.
Escalar.
```

---

## 25. Fontes oficiais e referências consultadas

Estas fontes justificam tecnicamente a direção de produto, principalmente NFS-e, e-CAC/Integra Contador, SPED e emissão fiscal:

- Portal Nacional da NFS-e: https://www.gov.br/nfse/pt-br
- Documentação técnica NFS-e: https://www.gov.br/nfse/pt-br/biblioteca/documentacao-tecnica
- APIs NFS-e produção restrita e produção: https://www.gov.br/nfse/pt-br/biblioteca/documentacao-tecnica/apis-prod-restrita-e-producao
- Obrigatoriedade NFS-e Simples Nacional a partir de 01/09/2026: https://www.gov.br/nfse/pt-br/noticias/nfs-e-e-simples-nacional-obrigatoriedade-de-emissao-atraves-do-emissor-nacional
- Integra Contador/Serpro: https://loja.serpro.gov.br/integra-contador/product/integracontador
- Documentação API Integra Contador: https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/
- Procurações no Integra Contador: https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/solucoes/integra-procuracoes/procuracoes/
- Autentica-Procurador: https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/solucoes/integra-contador-gerenciador/autenticaprocurador/
- EFD-Reinf: https://www.gov.br/pt-br/servicos/efd-reinf
- DCTFWeb: https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/declaracoes-e-demonstrativos/DCTFWeb
- Portal Nacional NF-e: https://www.nfe.fazenda.gov.br/
- Conta Azul — emissão fiscal integrada a financeiro: https://contaazul.com/
- Nibo — financeiro, NFS-e, boletos e cobranças: https://www.nibo.com.br/

---

## 26. Frase final de direção

O FiscWise não vai competir pedindo licença.

O FiscWise vai competir resolvendo o trabalho real do contador:

```txt
dados fiscais,
notas,
guias,
documentos,
cobranças,
certificados,
procurações,
obrigações,
evidências,
clientes
e operação diária.
```

Produto bonito atrai atenção.  
Produto que emite, consulta, cobra, alerta e comprova ganha mercado.
