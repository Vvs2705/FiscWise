# CTFlow / Contabilidade Flow - Project State Snapshot

**Data:** 20/05/2026  
**Status:** PAUSADO POR SOLICITACAO DO USUARIO  
**Objetivo atual:** transformar o antigo ContaFlow em um MVP SaaS operacional para contadores autonomos e pequenos escritorios, pronto para piloto com 10 contadores.

---

## Decisao de Produto Atual

O projeto deixou de ter como foco principal RAG/chatbot generico e passou a seguir a tese de produto **CTFlow / Contabilidade Flow**:

- Sistema unico para o contador gerenciar carteira de clientes.
- Controle de prazos fiscais, documentos, certificados digitais e honorarios.
- IA deve ser camada assistiva futura, nao o nucleo inicial do MVP.
- O MVP precisa resolver primeiro o problema validado com contadores: esquecimento de prazos, multa, documentos espalhados, certificados vencendo e controle financeiro manual.

---

## O Que Foi Feito Nesta Rodada

### 1. Orquestracao multiagente

- Foram acionados agentes em paralelo conforme pedido do usuario.
- `test-writer` finalizou a frente de testes backend.
- `frontend-developer` estava rodando e foi interrompido/fechado quando o usuario pediu pausa.
- Nenhum novo agente esta ativo neste momento.

### 2. Backend - base de seguranca e producao

Arquivos alterados:

- `backend/Dockerfile`
- `backend/app/core/middleware.py`
- `backend/app/core/deps.py`
- `backend/app/core/security.py`
- `backend/app/api/v1/endpoints/health.py`
- `backend/app/api/v1/endpoints/onboarding.py`
- `backend/app/models/user.py`
- `backend/app/models/tenant.py`
- `backend/app/schemas/user.py`
- `backend/app/schemas/tenant.py`
- `backend/app/schemas/onboarding.py`

Mudancas feitas:

- Removido `--reload` do Dockerfile de producao.
- Corrigido middleware multi-tenant: a rota `/` nao faz mais todas as rotas ficarem publicas por acidente.
- `X-Tenant-ID` agora precisa ser UUID valido em rotas protegidas.
- `get_current_user` agora valida se tenant do header bate com tenant do JWT/usuario.
- `health readiness` agora retorna 503 quando banco falha.
- `onboarding` agora tem logger definido e trata `IntegrityError`.
- `User.full_name` foi adicionado ao modelo.
- `Tenant.document` passou para 32 caracteres.
- Senhas maiores que 72 bytes sao rejeitadas antes do bcrypt para evitar truncamento silencioso.
- JWT usa horario timezone-aware.

### 3. Backend - nucleo MVP operacional criado

Arquivos novos:

- `backend/app/models/operations.py`
- `backend/app/schemas/operations.py`
- `backend/app/api/v1/endpoints/operations.py`
- `backend/alembic/versions/20260520_foundation_user_constraints.py`
- `backend/alembic/versions/20260520_operational_mvp.py`

Rotas novas planejadas/implementadas:

- `GET /api/v1/dashboard/overview`
- `GET/POST/PATCH/DELETE /api/v1/clients`
- `GET/POST/PATCH /api/v1/deadlines`
- `GET/POST/PATCH /api/v1/documents`
- `GET/POST/PATCH /api/v1/certificates`
- `GET/POST/PATCH /api/v1/receivables`

Entidades novas:

- `AccountingClient`
- `DeadlineItem`
- `ClientDocument`
- `DigitalCertificate`
- `AccountReceivable`

Observacao: o cofre de senhas ainda nao foi implementado de proposito. Ele exige criptografia, auditoria, permissao fina e politica de acesso antes de ser seguro para piloto.

### 4. Backend - testes adicionados pela frente de testes

Arquivos criados/alterados:

- `backend/tests/conftest.py`
- `backend/tests/test_health.py`
- `backend/tests/test_tenant_middleware.py`
- `backend/tests/unit/test_auth_tenant_isolation.py`

Cobertura adicionada:

- App importa corretamente.
- `/health` e `/api/v1/health` publicos.
- `/api/v1/ready` exige tenant header.
- UUID invalido em `X-Tenant-ID` retorna erro correto.
- Rotas de auth/onboarding seguem publicas.
- Unit test de mismatch entre tenant do header e tenant autenticado.

Validacao feita pelo agente:

- `py_compile` passou.
- `pytest` nao rodou no Python ativo porque faltava `fastapi` no ambiente local.

### 5. Frontend - base CTFlow operacional

Arquivos alterados/criados:

- `frontend/src/App.tsx`
- `frontend/src/components/Header.tsx`
- `frontend/src/components/Sidebar.tsx`
- `frontend/src/pages/BillingPage.tsx`
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/pages/SettingsPage.tsx`
- `frontend/src/pages/ClientsPage.tsx`
- `frontend/src/pages/DocumentsPage.tsx`
- `frontend/src/pages/DeadlinesPage.tsx`
- `frontend/src/pages/CertificatesPage.tsx`
- `frontend/src/pages/FinancePage.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/hooks/useOperations.ts`

Mudancas feitas:

- Navegacao alterada para CTFlow: Dashboard, Clientes, Documentos, Agenda e Prazos, Certificados, Financeiro, Configuracoes.
- Rotas novas adicionadas.
- `BillingPage` redireciona para Financeiro.
- `api.ts` usa `localhost:8000` em desenvolvimento e Railway em producao.
- `useOperations.ts` criado para consumir as novas rotas operacionais.
- `DashboardPage` comecou a ser trocada para dados reais da API.

Importante: a integracao frontend ainda ficou incompleta no momento da pausa.

---

## Estado Atual do Git

Ha alteracoes nao commitadas. Antes de continuar, revisar:

```bash
git status --short
```

Principais arquivos pendentes:

- Backend core, schemas, models e endpoints operacionais.
- Migrations Alembic novas.
- Testes backend novos.
- Telas frontend CTFlow novas.
- Hook frontend `useOperations.ts`.

---

## O Que Falta Fazer

### Fase 0 - Fechar base tecnica

- Rodar testes backend em ambiente com dependencias instaladas.
- Corrigir eventuais erros de import, tipagem ou Pydantic/SQLAlchemy.
- Validar migrations Alembic em banco limpo e em banco existente.
- Confirmar se a constraint `uq_users_tenant_email` nao quebra dados existentes.

### Fase 1 - Completar backend MVP

- Revisar endpoints operacionais criados.
- Adicionar testes de CRUD para clientes, prazos, documentos, certificados e recebiveis.
- Confirmar isolamento por tenant em todas as queries.
- Decidir se `DELETE /clients/{id}` deve ser soft delete definitivo ou apenas `inactive`.
- Adicionar seed opcional para demonstracao/piloto.

### Fase 2 - Completar frontend MVP

- Finalizar todas as paginas para usar API real, nao dados mockados.
- Criar formularios de cadastro para:
  - Cliente
  - Prazo
  - Documento
  - Certificado
  - Recebivel
- Adicionar estados de loading, vazio e erro.
- Corrigir textos com mojibake/acentuacao quebrada.
- Rodar `npm run type-check` e `npm run build`.

### Fase 3 - Validacao local

- Subir banco/API local ou Docker.
- Aplicar migrations.
- Registrar usuario teste.
- Criar cliente teste.
- Criar prazo, documento, certificado e recebivel.
- Validar dashboard com dados reais.
- Validar tenant isolation com dois usuarios/tenants.

### Fase 4 - Revisao final

- Rodar code review com agente/revisor.
- Revisar seguranca antes de deploy:
  - JWT
  - CORS
  - tenant isolation
  - armazenamento de documentos
  - ausencia de cofre de senhas inseguro
- Remover arquivos/stubs obsoletos do antigo RAG/chatbot, se ainda existirem.

### Fase 5 - Deploy

- Commitar e enviar para GitHub.
- Garantir que Railway rode `alembic upgrade head`.
- Validar backend em producao:
  - `/api/v1/health`
  - registro
  - login
  - dashboard overview
  - CRUD operacional basico
- Deploy Vercel com `VITE_API_URL` apontando para Railway ou dominio customizado.
- Testar fluxo completo em producao com usuario piloto.

---

## Riscos Atuais

- Frontend esta parcialmente integrado: algumas paginas ainda usam dados mockados.
- Backend operacional novo ainda nao foi testado em runtime.
- Migrations novas ainda nao foram aplicadas.
- Ambiente Python local ativo nao tinha dependencias para rodar pytest.
- Existem textos antigos com encoding quebrado em alguns arquivos.
- Cofre de senhas ainda nao deve ser vendido/ativado sem criptografia e auditoria.
- Deploy nao deve ser feito antes de build/testes passarem.

---

## Proximo Comando Recomendado Ao Retomar

```bash
git status --short
```

Depois:

```bash
cd backend
python -m pip install -r requirements.txt
python -m pytest
```

E no frontend:

```bash
cd frontend
npm install
npm run type-check
npm run build
```

---

## Diretriz Para Retomada

Ao retomar, continuar da integracao interrompida:

1. Fechar build/testes do backend.
2. Completar frontend usando `useOperations.ts`.
3. Validar localmente.
4. Fazer code review final.
5. So depois commit/push/deploy.

