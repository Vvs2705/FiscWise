# ANTIGRAVYTI_REALIZAR — Equipe Produto e Features

**Responsável:** Antigravyti (equipe produto)  
**Objetivo:** Implementar os domínios de feature que transformam o FiscWise em produto competitivo.  
**Regra de ouro:** Não toque em nenhum arquivo de segurança, middleware de autenticação, CORS, rate limiter ou config de infraestrutura — isso é responsabilidade da equipe Claude. Toda nova feature usa os helpers que a equipe Claude já construiu (audit_log, get_signed_url, validate_file_mime).

---

## Fronteiras desta equipe

### Você PODE criar/modificar
- `backend/app/domain/invoices/` (novo domínio, do zero)
- `backend/app/domain/ecac/` (novo domínio, do zero)
- `backend/app/domain/certificates/` — **somente evoluir**, sem quebrar o que existe
- `backend/app/domain/obligations/` — **somente evoluir o motor**, sem reescrever o que funciona
- `backend/app/domain/billing/` — **somente adicionar**, sem remover
- `backend/app/domain/guias/` (novo domínio, do zero)
- `backend/app/api/routes/` — adicionar novos arquivos de rota; não editar rotas existentes
- `backend/alembic/versions/` — criar novas migrations; não alterar migrations existentes
- `frontend/src/features/invoices/` (novo, do zero)
- `frontend/src/features/ecac/` (novo, do zero)
- `frontend/src/features/guias/` (novo, do zero)
- `frontend/src/components/` — adicionar novos componentes; não editar componentes compartilhados que outros módulos usam sem aprovação
- `frontend/src/hooks/` — adicionar novos hooks

### Você NÃO PODE modificar sem coordenação
- `backend/app/core/` (config, security, middleware, logging, audit) — use, não altere
- `backend/app/api/deps.py` — use as dependências existentes, não altere
- `backend/Dockerfile`, `docker-compose.yml`, `fly.toml`
- `.github/workflows/`
- `backend/app/domain/clients/` — se precisar de dado de cliente, leia via repository, não altere o domínio
- Qualquer migration já aplicada

---

## Pré-requisito: Usar os helpers da equipe Claude

Antes de implementar qualquer feature, confirme que estes helpers existem e use-os:

```python
# Auditoria — importar e usar em todo endpoint sensível
from app.core.audit import audit_log

# Storage — nunca gerar URL diretamente
from app.core.storage import get_signed_url

# Validação de arquivo — sempre antes de salvar
from app.core.file_validator import validate_file_mime
```

Se a equipe Claude ainda não entregou esses helpers, crie stubs com `pass` e marque com `# TODO: aguardar equipe Claude` — não bloqueie seu progresso.

---

## Domínio 1 — Notas Fiscais (NFS-e) — Onda 1

**Diretório:** `backend/app/domain/invoices/`  
**Prioridade:** MÁXIMA — este domínio é o principal gerador de receita do produto.

### 1.1 Estrutura de arquivos obrigatória

```
backend/app/domain/invoices/
  __init__.py
  models.py
  schemas.py
  repository.py
  service.py
  permissions.py
  validators.py
  events.py
  providers/
    __init__.py
    base.py          # ABC com interface padrão
    nfse_nacional.py # Integração Portal Nacional NFS-e
    mock.py          # Mock para testes e dev
  tests/
    test_invoice_service.py
    test_invoice_api.py
    test_invoice_cross_tenant.py
```

### 1.2 Migrations Alembic — criar nesta ordem

```sql
-- Migration 1: invoice_issuers
CREATE TABLE invoice_issuers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  client_id UUID REFERENCES clients(id),
  cnpj VARCHAR(14) NOT NULL,
  inscricao_municipal VARCHAR(50),
  regime_tributario VARCHAR(20) NOT NULL,
  municipio_ibge VARCHAR(7) NOT NULL,
  cod_servico_lc116 VARCHAR(10),
  aliquota_iss NUMERIC(5,4),
  retencao_iss BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Migration 2: invoices
CREATE TABLE invoices (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  issuer_id UUID NOT NULL REFERENCES invoice_issuers(id),
  client_id UUID REFERENCES clients(id),
  status VARCHAR(20) NOT NULL DEFAULT 'draft',
  -- Status válidos: draft | validating | queued | processing | issued | rejected | cancel_requested | cancelled | replaced | failed
  numero VARCHAR(50),
  serie VARCHAR(5),
  competencia DATE NOT NULL,
  valor_servico NUMERIC(15,2) NOT NULL,
  valor_deducoes NUMERIC(15,2) DEFAULT 0,
  valor_iss NUMERIC(15,2),
  descricao_servico TEXT NOT NULL,
  tomador_nome VARCHAR(255),
  tomador_cpf_cnpj VARCHAR(14),
  tomador_email VARCHAR(255),
  tomador_municipio_ibge VARCHAR(7),
  provider_protocol VARCHAR(100),
  provider_response JSONB,
  xml_content TEXT,
  pdf_storage_path VARCHAR(500),
  xml_storage_path VARCHAR(500),
  billing_charge_id UUID,  -- vínculo com financeiro (sem FK agora, apenas referência)
  issued_at TIMESTAMPTZ,
  cancelled_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Migration 3: invoice_events
CREATE TABLE invoice_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  invoice_id UUID NOT NULL REFERENCES invoices(id),
  tenant_id UUID NOT NULL,
  event_type VARCHAR(50) NOT NULL,
  payload JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Migration 4: invoice_rejections
CREATE TABLE invoice_rejections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  invoice_id UUID NOT NULL REFERENCES invoices(id),
  tenant_id UUID NOT NULL,
  codigo_rejeicao VARCHAR(20),
  descricao TEXT NOT NULL,
  raw_response JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

Habilitar RLS em TODAS as tabelas acima:
```sql
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON invoices USING (tenant_id = current_setting('app.tenant_id')::UUID);
-- Repetir para invoice_issuers, invoice_events, invoice_rejections
```

### 1.3 Status machine do invoice

Transições válidas (implementar em `service.py`, rejeitar transições inválidas com `ValueError`):

```
draft → validating → queued → processing → issued
processing → rejected
issued → cancel_requested → cancelled
rejected → draft (correção e reenvio)
processing → failed
```

### 1.4 Provider base (ABC)

```python
# providers/base.py
from abc import ABC, abstractmethod

class NfseProvider(ABC):
    @abstractmethod
    async def emit(self, invoice_data: dict) -> dict:
        """Envia NFS-e. Retorna {'protocol': str, 'status': str, 'raw': dict}"""

    @abstractmethod
    async def cancel(self, protocol: str, reason: str) -> dict:
        """Cancela NFS-e por protocolo."""

    @abstractmethod
    async def query_status(self, protocol: str) -> dict:
        """Consulta status de protocolo no provedor."""
```

### 1.5 Mock provider (dev e testes)

```python
# providers/mock.py
class MockNfseProvider(NfseProvider):
    async def emit(self, invoice_data: dict) -> dict:
        return {
            "protocol": f"MOCK-{uuid4()}",
            "status": "issued",
            "numero": "000001",
            "raw": {"mock": True}
        }
```

### 1.6 Endpoints obrigatórios

```
POST   /api/v1/invoices/issuers               → criar perfil emissor
GET    /api/v1/invoices/issuers               → listar emissores do tenant
POST   /api/v1/invoices                       → criar rascunho de NFS-e
GET    /api/v1/invoices                       → listar notas (com filtro por status, cliente, competência)
GET    /api/v1/invoices/{id}                  → detalhe da nota
POST   /api/v1/invoices/{id}/emit             → emitir nota (draft → validating → ...)
POST   /api/v1/invoices/{id}/cancel           → solicitar cancelamento
GET    /api/v1/invoices/{id}/pdf              → URL assinada para PDF (usar get_signed_url)
GET    /api/v1/invoices/{id}/xml              → URL assinada para XML
GET    /api/v1/invoices/{id}/events           → histórico de eventos
GET    /api/v1/invoices/{id}/rejections       → motivos de rejeição
```

### 1.7 Regras de negócio obrigatórias em service.py

- Validar CPF/CNPJ do tomador antes de emitir (usar validação modular 11).
- Valor do serviço deve ser > 0.
- Competência não pode ser futura (mês/ano).
- Após emissão com sucesso: armazenar XML via `get_signed_url`, chamar `audit_log` com `action="invoice.issued"`.
- Após rejeição: criar `InvoiceRejection`, emitir evento `invoice.rejected`, status → `rejected`.
- Toda emissão deve ser assíncrona (Celery task ou background task do FastAPI) — não bloquear o request.

### 1.8 Frontend — estrutura de arquivos

```
frontend/src/features/invoices/
  pages/
    InvoicesListPage.tsx       # Lista com filtros e paginação
    InvoiceDetailPage.tsx      # Detalhe com timeline de eventos
    InvoiceNewPage.tsx         # Formulário de novo rascunho
    InvoiceEmitPage.tsx        # Revisão antes de emitir
  components/
    InvoiceStatusBadge.tsx     # Badge colorido por status
    InvoiceTimeline.tsx        # Timeline de eventos da nota
    InvoiceRejectionAlert.tsx  # Exibe motivo de rejeição com botão de correção
    IssuerProfileForm.tsx      # Formulário de perfil fiscal do emissor
  hooks/
    useInvoices.ts             # CRUD + queries
    useInvoiceEmission.ts      # Fluxo de emissão com polling de status
  services/
    invoices.service.ts        # Chamadas à API
  schemas/
    invoice.schema.ts          # Zod schemas para validação de formulários
```

### 1.9 Critérios de aceite completos

- [ ] Criar rascunho → salvo com status `draft`
- [ ] Emitir rascunho → status evolui até `issued` ou `rejected`
- [ ] XML armazenado em bucket privado após emissão
- [ ] PDF acessível via URL assinada com TTL 300s
- [ ] Rejeição exibe código e descrição legível
- [ ] Tentativa de acessar nota de outro tenant → 404
- [ ] `audit_log` registrado em toda emissão
- [ ] Teste cross-tenant passa

---

## Domínio 2 — e-CAC / Receita Federal — Onda 2

**Diretório:** `backend/app/domain/ecac/`  
**Prioridade:** ALTA — diferenciador competitivo imediato.

### 2.1 Estrutura de arquivos

```
backend/app/domain/ecac/
  __init__.py
  models.py
  schemas.py
  repository.py
  service.py
  permissions.py
  events.py
  integrations/
    __init__.py
    base.py          # ABC para integração e-CAC
    integra_contador.py  # Integração Serpro/Integra Contador
    mock.py
  tests/
```

### 2.2 Migrations Alembic

```sql
-- ecac_proxies (procurações)
CREATE TABLE ecac_proxies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL,
  client_id UUID REFERENCES clients(id),
  outorgante_cpf_cnpj VARCHAR(14) NOT NULL,
  outorgante_nome VARCHAR(255),
  procurador_cpf VARCHAR(11) NOT NULL,
  tipo VARCHAR(50),               -- 'e-CAC', 'NFS-e', 'eSocial', etc.
  servicos_autorizados JSONB,     -- lista de serviços com acesso
  data_inicio DATE,
  data_validade DATE,
  status VARCHAR(20) DEFAULT 'ativa',
  ultima_verificacao TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ecac_fiscal_situations
CREATE TABLE ecac_fiscal_situations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL,
  client_id UUID REFERENCES clients(id),
  cpf_cnpj VARCHAR(14) NOT NULL,
  status_geral VARCHAR(50),
  pendencias JSONB,
  debitos JSONB,
  certidao_status VARCHAR(30),
  certidao_validade DATE,
  raw_response JSONB,
  consultado_em TIMESTAMPTZ DEFAULT NOW()
);

-- Habilitar RLS em ambas as tabelas
```

### 2.3 Endpoints obrigatórios

```
GET    /api/v1/ecac/proxies                       → lista procurações do tenant
POST   /api/v1/ecac/proxies                       → cadastrar procuração manual
GET    /api/v1/ecac/proxies/{id}                  → detalhe
PUT    /api/v1/ecac/proxies/{id}                  → atualizar
GET    /api/v1/ecac/proxies/expiring              → procurações vencendo em 30d
GET    /api/v1/ecac/fiscal-situation/{client_id}  → situação fiscal do cliente
POST   /api/v1/ecac/fiscal-situation/{client_id}/refresh  → reprocessar consulta
GET    /api/v1/ecac/clients-without-proxy         → clientes sem procuração
```

### 2.4 Regras de negócio

- Alertar automaticamente quando procuração vence em 30 dias → criar evento `proxy.expiring`.
- Consulta de situação fiscal é assíncrona (não bloquear request).
- Resultado de consulta sempre salvo em `ecac_fiscal_situations` com timestamp.
- Nunca expor credencial ou certificado no response.
- `audit_log` obrigatório em toda consulta: `action="ecac.situation_consulted"`.

### 2.5 Frontend

```
frontend/src/features/ecac/
  pages/
    EcacCentralPage.tsx         # Hub com sub-rotas
    ProxiesListPage.tsx         # Lista de procurações com status
    ProxyDetailPage.tsx
    FiscalSituationPage.tsx     # Situação fiscal por cliente
  components/
    ProxyStatusBadge.tsx
    ProxyExpirationAlert.tsx    # Alerta visual para vencimentos próximos
    FiscalSituationCard.tsx
    ClientsWithoutProxyList.tsx
```

### 2.6 Critérios de aceite

- [ ] Procuração cadastrada → aparece na lista
- [ ] Procuração vencendo em 30d → aparece em `/expiring` e gera evento
- [ ] Consulta de situação fiscal retorna dados reais (mock em dev)
- [ ] Cliente sem procuração → listado em `/clients-without-proxy`
- [ ] `audit_log` criado em toda consulta e-CAC
- [ ] Cross-tenant: procuração de tenant A não visível para tenant B

---

## Domínio 3 — Certificados Digitais (evolução) — Onda 1/2 paralelo

**Diretório:** `backend/app/domain/certificates/` — **JÁ EXISTE, APENAS EVOLUIR**  
**Prioridade:** MÉDIA-ALTA — necessário para NFS-e e e-CAC.

### 3.1 O que existe — não quebre

Antes de qualquer alteração: leia os models, schemas e routes existentes. Liste o que existe no início do seu trabalho neste domínio.

### 3.2 O que adicionar (sem remover o que existe)

Adicionar campos à tabela `certificates` via nova migration:
```sql
ALTER TABLE certificates
  ADD COLUMN IF NOT EXISTS uso_autorizado JSONB DEFAULT '[]',
  ADD COLUMN IF NOT EXISTS ultimo_uso TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS bloqueado BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS motivo_bloqueio VARCHAR(255);
```

Adicionar endpoints:
```
GET  /api/v1/certificates/expiring           → certificados vencendo em 60d
POST /api/v1/certificates/{id}/block         → bloquear certificado
GET  /api/v1/certificates/{id}/usage-trail   → trilha de uso
```

Regra: senha do certificado NUNCA aparece em resposta de API — nem em dev. Se existir campo `password` no model, garantir que o schema de response nunca o inclua.

---

## Domínio 4 — Guias, Impostos e Comprovantes — Onda 3

**Diretório:** `backend/app/domain/guias/` (novo)

### 4.1 Migrations Alembic

```sql
CREATE TABLE tax_guides (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL,
  client_id UUID REFERENCES clients(id),
  tipo VARCHAR(20) NOT NULL,  -- 'DAS' | 'DARF' | 'GPS' | 'ISS' | 'outro'
  competencia DATE NOT NULL,
  valor NUMERIC(15,2) NOT NULL,
  vencimento DATE NOT NULL,
  status VARCHAR(20) DEFAULT 'pendente',  -- 'pendente' | 'enviada' | 'paga' | 'atrasada'
  pdf_storage_path VARCHAR(500),
  comprovante_storage_path VARCHAR(500),
  enviada_em TIMESTAMPTZ,
  paga_em TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE tax_guides ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON tax_guides USING (tenant_id = current_setting('app.tenant_id')::UUID);
```

### 4.2 Endpoints

```
POST   /api/v1/guias                      → registrar guia
GET    /api/v1/guias                      → listar (filtro: tipo, status, competência, cliente)
GET    /api/v1/guias/{id}                 → detalhe
POST   /api/v1/guias/{id}/upload-pdf      → anexar PDF da guia
POST   /api/v1/guias/{id}/upload-comprovante  → anexar comprovante de pagamento
PUT    /api/v1/guias/{id}/mark-paid       → marcar como paga
GET    /api/v1/guias/pending-receipt      → guias pagas sem comprovante (alerta)
```

### 4.3 Regras de negócio

- Upload de PDF/comprovante → usar `validate_file_mime` antes de salvar.
- URL de PDF e comprovante → sempre via `get_signed_url` (TTL 300s).
- Guia com `vencimento < hoje` e `status != 'paga'` → status automático `atrasada`.
- `audit_log` obrigatório: `action="guide.paid"`, `action="guide.receipt_uploaded"`.

### 4.4 Frontend

```
frontend/src/features/guias/
  pages/
    GuiasListPage.tsx
    GuiaDetailPage.tsx
  components/
    GuiaStatusBadge.tsx
    GuiaUploadComprovante.tsx
    PendingReceiptAlert.tsx     # Lista de guias sem comprovante
```

---

## Domínio 5 — Motor de Obrigações (evolução) — Onda 3

**Diretório:** `backend/app/domain/obligations/` — **JÁ EXISTE, APENAS EVOLUIR**

### 5.1 O que adicionar ao motor existente

Sem remover nada que funciona. Adicionar suporte a novos campos no perfil do cliente:

```sql
ALTER TABLE clients
  ADD COLUMN IF NOT EXISTS cnae VARCHAR(7),
  ADD COLUMN IF NOT EXISTS regime_tributario VARCHAR(20),  -- 'simples' | 'lucro_presumido' | 'lucro_real' | 'mef'
  ADD COLUMN IF NOT EXISTS municipio_ibge VARCHAR(7),
  ADD COLUMN IF NOT EXISTS uf VARCHAR(2),
  ADD COLUMN IF NOT EXISTS tem_funcionarios BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS inscricao_estadual VARCHAR(30),
  ADD COLUMN IF NOT EXISTS inscricao_municipal VARCHAR(30);
```

Adicionar regras de obrigação para:
- `DAS` — todo Simples Nacional até dia 20 do mês seguinte
- `PGDAS-D` — apuração mensal Simples Nacional
- `DCTFWeb` — empresas com retenções (quinzenal)
- `EFD-Reinf` — prestadores de serviço com retenção na fonte
- `ISS municipal` — baseado em `municipio_ibge` do client

Cada nova regra deve ser uma função isolada em `obligations/rules/` com:
- Input: `client_profile: dict`
- Output: `list[ObligationRule]`
- Sem efeitos colaterais — funções puras

### 5.2 Critérios de aceite

- [ ] Cliente Simples Nacional → DAS gerado automaticamente para cada mês
- [ ] Cliente com `tem_funcionarios=True` → eSocial e DCTFWeb aparecem no calendário
- [ ] Regras novas não quebram obrigações existentes (rodar suite de testes antes de commitar)

---

## Domínio 6 — Financeiro (evolução) — Onda 1/2 paralelo

**Diretório:** `backend/app/domain/billing/` — **JÁ EXISTE, APENAS ADICIONAR**

### 6.1 O que adicionar

Campo de vínculo com nota fiscal (sem FK hard — referência suave):

```sql
ALTER TABLE billing_charges
  ADD COLUMN IF NOT EXISTS invoice_id UUID,
  ADD COLUMN IF NOT EXISTS nfse_emitida BOOLEAN DEFAULT FALSE;
```

Endpoint de relatório de inadimplência:
```
GET /api/v1/billing/delinquency-report → clientes com cobranças vencidas há mais de X dias
```

Régua de cobrança automática (via Celery ou cron):
```
D-7, D-3, D0, D+1, D+3, D+7 → emitir evento `payment.reminder` por tenant
```

**Não alterar** lógica existente de criação de cobrança, Pix ou boleto.

---

## Regras gerais para todos os domínios

### Cada domínio deve ter

1. **Migration Alembic** com RLS habilitado.
2. **Repository** com todos os filtros incluindo `tenant_id` obrigatoriamente.
3. **Service** com regras de negócio — sem lógica em routes.
4. **Permissions** com verificação de permissão antes de qualquer operação sensível.
5. **Events** emitindo eventos para domínios que precisam reagir.
6. **Testes**:
   - `test_{domain}_service.py` — unitário sem banco
   - `test_{domain}_api.py` — integração com banco de teste
   - `test_{domain}_cross_tenant.py` — isolamento multi-tenant

### Padrão de repository

```python
class InvoiceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, invoice_id: UUID, tenant_id: UUID) -> Invoice | None:
        # SEMPRE filtrar por tenant_id — nunca buscar só pelo id
        result = await self.db.execute(
            select(Invoice).where(
                Invoice.id == invoice_id,
                Invoice.tenant_id == tenant_id  # OBRIGATÓRIO
            )
        )
        return result.scalar_one_or_none()
```

### Padrão de rota

```python
@router.get("/{invoice_id}")
async def get_invoice(
    invoice_id: UUID,
    current_user: User = Depends(get_current_user),  # depende existente
    db: AsyncSession = Depends(get_db),               # depende existente
):
    repo = InvoiceRepository(db)
    invoice = await repo.get_by_id(invoice_id, current_user.tenant_id)
    if not invoice:
        raise HTTPException(404)
    return InvoiceResponse.model_validate(invoice)
```

---

## Progresso e handoff

### Ao completar cada domínio

1. Commit atômico por entrega lógica: `feat(invoices): adiciona emissão NFS-e com mock provider`
2. Nunca commitar com testes quebrando.
3. Registrar no `PROGRESSO_ANTIGRAVYTI.md` (arquivo local, não sobe para git):
   - O que foi feito
   - Migrations aplicadas
   - Endpoints entregues
   - Testes passando
   - O que ficou para próximo ciclo

### Ordem de execução recomendada

```
Ciclo 1 (paralelo, sem dependências entre si):
  - Domínio 1 (Invoices) — Fase 1: migrations + models + schemas + mock provider + service básico
  - Domínio 3 (Certificates) — campos de evolução
  - Domínio 6 (Billing) — campo invoice_id + relatório inadimplência

Ciclo 2 (após Ciclo 1):
  - Domínio 1 — Fase 2: endpoints + frontend básico
  - Domínio 2 (e-CAC) — migrations + models + mock
  - Domínio 4 (Guias) — migrations + models + endpoints

Ciclo 3:
  - Domínio 1 — Fase 3: integração real NFS-e Nacional (quando disponível)
  - Domínio 2 — endpoints + frontend
  - Domínio 5 (Motor de Obrigações) — novas regras fiscais
  - Domínio 4 — frontend
```

### Sinalização de bloqueio

Se precisar de algo da equipe Claude (ex: helper `audit_log` não entregue, `get_signed_url` com bug), abrir issue/comentário no PR com tag `[BLOQUEIO-SEGURANÇA]` e seguir com stub — não pare o domínio inteiro.

---

## Fontes técnicas de referência

- Portal Nacional NFS-e API: https://www.gov.br/nfse/pt-br/biblioteca/documentacao-tecnica/apis-prod-restrita-e-producao
- Integra Contador Serpro: https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/
- Obrigatoriedade NFS-e Simples Nacional: vigência 01/09/2026
