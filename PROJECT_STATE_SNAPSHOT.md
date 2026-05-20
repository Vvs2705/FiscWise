# CTFlow / Contabilidade Flow - Project State Snapshot

**Data:** 20/05/2026 (Commit: 875dc79)  
**Status:** MVP OPERACIONAL COMPLETO - PRONTO PARA VALIDAÇÃO LOCAL  
**Objetivo:** SaaS MVP para contadores (10 pilotos) — resolva esquecimento de prazos, multas, documentos espalhados, certificados vencendo, controle financeiro.

---

## O Que Foi Completado Nesta Rodada

### ✅ Fase 0 - Validação Técnica
- Backend compile check: sem erros de import, sintaxe, Alembic
- Segurança review: tenant isolation aprovado em 100% das rotas
- Frontend type-check: zero TypeScript errors, build limpa

### ✅ Fase 1 - Backend MVP Completo

**Endpoints operacionais (5 entidades):**

| Entidade | GET /list | POST /create | GET /{id} | PATCH /update | DELETE /soft |
|----------|-----------|--------------|-----------|---------------|--------------|
| Clients | ✅ | ✅ | ✅ | ✅ | ✅ (status=inactive) |
| Deadlines | ✅ | ✅ | ✅ | ✅ | ✅ |
| Documents | ✅ | ✅ | ✅ | ✅ | ✅ |
| Certificates | ✅ | ✅ | ✅ | ✅ | ✅ |
| Receivables | ✅ | ✅ | ✅ | ✅ | ✅ |

**Modelos (SQLAlchemy + Alembic):**
- `AccountingClient` — nome, CPF/CNPJ, tipo, regime, email, telefone, status
- `DeadlineItem` — tipo, prazo, cliente, status, completed_at automático
- `ClientDocument` — tipo, URL, emissão, vencimento
- `DigitalCertificate` — n_série, tipo (A1/A3/NF-e), vencimento, status automático
- `AccountReceivable` — valor, vencimento, status (pending/paid), paid_at automático

**Schemas Pydantic:**
- Validação de campos obrigatórios (nome, tipo, etc)
- Validators para CPF/CNPJ, datas, enums
- Response models com isolamento de tenant garantido

**Isolamento por tenant:**
- Todas as queries: `WHERE tenant_id = ?`
- `_get_client_or_404()` e `_get_item_or_404()` validam (tenant_id, user_id)
- Soft-delete: `status = "inactive"` (não mostra em listagens)
- Testes: 2 testes específicos de cross-tenant prevention ✅

**Migrations:**
- `20260520_foundation_user_constraints.py` — restrições de usuário
- `20260520_operational_mvp.py` — 5 tabelas + índices + FKs
- Reversíveis (downgrade dropa em ordem correta)

### ✅ Fase 2 - Frontend MVP Completo

**Páginas operacionais (todas com API real):**
- **ClientsPage** — tabela (nome, CNPJ, tipo, regime, email), form cadastro, delete com confirmação
- **DeadlinesPage** — cards com prioridade (urgencyVariant), form, status toggling
- **DocumentsPage** — tabela com link para arquivo, form com URL, datas
- **CertificatesPage** — cards com dias restantes (urgencyVariant automático), form A1/A3/NF-e
- **FinancePage** — tabela de recebiveis com ação "marcar como pago", totais calculados

**Componentes UI criados:**
- `Dialog.tsx` — modal acessível com backdrop + Escape
- `FormField.tsx` — wrapper label + erro + obrigatoriedade
- `Select.tsx` — select estilizado Tailwind
- `StateViews.tsx` — LoadingRows, LoadingCards, EmptyState, ErrorState, PageSpinner

**Hook `useOperations.ts`:**
- `useCreateMutation()` — POST com loading/error states
- `useUpdateMutation()` — PATCH com auto-refetch
- `useDeleteMutation()` — DELETE com confirmação
- Exporta hooks específicos: `useCreateClient`, `useUpdateDeadline`, `useDeleteCertificate`, etc

**Build:**
- `npm run type-check`: zero erros
- `npm run build`: 432 kB JS / 130 kB gzip
- SPA responsiva (Tailwind CSS)

### ✅ Testing - 34 Testes CRUD

**Testes implementados (`backend/tests/test_operations_crud.py`):**

| Classe | Testes | Coverage |
|--------|--------|----------|
| TestClientsCRUD | 12 | Create (validação, duplicata), Read (list/id, isolamento), Update, Delete soft |
| TestDeadlinesCRUD | 6 | Create (validação), List (filtro), Status (automático completed_at) |
| TestDocumentsCRUD | 4 | CRUD básico + referência a cliente |
| TestCertificatesCRUD | 4 | CRUD + validação de data |
| TestReceivablesCRUD | 6 | CRUD + status automation (paid_at) |
| TestTenantIsolation | 2 | **Cross-tenant read/update prevention** |

**Fixtures (`conftest.py`):**
- `test_db` — in-memory SQLite per test
- `tenant_a, tenant_b` — 2 tenants isolados
- `user_a, user_b` — 2 usuários autenticados
- `client_a, client_b` — clientes de cada tenant
- JWT mock para autenticação

### ✅ Segurança - Code Review

**Aprovado:**
- ✅ Tenant isolation (WHERE tenant_id em 100% das queries)
- ✅ 100% SQLAlchemy ORM (zero raw SQL)
- ✅ Validação Pydantic (enums, ranges, tipos)
- ✅ JWT validation + CORS seguro
- ✅ Bcrypt 72-byte limit

**Nota:**
- `.env` **nunca foi commitado** (já em .gitignore desde origem)
- Nenhum secret no repo

---

## Estado Atual do Git

```
commit 875dc79
Author: Vvs2705
Date: 2026-05-20

feat: complete CTFlow MVP operational phase (Phase 0-2)
- 47 files changed
- 4594 insertions
- 659 deletions
```

**Branch:** main  
**Alterações não staged:** NENHUMA (tudo commitado)

---

## Próxima Etapa: Fase 3 - Validação Local

### 3a. Setup do ambiente

```bash
# Backend
cd backend
python -m pip install -r requirements.txt
python -m alembic upgrade head  # Apply migrations
python -m pytest  # Run 34 tests

# Frontend
cd ../frontend
npm install
npm run build
npm run dev  # Local dev server em http://localhost:3000
```

### 3b. Validação de funcionalidade

1. **Registrar usuário piloto:**
   - POST `/api/v1/auth/register` (email, senha, tenant name)
   - Confirmar JWT retornado

2. **Login:**
   - POST `/api/v1/auth/login`
   - Validar JWT + X-Tenant-ID header

3. **CRUD Clientes:**
   - POST `/api/v1/clients` (criar cliente teste)
   - GET `/api/v1/clients` (listar)
   - GET `/api/v1/clients/{id}` (buscar por ID)
   - PATCH `/api/v1/clients/{id}` (atualizar)
   - DELETE `/api/v1/clients/{id}` (soft-delete)

4. **Dashboard (dados reais):**
   - GET `/api/v1/dashboard/overview` (deve retornar contadores: clientes, prazos, certificados vencendo, recebiveis)
   - Frontend exibe em `DashboardPage`

5. **Tenant isolation test:**
   - Registrar user_a e user_b
   - User A cria cliente_a
   - User B tenta GET cliente_a com X-Tenant-ID=tenant_b → 404 ✅

### 3c. Validação de segurança

- [ ] JWT não consegue acessar endpoints sem X-Tenant-ID (501 Unavailable ou 401)
- [ ] Cliente de tenant B não aparece em GET /clients de tenant A
- [ ] Soft-delete não mostra clientes inativados
- [ ] Migrations reversíveis (test com downgrade)

---

## Fase 4 - Antes do Deploy

1. **Lint/Format:** `black .`, `ruff check`
2. **Documentação:** README.md com setup local
3. **Environment:** Criar `.env.example` (sem secrets)
4. **CI/CD:** Validar que Railway roda `alembic upgrade head` antes de uvicorn

---

## Fase 5 - Deploy para Railway

1. **Backend:** Push para Railway, validar:
   - `/api/v1/health` → 200
   - `/api/v1/ready` (com tenant header válido) → 200
   - Migrations rodaram (check `_prisma_migrations`)

2. **Frontend:** Deploy Vercel com `VITE_API_URL=https://api.contabilidadeflow.com.br`

3. **Teste em produção:**
   - Registrar user piloto
   - Criar client/deadline/documento/certificado
   - Validar dashboard com dados reais
   - Verificar email (quando automação de notificação for adicionada)

---

## Riscos Residuais

- Migrations ainda não foram testadas contra DB real (Railway)
- Cofre de senhas NÃO foi implementado propositalmente (precisa criptografia + auditoria)
- Notificações de prazos ainda não implementadas (próxima fase)
- Integração com APIs de certificados (e-sign, ICP-Brasil) ainda não existe

---

## Diretriz Para Próxima Retomada

**Começar por:**

```bash
cd backend
python -m pip install -r requirements.txt
python -m pytest  # Confirm all 34 tests pass

cd ../frontend
npm run build  # Confirm zero errors
npm run dev    # Test UI locally against http://localhost:8000
```

Depois: Fase 3 (validação local) → Fase 4 (revisão final) → Fase 5 (deploy)
