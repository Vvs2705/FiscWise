# FiscWise — Equipe Claude
## Fundação técnica, segurança, backend fiscal core e integrações oficiais

**Objetivo:** executar a base técnica que transforma o FiscWise em um sistema fiscal operacional real, não apenas um organizador contábil com interface bonita.

**Escopo da equipe:** repositório, segurança, infraestrutura, backend, banco, storage, filas, workers, RLS, testes, NFS-e, e-CAC/Integra Contador, certificados, procurações, guias, caixa postal fiscal, fechamento mensal e dossiê fiscal.

**Regra:** nada de mentalidade de MVP. Todo módulo nasce com multi-tenant, RBAC, auditoria, testes, logs seguros, idempotência, observabilidade e caminho de escala.

---

# 1. Limpeza técnica do repositório

## 1.1 Remover da raiz

Excluir documentos de plano, progresso, rascunho e legado:

```txt
BACKEND_FEATURES_IMPLEMENTATION_PLAN.md
CLIENT_SECRETS_TEMPLATE.md
DEPLOYMENT_SUMMARY.md
FEATURE_IMPLEMENTATION_STATUS.md
LOGIN_LAYOUT_CORRECOES.md
PRODUCTION_STATUS.md
PROGRESSO.md
ROADMAP.md
FISCWISE_DIRECAO_PRODUTO_REAL.md
Evolução seguinte.md
FiscWise_Analise_Pre_Lancamento.md
FISCWISE_REDESIGN_MASTERPLAN.md
```

Excluir diretórios locais/rascunhos:

```txt
ideia e melhorias/
rascunhos/
rascunhos-locais/
.local/
.local-notes/
```

## 1.2 Consolidar `docs/`

Manter somente:

```txt
docs/SECURITY_CORRECTIONS.md
```

Remover ou consolidar nele:

```txt
docs/AUDITORIA_COMPLETA_FISCWISE.md
docs/PLANO_CORRECOES_PRIORIZADO.md
docs/STAGING_AND_OBSERVABILITY.md
docs/VALIDACAO_ONLINE_FISCWISE.md
```

## 1.3 README

Reescrever o `README.md` como documentação de produto/código, removendo:

- histórico de commits;
- links de `/docs`, `/redoc` ou `/openapi.json` em produção;
- qualquer menção a ContaFlow;
- progresso antigo;
- roadmap antigo;
- instruções internas de deploy que devem ficar fora do README público.

Manter:

- visão objetiva do produto;
- stack;
- setup local;
- env vars via `.env.example`;
- testes;
- segurança resumida.

## 1.4 Comando sugerido

```bash
git checkout -b chore/repository-cleanup

mkdir -p docs

rm -f BACKEND_FEATURES_IMPLEMENTATION_PLAN.md
rm -f CLIENT_SECRETS_TEMPLATE.md
rm -f DEPLOYMENT_SUMMARY.md
rm -f FEATURE_IMPLEMENTATION_STATUS.md
rm -f LOGIN_LAYOUT_CORRECOES.md
rm -f PRODUCTION_STATUS.md
rm -f PROGRESSO.md
rm -f ROADMAP.md
rm -f FISCWISE_DIRECAO_PRODUTO_REAL.md
rm -f "Evolução seguinte.md"
rm -f FiscWise_Analise_Pre_Lancamento.md
rm -f FISCWISE_REDESIGN_MASTERPLAN.md

rm -rf "ideia e melhorias" rascunhos rascunhos-locais .local .local-notes

rm -f docs/AUDITORIA_COMPLETA_FISCWISE.md
rm -f docs/PLANO_CORRECOES_PRIORIZADO.md
rm -f docs/STAGING_AND_OBSERVABILITY.md
rm -f docs/VALIDACAO_ONLINE_FISCWISE.md

git status
```

---

# 2. Memória local de execução

Criar localmente na raiz:

```txt
FISCWISE_MEMORIA_LOCAL.md
```

Modelo:

```md
# FiscWise — Memória Local

## Última atualização
## Branch atual
## Concluído
## Em andamento
## Bloqueios
## Decisões técnicas
## Próximo bloco de execução
```

Regra absoluta:

```txt
NUNCA COMMITAR.
NUNCA SUBIR PARA O GITHUB.
NUNCA USAR COMO DOCUMENTAÇÃO OFICIAL.
```

Garantir no `.gitignore`:

```gitignore
FISCWISE_MEMORIA_LOCAL.md
MEMORIA_LOCAL.md
*_MEMORIA_LOCAL.md
PROGRESSO_*.md
.local/
.local-notes/
rascunhos-locais/
```

Validar:

```bash
git check-ignore -v FISCWISE_MEMORIA_LOCAL.md
```

---

# 3. Segurança de produção — fechamento obrigatório

## 3.1 FastAPI docs fora de produção

Arquivo:

```txt
backend/app/main.py
```

Implementar:

```python
is_prod = settings.ENVIRONMENT == "production"

app = FastAPI(
    title="FiscWise API",
    version=settings.APP_VERSION,
    docs_url=None if is_prod else "/docs",
    redoc_url=None if is_prod else "/redoc",
    openapi_url=None if is_prod else "/openapi.json",
    lifespan=lifespan,
)
```

A rota `/` em produção não deve expor `docs`, `redoc` ou `openapi`.

## 3.2 Secrets fail-closed

Arquivo:

```txt
backend/app/core/config.py
```

Em `production` e `staging`, levantar erro no startup se ausentes/fracos:

```txt
DATABASE_URL
JWT_SECRET_KEY
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
REDIS_URL
ASAAS_API_KEY, se billing ativo
ASAAS_WEBHOOK_TOKEN, se webhook ativo
SENTRY_DSN, se observabilidade obrigatória
SERPRO_CLIENT_ID, quando Integra Contador ativo
SERPRO_CLIENT_SECRET, quando Integra Contador ativo
NFSE_* quando emissão estiver ativa
```

Regras:

- `JWT_SECRET_KEY` mínimo 64 caracteres;
- proibir `dev`, `test`, `local`, `do_not_use`, `secret_key_2026`;
- `DATABASE_URL` não pode apontar para localhost em produção;
- Redis obrigatório se rate limit estiver ativo.

## 3.3 Remover logs de segredo

Remover qualquer log parcial ou total de:

```txt
DATABASE_URL
JWT_SECRET_KEY
REDIS_URL
SUPABASE_SERVICE_ROLE_KEY
ASAAS_API_KEY
OPENAI_API_KEY
SERPRO_CLIENT_SECRET
CERTIFICATE_PASSWORD
```

Permitido:

```python
logger.info("DATABASE_URL configured: %s", bool(settings.DATABASE_URL))
```

## 3.4 CORS por ambiente

Produção não pode conter:

```txt
localhost
127.0.0.1
contaflow
domínios temporários desnecessários
```

Exemplo:

```env
ALLOWED_ORIGINS=https://fiscwise.com.br,https://www.fiscwise.com.br,https://app.fiscwise.com.br
```

Adicionar validação que derruba startup se origem inválida aparecer em produção.

## 3.5 Health check real

Criar:

```txt
GET /api/v1/live
GET /api/v1/ready
```

`/live`: processo vivo.

`/ready`: verificar PostgreSQL, Redis, Supabase Storage, migrations, secrets obrigatórios, filas/workers e providers críticos habilitados.

Atualizar `fly.toml` para usar `/api/v1/ready`.

## 3.6 Rate limit forte

Aplicar limites:

```txt
/auth/login                    5/min/IP + 10/h/email
/auth/login/verify-2fa          5/5min/user
/auth/register                  10/h/IP
/auth/password-reset            5/h/email
/portal/magic-link/request      5/h/email + 20/h/IP
/portal/magic-link/verify       10/10min/IP
/documents/upload               30/h/user + plano
/admin/*                        3/min/IP + alerta
/billing/webhooks/*             validação token/HMAC
/developer/api-keys             10/h/user
/invoices/*                     quota por tenant
/ecac/*                         quota por tenant/provider
```

Produção com `RATE_LIMIT_STRICT=true` deve retornar `503` se Redis cair.

## 3.7 Docker non-root

Arquivo:

```txt
backend/Dockerfile
```

Adicionar:

```dockerfile
RUN addgroup --system app && adduser --system --ingroup app app
RUN chown -R app:app /app
USER app
```

## 3.8 Storage privado

Criar:

```txt
backend/app/domain/documents/security_policy.py
```

Requisitos:

- buckets privados;
- signed URLs com TTL curto;
- nunca retornar `storage_key` bruto;
- MIME sniffing real;
- limite por arquivo e plano;
- scan antivírus ou fila de verificação;
- status: `uploaded`, `scanning`, `safe`, `blocked`, `rejected`;
- path seguro:

```txt
tenants/{tenant_id}/clients/{client_id}/documents/{document_id}/{uuid_filename}
```

---

# 4. CI/CD e gates de segurança

Criar/ajustar:

```txt
.github/workflows/ci.yml
.github/workflows/security.yml
.github/workflows/deploy-staging.yml
.github/workflows/deploy-production.yml
```

Comandos obrigatórios:

```bash
ruff check backend
mypy backend/app
pytest backend/tests -q
docker build -f backend/Dockerfile .

npm ci --prefix frontend
npm run lint --prefix frontend
npm run type-check --prefix frontend
npm run build --prefix frontend

gitleaks detect --source .
pip-audit
npm audit --audit-level=high --prefix frontend
bandit -r backend/app
```

Bloquear merge se falhar:

- secret scan;
- teste cross-tenant;
- teste de produção sem docs públicas;
- teste de CORS sem localhost;
- migrations;
- build backend;
- build frontend;
- lint/typecheck.

---

# 5. Estrutura Fiscal Core

Criar domínios separados. Não despejar lógica em `operations.py`.

```txt
backend/app/domain/
  fiscal_core/
    events.py
    enums.py
    permissions.py

  invoices/
    models.py
    schemas.py
    repository.py
    service.py
    validators.py
    api.py
    providers/
      base.py
      nfse_nacional.py
      asaas_nfse.py
      municipal_generic.py
      mock.py

  ecac/
    models.py
    schemas.py
    repository.py
    service.py
    api.py
    providers/
      base.py
      serpro_integra_contador.py
      mock.py

  certificates/
    models.py
    schemas.py
    repository.py
    service.py
    api.py
    vault.py

  powers_of_attorney/
    models.py
    schemas.py
    repository.py
    service.py
    api.py

  fiscal_guides/
    models.py
    schemas.py
    repository.py
    service.py
    api.py

  fiscal_mailbox/
    models.py
    schemas.py
    repository.py
    service.py
    api.py

  monthly_closing/
    models.py
    schemas.py
    repository.py
    service.py
    api.py
```

Registrar routers em:

```txt
backend/app/api/v1/api.py
```

---

# 6. Módulo Notas Fiscais / NFS-e

## 6.1 Escopo

Implementar NFS-e antes de NF-e de mercadoria.

Casos de uso:

```txt
1. Contador emite NFS-e dos próprios honorários.
2. Contador emite NFS-e de serviço avulso.
3. Contador emite/acompanha NFS-e em nome do cliente prestador autorizado.
4. Sistema consulta status.
5. Sistema armazena XML, PDF e DANFSe em storage privado.
6. Sistema vincula nota a cliente, competência, cobrança e fechamento mensal.
```

## 6.2 Migration

Criar:

```txt
backend/alembic/versions/YYYYMMDD_create_fiscal_invoices.py
```

Tabelas:

```sql
invoice_issuers
invoice_service_profiles
invoices
invoice_events
invoice_provider_credentials
```

Campos mínimos `invoice_issuers`:

```txt
id
tenant_id
client_id nullable
issuer_type: accountant | client
legal_name
document
municipal_registration
state_registration
tax_regime
city_code
city_name
state
provider
certificate_id
active
created_at
updated_at
```

Campos mínimos `invoices`:

```txt
id
tenant_id
issuer_id
customer_client_id
receivable_id
status
invoice_type
competence
service_profile_id
service_description
service_code
amount
deductions
iss_rate
retained_taxes jsonb
provider
provider_invoice_id
provider_protocol
verification_code
number
series
xml_storage_key
pdf_storage_key
danfse_storage_key
rejection_reason
issued_at
cancelled_at
created_by
created_at
updated_at
```

Status:

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

## 6.3 Provider interface

Arquivo:

```txt
backend/app/domain/invoices/providers/base.py
```

Interface:

```python
class InvoiceProvider(Protocol):
    async def validate_issuer(self, issuer): ...
    async def issue_nfse(self, invoice): ...
    async def get_status(self, invoice): ...
    async def cancel_nfse(self, invoice, reason: str): ...
    async def fetch_xml(self, invoice) -> bytes: ...
    async def fetch_pdf(self, invoice) -> bytes: ...
```

## 6.4 Auditoria

Eventos obrigatórios:

```txt
invoice.draft.created
invoice.validated
invoice.issue.requested
invoice.issued
invoice.rejected
invoice.cancel.requested
invoice.cancelled
invoice.xml.downloaded
invoice.pdf.downloaded
invoice.sent_to_customer
```

## 6.5 Endpoints

```txt
GET    /api/v1/invoices
POST   /api/v1/invoices
GET    /api/v1/invoices/{id}
PATCH  /api/v1/invoices/{id}
POST   /api/v1/invoices/{id}/issue
POST   /api/v1/invoices/{id}/cancel
GET    /api/v1/invoices/{id}/events
GET    /api/v1/invoices/{id}/pdf-url
GET    /api/v1/invoices/{id}/xml-url

GET    /api/v1/invoice-issuers
POST   /api/v1/invoice-issuers
PATCH  /api/v1/invoice-issuers/{id}

GET    /api/v1/invoice-service-profiles
POST   /api/v1/invoice-service-profiles
PATCH  /api/v1/invoice-service-profiles/{id}
```

---

# 7. e-CAC / Integra Contador

## 7.1 Objetivo

Criar camada oficial para automação fiscal ligada à Receita Federal via provedor contratado.

Frontend pode chamar de `Central Receita/e-CAC`; backend deve tratar como provider `serpro_integra_contador`.

## 7.2 Estrutura

```txt
backend/app/domain/ecac/
  providers/serpro_integra_contador.py
```

Interface:

```python
class EcacProvider(Protocol):
    async def get_tax_status(self, subject): ...
    async def get_pgdas(self, subject, period): ...
    async def generate_das(self, subject, period): ...
    async def get_dctfweb(self, subject, period): ...
    async def get_mailbox_messages(self, subject): ...
    async def get_certidao_status(self, subject): ...
```

## 7.3 Tabelas

```txt
ecac_credentials
fiscal_subjects
ecac_requests
tax_status_snapshots
```

Campos mínimos `fiscal_subjects`:

```txt
id
tenant_id
client_id nullable
subject_type: accountant | client
document
legal_name
tax_regime
city_code
state
active
created_at
```

## 7.4 Serviços desejados

```txt
situação fiscal
pendências
certidão negativa/positiva com efeito negativa
caixa postal
PGDAS-D
DAS
DCTFWeb
DARF
procurações autorizadas
histórico fiscal por cliente
```

## 7.5 Endpoints

```txt
GET  /api/v1/ecac/subjects
POST /api/v1/ecac/subjects
GET  /api/v1/ecac/subjects/{id}
POST /api/v1/ecac/subjects/{id}/sync
GET  /api/v1/ecac/subjects/{id}/tax-status
GET  /api/v1/ecac/subjects/{id}/mailbox
GET  /api/v1/ecac/subjects/{id}/guides
GET  /api/v1/ecac/requests
```

---

# 8. Procurações

Tabela:

```txt
powers_of_attorney
```

Campos:

```txt
id
tenant_id
client_id
grantor_document
attorney_document
provider
services jsonb
valid_from
valid_until
status
last_checked_at
created_at
```

Status:

```txt
pending
active
expired
revoked
invalid
unknown
```

Endpoints:

```txt
GET    /api/v1/powers-of-attorney
POST   /api/v1/powers-of-attorney
GET    /api/v1/powers-of-attorney/{id}
PATCH  /api/v1/powers-of-attorney/{id}
POST   /api/v1/powers-of-attorney/{id}/check
```

Regras:

- bloquear consulta e-CAC sem procuração válida quando exigida;
- gerar alerta antes do vencimento;
- auditar toda verificação.

---

# 9. Certificados digitais

Tabelas:

```txt
digital_certificates
certificate_usage_events
```

Campos `digital_certificates`:

```txt
id
tenant_id
client_id nullable
owner_type: accountant | client
owner_document
certificate_type: A1 | A3 | cloud
provider
encrypted_storage_key
encrypted_password
serial_number
valid_from
valid_until
status
created_at
```

Requisitos:

- certificado A1 criptografado;
- senha em cofre/criptografia forte;
- nunca logar senha;
- auditoria de uso;
- alerta de vencimento;
- vínculo com emissor fiscal, e-CAC e procurações.

Endpoints:

```txt
GET    /api/v1/certificates
POST   /api/v1/certificates
GET    /api/v1/certificates/{id}
PATCH  /api/v1/certificates/{id}
POST   /api/v1/certificates/{id}/validate
```

---

# 10. Guias, pagamentos e comprovantes

Domínio:

```txt
backend/app/domain/fiscal_guides/
```

Tabela:

```txt
fiscal_guides
fiscal_guide_events
```

Campos:

```txt
id
tenant_id
client_id
subject_id
guide_type: DAS | DARF | DAE | GPS | DCTFWEB
competence
due_date
amount
status
barcode
pix_code
provider
provider_id
pdf_storage_key
payment_proof_storage_key
paid_at
created_at
```

Status:

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

Endpoints:

```txt
GET  /api/v1/fiscal-guides
POST /api/v1/fiscal-guides
GET  /api/v1/fiscal-guides/{id}
POST /api/v1/fiscal-guides/{id}/send
POST /api/v1/fiscal-guides/{id}/payment-proof
POST /api/v1/fiscal-guides/{id}/mark-paid
```

Regras:

- guia deve vincular cliente e competência;
- comprovante entra no dossiê;
- divergência gera alerta;
- envio ao cliente gera evento.

---

# 11. Caixa postal fiscal

Tabela:

```txt
fiscal_mailbox_messages
```

Campos:

```txt
id
tenant_id
subject_id
provider
external_id
sender
title
content_summary
received_at
due_date
risk_level
status
raw_payload
created_at
```

Riscos:

```txt
low
medium
high
critical
```

Endpoints:

```txt
GET  /api/v1/fiscal-mailbox
GET  /api/v1/fiscal-mailbox/{id}
POST /api/v1/fiscal-mailbox/{id}/mark-read
POST /api/v1/fiscal-mailbox/{id}/create-task
```

Regra:

- mensagem crítica deve criar item no Foco de Hoje;
- mensagem com prazo deve gerar obrigação/tarefa;
- payload bruto só para admin técnico autorizado.

---

# 12. Fechamento mensal e dossiê fiscal

Tabelas:

```txt
monthly_closings
monthly_closing_items
fiscal_dossiers
```

Campos `monthly_closings`:

```txt
id
tenant_id
client_id
competence
status
health_score
blockers jsonb
completed_at
created_at
unique(tenant_id, client_id, competence)
```

Dossiê deve incluir:

```txt
dados do cliente
competência
documentos
obrigações
notas fiscais
guias
comprovantes
pendências e-CAC
mensagens fiscais
eventos
hash do pacote
```

Endpoints:

```txt
GET  /api/v1/monthly-closings
POST /api/v1/monthly-closings/bootstrap
GET  /api/v1/monthly-closings/{id}
POST /api/v1/monthly-closings/{id}/complete
POST /api/v1/monthly-closings/{id}/reopen
POST /api/v1/monthly-closings/{id}/generate-dossier
GET  /api/v1/monthly-closings/{id}/dossier-url
```

---

# 13. Workers, filas e idempotência

Criar:

```txt
backend/app/workers/
  main.py
  queues.py
  jobs/
    fiscal_sync.py
    invoice_status_sync.py
    guide_payment_check.py
    mailbox_sync.py
    monthly_closing_generation.py
    document_scan.py
```

Jobs:

```txt
daily_ecac_sync
hourly_invoice_status_sync
weekly_pending_docs_notification
daily_certificate_expiration_check
daily_power_of_attorney_check
monthly_obligation_generation
monthly_closing_bootstrap
fiscal_dossier_generation
```

Toda operação externa deve registrar:

```txt
tenant_id
provider
operation
subject_id
period
idempotency_key
status
request_hash
response_hash
```

---

# 14. Testes obrigatórios

Criar:

```txt
backend/tests/test_security_production_config.py
backend/tests/test_cross_tenant_isolation.py
backend/tests/test_invoice_nfse_flow.py
backend/tests/test_ecac_provider_contract.py
backend/tests/test_certificates_security.py
backend/tests/test_powers_of_attorney.py
backend/tests/test_fiscal_guides.py
backend/tests/test_monthly_closing.py
backend/tests/test_storage_signed_urls.py
backend/tests/test_rate_limit_auth.py
```

Cobrir:

- tenant A não acessa dados do tenant B;
- nota fiscal não cruza tenant;
- guia não cruza tenant;
- certificado/procuração não cruzam tenant;
- storage assinado expira;
- docs públicas não existem em produção;
- CORS produção não contém localhost;
- secrets ausentes derrubam startup;
- provider mock de NFS-e emite, rejeita e cancela;
- provider mock e-CAC retorna pendência, erro de procuração e erro de certificado.

---

# 15. Definition of Done

Um item da Equipe Claude só está concluído quando:

```txt
migration criada
RLS aplicada
endpoint implementado
schemas criados
service/repository separados
audit log implementado
testes criados
cross-tenant validado quando aplicável
logs sem segredo
CI passando
staging validado
memória local atualizada sem commit
```

---

# 16. Ordem de execução

```txt
1. Limpeza do repositório.
2. README profissional.
3. SECURITY_CORRECTIONS.md consolidado.
4. Memória local ignorada.
5. Docs públicas desligadas em produção.
6. Secrets fail-closed.
7. Logs sem segredo.
8. CORS produção limpo.
9. /live e /ready.
10. Rate limit forte.
11. Docker non-root.
12. Storage privado + signed URLs.
13. CI security gates.
14. Domínio invoices/NFS-e.
15. Domínio certificates.
16. Domínio powers_of_attorney.
17. Domínio ecac.
18. Domínio fiscal_guides.
19. Domínio fiscal_mailbox.
20. Domínio monthly_closing/dossier.
21. Workers/fila.
22. Testes cross-tenant e provider contracts.
23. Staging.
24. Produção controlada.
```
