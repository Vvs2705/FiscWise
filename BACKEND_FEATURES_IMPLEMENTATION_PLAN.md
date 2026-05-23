# FiscWise Backend — Plano de Implementação de 4 Funcionalidades Críticas

**Data:** 22 de Maio de 2026  
**Escopo:** Advanced Filtering, Automated Billing, File Upload+Parsing, Client Portal  
**Status:** 📋 Análise (Pronto para Implementação)  
**Responsável:** Backend Team (FastAPI + SQLAlchemy)

---

## 📋 Resumo Executivo

Identificadas **4 funcionalidades críticas** que aumentam o valor do FiscWise para contadores. Duas já têm infraestrutura parcial (`AccountReceivable` table existe), duas precisam ser construídas do zero.

| # | Feature | Dia Estimado | Complexidade | Estado | Prioridade |
|---|---------|--------------|--------------|--------|-----------|
| 1 | Advanced Client Filtering | 2 dias | ⚫ Baixa | Schema OK | 🔥 PRIMEIRO |
| 2 | Automated Billing (Honorários) | 1.5 dias | ⚫⚫ Média | Parcial | 🔥 SEGUNDO |
| 3 | File Upload + Parsing (Secrets) | 4.5 dias | ⚫⚫⚫ Alta | Zero | 🔴 TERCEIRO |
| 4 | Client Portal (New Role) | 4.5 dias | ⚫⚫⚫ Alta | Zero | 🔴 ÚLTIMO |

**Total:** 12.5 dias (2-3 sprints)  
**Risco:** MÉDIO (3 features independentes, 1 complexa com nova role)

---

## 🎯 Feature #1: Advanced Client Filtering

**Objetivo:** Permitir que contadores pesquisem clientes por múltiplos critérios (CNAE, regime tributário, tipo de entidade, data de criação).

**Status Atual:**
- ✓ Endpoint `GET /clients` existe
- ✓ Filtro básico por `search` (name) e `status` funciona
- ❌ Faltam: CNAE, tax_regime, entity_type, created_date, pagination completa

### Mudanças Necessárias

#### 1. Modelo (`backend/app/models/operations.py`)

```python
class AccountingClient(Base):
    __tablename__ = "accounting_clients"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str]
    email: Mapped[str]
    cnpj: Mapped[str]
    
    # ✅ JÁ EXISTEM
    status: Mapped[str] = mapped_column(default="active")  # active, inactive
    created_at: Mapped[datetime]
    
    # 🆕 NOVOS CAMPOS (Adicionar)
    cnae_code: Mapped[Optional[str]] = mapped_column(nullable=True, index=True)  # Ex: "6201-5/00"
    tax_regime: Mapped[Optional[str]] = mapped_column(nullable=True, index=True)  # simples, lucro_presumido, lucro_real, mei
    entity_type: Mapped[Optional[str]] = mapped_column(nullable=True, index=True)  # pj, mei, autônomo
```

#### 2. Endpoint (`backend/app/api/v1/endpoints/operations.py`)

```python
@router.get("/clients")
async def list_clients(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    # Filtros Básicos
    search: Optional[str] = Query(None, min_length=1),
    status: Optional[str] = Query(None, regex="^(active|inactive)$"),
    # 🆕 Novos Filtros
    cnae_code: Optional[str] = Query(None),
    tax_regime: Optional[str] = Query(None, regex="^(simples|lucro_presumido|lucro_real|mei)$"),
    entity_type: Optional[str] = Query(None, regex="^(pj|mei|autônomo)$"),
    created_after: Optional[date] = Query(None),
    created_before: Optional[date] = Query(None),
    # Paginação
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
) -> PaginatedResponse[ClientResponse]:
    """
    Lista clientes com filtros avançados e paginação.
    
    Exemplos:
    GET /clients?tax_regime=simples&entity_type=mei
    GET /clients?cnae_code=6201-5&created_after=2024-01-01
    GET /clients?search=João&status=active&limit=20&skip=0
    """
    stmt = select(AccountingClient).where(
        AccountingClient.tenant_id == current_user.tenant_id
    )
    
    # Filtros
    if search:
        stmt = stmt.where(
            or_(
                AccountingClient.name.ilike(f"%{search}%"),
                AccountingClient.email.ilike(f"%{search}%")
            )
        )
    if status:
        stmt = stmt.where(AccountingClient.status == status)
    if cnae_code:
        stmt = stmt.where(AccountingClient.cnae_code.like(f"{cnae_code}%"))
    if tax_regime:
        stmt = stmt.where(AccountingClient.tax_regime == tax_regime)
    if entity_type:
        stmt = stmt.where(AccountingClient.entity_type == entity_type)
    if created_after:
        stmt = stmt.where(AccountingClient.created_at >= created_after)
    if created_before:
        stmt = stmt.where(AccountingClient.created_at <= created_before)
    
    # Paginação
    total = await session.scalar(select(func.count()).select_from(stmt.alias()))
    results = await session.scalars(stmt.offset(skip).limit(limit))
    
    return PaginatedResponse(
        items=[ClientResponse.from_orm(r) for r in results],
        total=total,
        skip=skip,
        limit=limit
    )
```

#### 3. Migração Alembic

```python
# alembic/versions/2026_05_22_add_advanced_client_filters.py

def upgrade():
    op.add_column('accounting_clients', sa.Column('cnae_code', sa.String(20), nullable=True))
    op.add_column('accounting_clients', sa.Column('tax_regime', sa.String(50), nullable=True))
    op.add_column('accounting_clients', sa.Column('entity_type', sa.String(50), nullable=True))
    
    op.create_index('ix_accounting_clients_cnae_code', 'accounting_clients', ['cnae_code'])
    op.create_index('ix_accounting_clients_tax_regime', 'accounting_clients', ['tax_regime'])
    op.create_index('ix_accounting_clients_entity_type', 'accounting_clients', ['entity_type'])

def downgrade():
    op.drop_index('ix_accounting_clients_entity_type', table_name='accounting_clients')
    op.drop_index('ix_accounting_clients_tax_regime', table_name='accounting_clients')
    op.drop_index('ix_accounting_clients_cnae_code', table_name='accounting_clients')
    op.drop_column('accounting_clients', 'entity_type')
    op.drop_column('accounting_clients', 'tax_regime')
    op.drop_column('accounting_clients', 'cnae_code')
```

**Tempo Estimado:** 2 dias  
**Risco:** Baixo (apenas SELECT queries, sem lógica complexa)

---

## 🎯 Feature #2: Automated Billing (Honorários Mensais)

**Objetivo:** Gerar automaticamente faturas/cobrança de honorários mensais para cada cliente, com opção de cobrança automática.

**Status Atual:**
- ✅ Tabela `AccountReceivable` JÁ EXISTE com campos: `client_id`, `description`, `amount`, `due_date`, `status`, `paid_at`, `notes`
- ✅ Schema de pagamentos está funcional
- ❌ Faltam: `monthly_fee` no cliente, endpoint de geração, automação

### Mudanças Necessárias

#### 1. Modelo — Adicionar Campo ao Cliente

```python
class AccountingClient(Base):
    __tablename__ = "accounting_clients"
    
    # ... campos existentes ...
    
    # 🆕 NOVO CAMPO
    monthly_fee: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), 
        nullable=True,
        comment="Taxa mensal de honorários em R$"
    )
    billing_day: Mapped[int] = mapped_column(
        default=1,
        comment="Dia do mês para gerar cobrança (1-28)"
    )
    auto_billing_enabled: Mapped[bool] = mapped_column(
        default=False,
        comment="Se True, tenta cobrar automaticamente (requer integração Stripe/Asaas)"
    )
```

#### 2. Novo Endpoint — Gerar Cobranças Mensais

```python
@router.post("/receivables/generate-monthly")
async def generate_monthly_billings(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    year_month: str = Query(..., regex="^\d{4}-\d{2}$"),  # "2026-05"
) -> dict:
    """
    Gera automaticamente faturas de honorários para TODOS os clientes
    que têm monthly_fee configurado.
    
    Endpoint idempotente — se já existe fatura para esse mês/cliente, 
    não gera duplicata.
    
    Exemplo:
    POST /receivables/generate-monthly?year_month=2026-05
    """
    year, month = map(int, year_month.split('-'))
    billing_date = date(year, month, 1)
    
    # Buscar todos os clientes com monthly_fee > 0
    stmt = select(AccountingClient).where(
        and_(
            AccountingClient.tenant_id == current_user.tenant_id,
            AccountingClient.monthly_fee > 0,
            AccountingClient.status == 'active'
        )
    )
    clients = await session.scalars(stmt)
    
    created_count = 0
    skipped_count = 0
    
    for client in clients:
        # Checar se já existe fatura para este mês
        existing = await session.scalar(
            select(AccountReceivable).where(
                and_(
                    AccountReceivable.client_id == client.id,
                    AccountReceivable.description.like(f"Honorários - {year_month}%")
                )
            )
        )
        
        if existing:
            skipped_count += 1
            continue
        
        # Calcular vencimento (billing_day do cliente)
        due_day = min(client.billing_day, calendar.monthrange(year, month)[1])
        due_date = date(year, month, due_day)
        
        # Criar novo AccountReceivable
        receivable = AccountReceivable(
            client_id=client.id,
            description=f"Honorários - {year_month}",
            amount=client.monthly_fee,
            due_date=due_date,
            status="pending",
            created_at=datetime.now(timezone.utc)
        )
        session.add(receivable)
        created_count += 1
    
    await session.commit()
    
    return {
        "status": "success",
        "year_month": year_month,
        "created": created_count,
        "skipped_duplicates": skipped_count,
        "message": f"Geradas {created_count} faturas de honorários"
    }
```

#### 3. Background Task (Cron) — Executar Automaticamente

```python
# backend/app/core/scheduler.py (novo arquivo)

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timezone

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('cron', day=1, hour=2, minute=0)
async def auto_generate_monthly_billing():
    """
    Executa todo dia 1º do mês às 2:00 AM.
    Gera faturas de honorários para todos os tenants.
    """
    async with get_session() as session:
        year_month = datetime.now(timezone.utc).strftime("%Y-%m")
        
        # Para cada tenant
        tenants = await session.scalars(select(Tenant))
        for tenant in tenants:
            try:
                await generate_monthly_billings(
                    session=session,
                    tenant_id=tenant.id,
                    year_month=year_month
                )
                logger.info(f"Billing gerado para tenant {tenant.id}, {year_month}")
            except Exception as e:
                logger.error(f"Erro ao gerar billing para {tenant.id}: {str(e)}")

# No main.py
scheduler.start()
```

#### 4. Migração Alembic

```python
def upgrade():
    op.add_column('accounting_clients', 
                  sa.Column('monthly_fee', sa.Numeric(10, 2), nullable=True))
    op.add_column('accounting_clients', 
                  sa.Column('billing_day', sa.Integer(), default=1))
    op.add_column('accounting_clients', 
                  sa.Column('auto_billing_enabled', sa.Boolean(), default=False))

def downgrade():
    op.drop_column('accounting_clients', 'auto_billing_enabled')
    op.drop_column('accounting_clients', 'billing_day')
    op.drop_column('accounting_clients', 'monthly_fee')
```

**Tempo Estimado:** 1.5 dias  
**Risco:** Baixo-Médio (tabela já existe, apenas adiciona campos e endpoint)  
**⚠️ Nota:** Integração com Stripe/Asaas para cobrança automática é separada (+5 dias)

---

## 🎯 Feature #3: File Upload + Parsing (Client Secrets)

**Objetivo:** Permitir que contadores façam upload de arquivos (PDF, Excel, Word) com dados de clientes (CPF, senhas, certificados, etc.) e o sistema parse automaticamente.

**Status Atual:**
- ✅ Upload para Supabase Storage JÁ FUNCIONA (`documents` bucket)
- ✅ Tabela `ClientDocument` existe
- ❌ Faltam: libraries de parsing, lógica de processamento, schema de dados parseados

### Mudanças Necessárias

#### 1. Modelo — Adicionar Campos de Parsing

```python
class ClientDocument(Base):
    __tablename__ = "client_documents"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("accounting_clients.id"))
    document_type: Mapped[str]  # "contract", "secret_sheet", "certificate", etc
    file_name: Mapped[str]
    file_url: Mapped[str]  # URL do Supabase Storage
    
    # ✅ JÁ EXISTEM
    uploaded_at: Mapped[datetime]
    
    # 🆕 NOVOS CAMPOS
    parse_status: Mapped[str] = mapped_column(
        default="pending",  # pending, processing, completed, failed
    )
    parsed_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Dados extraídos do arquivo em JSON"
    )
    parse_error: Mapped[Optional[str]] = mapped_column(
        nullable=True,
        comment="Mensagem de erro se parsing falhou"
    )
    parsed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
```

#### 2. DTO para Template de Upload

```python
# backend/app/schemas/documents.py

from pydantic import BaseModel, Field
from enum import Enum

class SecretSheetTemplate(BaseModel):
    """
    Template que o cliente preenchee para enviar dados de Secrets.
    Pode ser em Excel, PDF, ou até JSON.
    """
    cpf: Optional[str] = Field(None, description="CPF do titular")
    email: Optional[str] = Field(None, description="Email corporativo")
    password: Optional[str] = Field(None, description="Senha (criptografada)")
    banking_account: Optional[str] = Field(None, description="Agência e Conta")
    banking_password: Optional[str] = Field(None, description="Senha do banco")
    digital_certificate_path: Optional[str] = Field(None, description="Caminho do certificado")
    digital_certificate_password: Optional[str] = Field(None, description="Senha do certificado")
    signer_name: Optional[str] = Field(None, description="Nome do assinante")
    phone: Optional[str] = Field(None, description="Telefone")
    notes: Optional[str] = Field(None, description="Observações")

class DocumentUploadRequest(BaseModel):
    document_type: str = Field(..., regex="^(contract|secret_sheet|certificate|other)$")
    file_name: str

class DocumentResponse(BaseModel):
    id: int
    client_id: int
    document_type: str
    file_name: str
    parse_status: str  # pending, processing, completed, failed
    parsed_data: Optional[dict]
    parse_error: Optional[str]
    uploaded_at: datetime
    parsed_at: Optional[datetime]
```

#### 3. Endpoint de Upload

```python
# backend/app/api/v1/endpoints/documents.py

@router.post("/clients/{client_id}/documents")
async def upload_client_document(
    client_id: int,
    file: UploadFile = File(...),
    document_type: str = Query(..., regex="^(contract|secret_sheet|certificate|other)$"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = None,
) -> DocumentResponse:
    """
    Upload de arquivo para cliente específico.
    Arquivo é armazenado no Supabase Storage.
    Parsing acontece em background (assíncrono).
    """
    # Validar cliente pertence ao tenant
    client = await session.get(AccountingClient, client_id)
    if not client or client.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Cliente não encontrado")
    
    # Upload para Supabase Storage
    file_ext = Path(file.filename).suffix
    storage_path = f"{current_user.tenant_id}/{uuid4()}{file_ext}"
    
    file_content = await file.read()
    supabase.storage.from_("documents").upload(storage_path, file_content)
    
    file_url = f"https://{SUPABASE_URL}/storage/v1/object/public/documents/{storage_path}"
    
    # Criar registro no banco (parse_status = "pending")
    document = ClientDocument(
        client_id=client_id,
        document_type=document_type,
        file_name=file.filename,
        file_url=file_url,
        parse_status="pending",
        uploaded_at=datetime.now(timezone.utc)
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)
    
    # Agendar parsing em background
    if background_tasks:
        background_tasks.add_task(
            parse_document_async,
            document_id=document.id,
            file_path=storage_path,
            document_type=document_type
        )
    
    return DocumentResponse.from_orm(document)


@router.get("/clients/{client_id}/documents")
async def list_client_documents(
    client_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> List[DocumentResponse]:
    """Lista todos os documentos/secrets de um cliente."""
    stmt = select(ClientDocument).where(
        ClientDocument.client_id == client_id
    )
    documents = await session.scalars(stmt)
    return [DocumentResponse.from_orm(d) for d in documents]
```

#### 4. Lógica de Parsing (Background Task)

```python
# backend/app/services/document_parser.py

import openpyxl
import pdfplumber
from docx import Document as DocxDocument

async def parse_document_async(
    document_id: int,
    file_path: str,
    document_type: str,
    session: AsyncSession
):
    """
    Executa em background. Parse automático de arquivo.
    Suporta: PDF, Excel (.xlsx), Word (.docx)
    """
    try:
        # Marcar como "processing"
        doc = await session.get(ClientDocument, document_id)
        doc.parse_status = "processing"
        await session.commit()
        
        # Download arquivo do Supabase
        file_content = supabase.storage.from_("documents").download(file_path)
        temp_file = f"/tmp/{document_id}_{file_path.split('/')[-1]}"
        
        with open(temp_file, 'wb') as f:
            f.write(file_content)
        
        # Parse conforme tipo
        parsed_data = {}
        
        if file_path.endswith('.xlsx'):
            parsed_data = parse_excel(temp_file, document_type)
        elif file_path.endswith('.pdf'):
            parsed_data = parse_pdf(temp_file, document_type)
        elif file_path.endswith('.docx'):
            parsed_data = parse_docx(temp_file, document_type)
        
        # Salvar resultado
        doc.parsed_data = parsed_data
        doc.parse_status = "completed"
        doc.parsed_at = datetime.now(timezone.utc)
        await session.commit()
        
        logger.info(f"Document {document_id} parsed successfully")
        
    except Exception as e:
        doc.parse_status = "failed"
        doc.parse_error = str(e)
        await session.commit()
        logger.error(f"Error parsing document {document_id}: {str(e)}")

def parse_excel(file_path: str, document_type: str) -> dict:
    """Parse arquivo Excel."""
    wb = openpyxl.load_workbook(file_path)
    ws = wb.active
    
    parsed = {}
    for row in ws.iter_rows(values_only=True):
        if row[0] and row[1]:  # key: value
            parsed[str(row[0]).lower().replace(" ", "_")] = row[1]
    
    return parsed

def parse_pdf(file_path: str, document_type: str) -> dict:
    """Parse arquivo PDF (extrai texto)."""
    parsed = {"text_content": ""}
    
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            parsed["text_content"] += page.extract_text() + "\n"
    
    # Se é "secret_sheet", tentar extrair pares key:value
    if document_type == "secret_sheet":
        parsed = extract_key_value_pairs(parsed["text_content"])
    
    return parsed

def parse_docx(file_path: str, document_type: str) -> dict:
    """Parse arquivo Word."""
    doc = DocxDocument(file_path)
    parsed = {"text_content": ""}
    
    for para in doc.paragraphs:
        parsed["text_content"] += para.text + "\n"
    
    if document_type == "secret_sheet":
        parsed = extract_key_value_pairs(parsed["text_content"])
    
    return parsed

def extract_key_value_pairs(text: str) -> dict:
    """Extrai pares key: value de texto livre."""
    result = {}
    for line in text.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            result[key.strip().lower()] = value.strip()
    return result
```

#### 5. Migração Alembic

```python
def upgrade():
    op.add_column('client_documents',
                  sa.Column('parse_status', sa.String(50), default='pending'))
    op.add_column('client_documents',
                  sa.Column('parsed_data', postgresql.JSON, nullable=True))
    op.add_column('client_documents',
                  sa.Column('parse_error', sa.Text, nullable=True))
    op.add_column('client_documents',
                  sa.Column('parsed_at', sa.DateTime, nullable=True))

def downgrade():
    op.drop_column('client_documents', 'parsed_at')
    op.drop_column('client_documents', 'parse_error')
    op.drop_column('client_documents', 'parsed_data')
    op.drop_column('client_documents', 'parse_status')
```

#### 6. Dependencies (requirements.txt)

```
openpyxl>=3.10.0      # Excel parsing
pdfplumber>=0.9.0     # PDF extraction
python-docx>=0.8.11   # Word document parsing
```

**Tempo Estimado:** 4.5 dias  
**Risco:** Médio (envolve I/O, parsing, background tasks)  
**⚠️ Nota:** Parsing de PDF complexos (tabelas) pode requerer `tabula-py` ou `PyPDF2` (+1 dia)

---

## 🎯 Feature #4: Client Portal (Nova Role)

**Objetivo:** Criar novo role `CLIENT` que permite que clientes (não-countadores) acessem o portal para ver seus dados, documentos e honorários.

**Status Atual:**
- ❌ Role `CLIENT` não existe no `UserRole` enum
- ❌ Nenhuma filtragem por role (tudo é PUBLIC uma vez autenticado)
- ❌ Nenhuma interface de cliente

### Mudanças Necessárias

#### 1. Modelo — Adicionar Role CLIENT

```python
# backend/app/models/user.py

class UserRole(str, Enum):
    OWNER = "owner"          # Dono do escritório (admin total)
    ADMIN = "admin"          # Admin do escritório
    MEMBER = "member"        # Contador/auxiliar do escritório
    CLIENT = "client"        # 🆕 NOVO: Cliente do escritório
```

#### 2. Modelo — Linkar Cliente a Usuário Portal

```python
class AccountingClient(Base):
    __tablename__ = "accounting_clients"
    
    # ... campos existentes ...
    
    # 🆕 NOVO
    portal_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
        comment="Usuário do portal do cliente (role=CLIENT)"
    )
```

#### 3. Dependency — Autorização por Role

```python
# backend/app/core/deps.py

def require_role(*allowed_roles: UserRole):
    """
    Dependency que verifica se usuário tem uma das roles permitidas.
    
    Uso:
    @router.get("/admin-only")
    async def admin_endpoint(current_user: User = Depends(require_role(UserRole.ADMIN))):
        ...
    """
    async def check_role(
        current_user: User = Depends(get_current_user)
    ) -> User:
        if UserRole(current_user.role) not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Role {current_user.role} não permitido. Roles aceitas: {allowed_roles}"
            )
        return current_user
    
    return check_role
```

#### 4. Endpoint — Invite Cliente para Portal

```python
@router.post("/clients/{client_id}/invite-portal")
async def invite_client_to_portal(
    client_id: int,
    email: str = Query(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(UserRole.OWNER, UserRole.ADMIN)),
) -> dict:
    """
    Cria usuário CLIENT e envia email de convite.
    
    POST /clients/123/invite-portal?email=cliente@example.com
    """
    # Validar cliente
    client = await session.get(AccountingClient, client_id)
    if not client or client.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # Criar usuário CLIENT
    temp_password = generate_random_password(16)
    portal_user = User(
        email=email,
        tenant_id=current_user.tenant_id,
        role=UserRole.CLIENT,
        hashed_password=hash_password(temp_password),
        is_active=True
    )
    session.add(portal_user)
    await session.commit()
    await session.refresh(portal_user)
    
    # Linkar ao cliente
    client.portal_user_id = portal_user.id
    await session.commit()
    
    # Enviar email (usar Resend/SendGrid)
    await send_email(
        to=email,
        subject=f"Acesso ao Portal de Clientes — {client.name}",
        template="client_invite",
        context={
            "client_name": client.name,
            "email": email,
            "temp_password": temp_password,
            "login_url": "https://fiscwise.com.br/login"
        }
    )
    
    return {
        "status": "success",
        "user_id": portal_user.id,
        "message": f"Email de convite enviado para {email}"
    }
```

#### 5. Filtros de Autorização — Exemplos

```python
# Endpoint que TODOS podem acessar (com filtro por role)
@router.get("/me/dashboard")
async def my_dashboard(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Dashboard diferente conforme role:
    - OWNER/ADMIN/MEMBER: vêem clientes e dados da empresa
    - CLIENT: vêem apenas seus próprios dados
    """
    role = UserRole(current_user.role)
    
    if role == UserRole.CLIENT:
        # Client vê apenas seus dados
        client = await session.scalar(
            select(AccountingClient).where(
                AccountingClient.portal_user_id == current_user.id
            )
        )
        if not client:
            raise HTTPException(status_code=404, detail="Dados do cliente não encontrados")
        
        return {
            "type": "client",
            "name": client.name,
            "receivables": await get_client_receivables(client.id, session),
            "documents": await get_client_documents(client.id, session),
        }
    else:
        # OWNER/ADMIN/MEMBER vêem tudo da empresa
        return {
            "type": "company",
            "total_clients": await count_clients(current_user.tenant_id, session),
            "total_receivables": await sum_receivables(current_user.tenant_id, session),
            # ... mais dados ...
        }


# Endpoint CLIENT-only
@router.get("/me/receivables")
async def my_receivables(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(UserRole.CLIENT)),
) -> List[ReceivableResponse]:
    """
    Cliente vê apenas seus próprios honorários.
    """
    client = await session.scalar(
        select(AccountingClient).where(
            AccountingClient.portal_user_id == current_user.id
        )
    )
    
    receivables = await session.scalars(
        select(AccountReceivable).where(
            AccountReceivable.client_id == client.id
        )
    )
    return [ReceivableResponse.from_orm(r) for r in receivables]


# Endpoint ADMIN-only
@router.post("/clients/{client_id}/disable-portal")
async def disable_client_portal(
    client_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_role(UserRole.OWNER, UserRole.ADMIN)),
) -> dict:
    """
    Desativa acesso do cliente ao portal.
    """
    client = await session.get(AccountingClient, client_id)
    if client.portal_user_id:
        portal_user = await session.get(User, client.portal_user_id)
        portal_user.is_active = False
        await session.commit()
    
    return {"status": "success"}
```

#### 6. Migração Alembic

```python
def upgrade():
    op.add_column('accounting_clients',
                  sa.Column('portal_user_id', sa.Integer, 
                           sa.ForeignKey('users.id'), nullable=True))
    op.create_index('ix_accounting_clients_portal_user_id',
                   'accounting_clients', ['portal_user_id'])

def downgrade():
    op.drop_index('ix_accounting_clients_portal_user_id')
    op.drop_column('accounting_clients', 'portal_user_id')
```

**Tempo Estimado:** 4.5 dias  
**Risco:** Alto (envolve novo modelo de autorização, fluxo de convite, UI cliente)

---

## 📊 Resumo de Complexidade & Dependências

```
Feature #1 (Filters) — 2 dias
  └─ Independente ✓
  └─ Pode começar AGORA

Feature #2 (Billing) — 1.5 dias
  └─ Depende de: Schema cliente (monthly_fee, billing_day)
  └─ Pode começar DEPOIS da #1 ou PARALELO

Feature #3 (File Parsing) — 4.5 dias
  └─ Independente ✓
  └─ Pode começar PARALELO com #1 e #2

Feature #4 (Client Portal) — 4.5 dias
  └─ Depende de: Implementação de novo role (pode ser feita primeiro)
  └─ Depende de: Frontend portal (não coberto neste plano)
  └─ ⚠️ Deixar para o final
```

---

## 🗓️ Cronograma Recomendado

### **Sprint 1 — Semana 1 (Advanced Filters + Início Billing)**
- [ ] Dia 1-2: Implementar Feature #1 (Filters)
- [ ] Dia 2-3: Implementar Feature #2 (Billing Schema + Endpoint)
- [ ] Dia 4-5: Testes + Code Review

### **Sprint 2 — Semana 2 (File Parsing + Client Portal Schema)**
- [ ] Dia 1-2: Implementar Feature #3 (Upload + Parsing)
- [ ] Dia 3-5: Implementar Feature #4 Backend (role, autorização)
- [ ] Dia 5: Testes + Integração

### **Sprint 3 — Semana 3 (Portal Frontend + Ajustes)**
- [ ] Frontend: Interface do portal cliente (FORA do escopo deste plano)
- [ ] Testes E2E
- [ ] Deploy

---

## ⚠️ Questões Abertas / Decisões Necessárias

1. **Cobrança Automática (Feature #2)**
   - Integrar com Stripe/Asaas para cobrança automática?
   - Ou apenas gerar faturas (cliente paga manualmente)?
   - **Decisão necessária antes de implementar Feature #2**

2. **Frontend do Cliente Portal (Feature #4)**
   - Será desenvolvido junto com backend ou depois?
   - Qual rota? `/client/` ou `/portal/`?
   - **Decisão necessária antes de começar Feature #4**

3. **Migrations Alembic**
   - Estão sincronizadas com schema atual?
   - Há migrations pendentes?
   - **Validar com: `alembic current`**

4. **Email Service (Feature #4)**
   - Qual provider usar para enviar convites? (Resend, SendGrid, etc.)
   - Templates prontos?
   - **Decidir antes de implementar invites**

---

## ✅ Checklist Pré-Implementação

- [ ] Todas as 4 features foram discutidas com stakeholders
- [ ] Prioridade de implementação foi confirmada
- [ ] Dependências externas (libs Python) foram validadas
- [ ] Decisões comerciais foram tomadas (cobrança automática? email provider?)
- [ ] BD: migrations estão sincronizadas
- [ ] Testes unitários estarão prontos para cada feature
- [ ] Code review será feito antes de merge
- [ ] Deploy será feito em staging antes de produção

---

**Documento preparado para alinhamento da equipe de backend.**  
**Próximo passo: Aprovação de scope e início de Sprint 1.**
