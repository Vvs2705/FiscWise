# Status de Implementação de Features — FiscWise

**Data:** 2026-05-24  
**Versão:** Feature #1-6 Complete (Pronto para Staging)

---

## Feature #1: Filtros Avançados de Clientes ✅

### Implementado:
- ✅ Modelo `AccountingClient`: adicionados campos `cnae_code`, `tax_regime` (com índice), `entity_type` (com índice)
- ✅ Endpoint GET `/clients`: 3 novos query params para filtro (`tax_regime`, `entity_type`, `cnae_code`)
- ✅ Migration Alembic `20260522_advanced_features.py` criada
- ✅ Índices de banco de dados para performance

### Status: PRONTO PARA MERGE

---

## Feature #2: Billing Automatizado ✅

### Implementado:
- ✅ Modelo `AccountingClient`: adicionados campos `monthly_fee` (Numeric), `billing_day` (Integer), `portal_user_id` (UUID)
- ✅ Endpoint POST `/receivables/generate-monthly`: gera faturas mensais idempotentes
- ✅ Lógica de vencimento flexível baseado em `billing_day`
- ✅ APScheduler integrado: executa automaticamente todo dia 1º do mês às 2:00 AM UTC
- ✅ Arquivo `app/services/scheduler.py` criado com task scheduler
- ✅ Integração com lifespan do FastAPI

### Status: PRONTO PARA MERGE

---

## Feature #3: Upload e Parsing de Documentos ✅

### Implementado:
- ✅ Modelo `ClientDocument`: adicionados campos `parse_status`, `parsed_data` (JSON), `parse_error`, `parsed_at`
- ✅ Endpoint POST `/clients/{client_id}/documents`: upload de arquivos (PDF, Excel, Word, TXT)
- ✅ Endpoint GET `/clients/{client_id}/documents`: listagem de documentos
- ✅ Arquivo `app/services/document_parser.py` criado com parsers para:
  - PDF (via pdfplumber) — extrai texto e metadados
  - Excel (via openpyxl) — extrai dados de planilhas
  - Word (via python-docx) — extrai texto e tabelas
  - TXT — extrai conteúdo bruto
- ✅ Background task assíncrona para parsing (não bloqueia upload)
- ✅ Status de parsing (`pending`, `processing`, `completed`, `failed`)
- ✅ Armazenamento de erros em `parse_error`

### Dependências Adicionadas:
```
pdfplumber==0.11.0
openpyxl==3.10.10
python-docx==0.8.11
```

### Status: PRONTO PARA MERGE

---

## Feature #4: Client Portal — Acesso ao Cliente ✅

### Implementado:
- ✅ Nova role `CLIENT` adicionada ao enum `UserRole`
- ✅ Modelo `ClientPortalInvite` criado com:
  - Status: `pending`, `accepted`, `rejected`, `expired`
  - Rastreamento de quem convidou e quando foi aceito
  - Expiração automática em 30 dias
- ✅ Arquivo `app/api/v1/endpoints/portal.py` criado com 4 endpoints:
  - **POST `/portal/invites`**: convida cliente (ADMIN/OWNER only)
  - **GET `/portal/invites/{invite_id}`**: visualiza convite (público)
  - **POST `/portal/invites/{invite_id}/accept`**: aceita convite e cria conta CLIENT
  - **GET `/portal/my-data`**: cliente acessa seus próprios dados
- ✅ Autorização por role implementada (CLIENT users só veem seus dados)
- ✅ Integração com lifespan do FastAPI para iniciar scheduler
- ✅ Migration Alembic `20260523_client_portal_invites.py` criada

### Dependências Adicionadas:
```
apscheduler==3.10.4
pytz==2024.1
```

### Status: PRONTO PARA MERGE

---

## Feature #5: Cadastro Expandido de Empresa ✅

### Implementado:
- ✅ Modelo `AccountingClient`: adicionados campos `responsible_name`, `responsible_cpf`, `responsible_address`, `responsible_phone`, `responsible_email`
- ✅ Modelo `CompanyPartner`: criado para gerenciar sócios com campos `name`, `cpf`, `participation_percentage`, `entry_date`, `status`
- ✅ Endpoints CRUD para sócios:
  - **POST `/clients/{client_id}/partners`**: criar sócio
  - **GET `/clients/{client_id}/partners`**: listar sócios
  - **GET `/clients/{client_id}/partners/{partner_id}`**: detalhes do sócio
  - **PUT `/clients/{client_id}/partners/{partner_id}`**: editar sócio
  - **DELETE `/clients/{client_id}/partners/{partner_id}`**: remover sócio
- ✅ Endpoint PATCH `/clients/{client_id}` já existente para editar dados da empresa (adicionados campos de responsável)
- ✅ Schemas Pydantic para validação (PartnerCreate, PartnerUpdate, PartnerResponse)
- ✅ Arquivo `app/api/v1/endpoints/partners.py` criado

### Status: PRONTO PARA MERGE

---

## Feature #6: Documentos Organizados por Empresa ✅

### Implementado:
- ✅ Modelo `CompanyDocument`: armazena documentos oficiais da empresa com campos `document_type`, `file_url`, `upload_date`, `expiration_date`, `status`
- ✅ Enum `CompanyDocumentType` com 9 tipos:
  - CNPJ
  - CONTRATO_SOCIAL
  - INSCRICAO_MUNICIPAL
  - INSCRICAO_ESTADUAL
  - ALVARA_FUNCIONAMENTO
  - LICENCA_SANITARIA
  - CNES
  - ALVARA_BOMBEIROS
  - CRO_JURIDICO
- ✅ Endpoints para documentos:
  - **POST `/clients/{client_id}/company-documents`**: upload documento
  - **GET `/clients/{client_id}/company-documents`**: listar documentos
  - **GET `/clients/{client_id}/company-documents/expiring-soon`**: alertar vencimentos (padrão 30 dias)
  - **GET `/clients/{client_id}/company-documents/{doc_id}`**: detalhes do documento
  - **PUT `/clients/{client_id}/company-documents/{doc_id}`**: editar documento
  - **DELETE `/clients/{client_id}/company-documents/{doc_id}`**: remover documento
- ✅ Schemas Pydantic para validação e resposta
- ✅ Índices de banco para performance (tenant_id, client_id, document_type, status, expiration_date)
- ✅ Arquivo `app/api/v1/endpoints/company_documents.py` criado

### Status: PRONTO PARA MERGE

---

## Resumo de Migrações Criadas

| Migration | Descrição | Status |
|-----------|-----------|--------|
| 20260522_advanced_features.py | Filtros + Billing | Criada ✅ |
| 20260523_client_portal_invites.py | Portal de Cliente | Criada ✅ |
| 20260524_expanded_client_registry.py | Cadastro Expandido + Documentos | Criada ✅ |

**Como executar:**
```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
```

---

## Próximos Passos

### Fase de Testes:
1. **Testes Unitários**: Validar lógica de parsing, billing, portal, partners, documents
2. **Testes de Integração**: 
   - Fluxo completo (invite → accept → access)
   - CRUD de sócios (create → read → update → delete)
   - Upload e gerenciamento de documentos da empresa
3. **Testes de Scheduler**: Verificar execução automática no dia 1º
4. **Testes de Upload**: Validar parsing de diferentes formatos
5. **Testes de Expiração**: Verificar alerta de documentos vencendo em 30 dias
6. **Testes de Validação**: CPF de responsável e sócios, percentual de participação

### Fase de Deployment:
1. Executar migrações em staging
2. Validar funcionalidades em staging
3. Deploy para produção
4. Monitorar scheduler e background tasks

### Landing Page (vstack-site):
- Equipe de frontend responsável
- Diagnóstico completo em `FISCWISE_LANDING_DIAGNOSTIC.md`

---

## Resumo Técnico

### Arquitetura de Features:
- **Clean Architecture**: separação entre models, schemas, services, endpoints
- **Async/Await**: todas as operações assíncronas
- **Background Tasks**: parsing e billing em background
- **Multi-tenant**: isolamento por tenant_id
- **Security**: role-based access control (RBAC)

### Stack Adicionado:
- Document Processing: pdfplumber, openpyxl, python-docx
- Task Scheduling: APScheduler
- Timezone: pytz

### Performance:
- Índices de banco: CNAE code, tax regime, entity type, expires_at, responsible_cpf, document_type, expiration_date
- Background processing: não bloqueia requisições HTTP
- Idempotência: geração de billing verifica duplicatas

### Endpoints Totais Implementados:
- **Authentication**: 6 endpoints (signup, login, logout, refresh, reset, verify)
- **Clients**: 4 endpoints (list, get, create, patch) + responsável fields
- **Partners**: 5 endpoints (create, list, get, update, delete)
- **Company Documents**: 6 endpoints (upload, list, get, update, delete, expiring-soon)
- **Deadlines**: 6 endpoints (list, get, create, update, delete, archive)
- **Receivables**: 4 endpoints (list, get, create, generate-monthly)
- **Digital Certificates**: 6 endpoints (list, get, create, update, delete, renewal-alert)
- **Client Documents**: 3 endpoints (upload, list, delete)
- **Portal**: 4 endpoints (invite, accept, view-invite, my-data)
- **Admin/Health**: 4 endpoints (health, diagnostics, admin fixes)

---

## Checklist de Deploy

- [ ] Todos os requirements instalados (`pip install -r requirements.txt`)
- [ ] Migrações executadas (`alembic upgrade head`)
- [ ] Variáveis de ambiente configuradas
- [ ] Tests rodando com sucesso
- [ ] Scheduler iniciando corretamente
- [ ] Background tasks funcionando
- [ ] Endpoints documentados em `/docs`
- [ ] Rate limiting funcionando
- [ ] Logging configurado

---

**Pronto para aprovação e deployment!** ✅
