# Auditoria Completa FiscWise

Este documento registra o diagnóstico detalhado de arquitetura, segurança, banco de dados, testes e infraestrutura do projeto FiscWise (Plataforma de Gestão Contábil SaaS).

---

## 1. Visão Geral Tecnológica

### Stack Real do Backend
- **Linguagem**: Python 3.14.4
- **Framework**: FastAPI (0.115.0)
- **ORM & Driver**: SQLAlchemy (2.0.49 async) + asyncpg
- **Validação de Entrada**: Pydantic v2 (pydantic>=2.9.2)
- **Migrações**: Alembic (1.13.3)
- **Banco de Dados**: PostgreSQL com pgvector (pgvector/pgvector:pg16 no Docker)
- **Cache/Mensageria**: Redis 7 (redis:7-alpine)
- **Segurança**: JWT (python-jose) + bcrypt para hashing de senhas

### Stack Real do Frontend
- **Framework Core**: React 18 (18.3.1)
- **Linguagem**: TypeScript 5.5 (TypeScript strict mode)
- **Build/Bundler**: Vite 6.4 (vite>=6.4.2)
- **Estilização**: Tailwind CSS v3
- **Roteamento**: React Router v6
- **Data Fetching/Cache**: TanStack Query v5 (React Query)
- **Formulários & Validação**: React Hook Form + Zod
- **Gráficos**: Recharts
- **Animações**: Framer Motion
- **Hospedagem**: Vercel

---

## 2. Diagnóstico de Arquitetura e Segurança

### [AUD-01] [Segurança Crítica] Brecha de Isolamento Multi-Tenant em Endpoints de Autenticação (/api/v1/auth)
- **Evidência**: `backend/app/core/middleware.py` (linhas 17-29).
- **Impacto**: O middleware `TenantMiddleware` incluía o prefixo `/api/v1/auth` na lista de rotas excluídas. Isso fazia com que qualquer endpoint protegido localizado sob `/auth` (como `/api/v1/auth/me`, `/api/v1/auth/tenant` e `/api/v1/auth/change-password`) bypassasse completamente a validação do cabeçalho `X-Tenant-ID`. Um usuário mal-intencionado com um JWT de um tenant A poderia acessar as informações do tenant B enviando o `X-Tenant-ID` do tenant B, pois o middleware não o rejeitava e o `get_current_user` não recebia o tenant a ser verificado no estado da requisição.
- **Correção Recomendada**: Remover `/api/v1/auth` dos prefixos excluídos globais e adicionar apenas os endpoints estritamente públicos (`/api/v1/auth/login`, `/api/v1/auth/google`, `/api/v1/auth/logout`) à lista de caminhos exatos excluídos (`_EXCLUDED_EXACT_PATHS`).

### [AUD-02] [Arquitetura] Falta de Inicialização Automática de Cabeçalho X-Tenant-ID nos Clientes de Teste
- **Evidência**: `backend/tests/conftest.py` (linhas 219-263).
- **Impacto**: Os clients de integração `client_with_auth_a` e `client_with_auth_b` atualizavam apenas o cabeçalho `Authorization`. Como o middleware passou a exigir o cabeçalho `X-Tenant-ID` em endpoints protegidos, todos os testes de CRUD de operações resultaram em erros `400 Bad Request` devido à falta do cabeçalho de tenant obrigatório.
- **Correção Recomendada**: Injetar automaticamente o cabeçalho `X-Tenant-ID` nas requisições do client de teste associando-o ao tenant ID do usuário correspondente.

### [AUD-03] [Testes/Erros de Digitação] Atributos Inexistentes Usados no Modelo Tenant durante Testes
- **Evidência**: `backend/tests/test_operations_crud.py` (linhas 215, 216, 664, 665, 704, 705).
- **Impacto**: O modelo `Tenant` no banco não possui os campos `slug` e `plan` (o campo correto é `plan_slug`). Chamar `Tenant(...)` passando `slug` ou `plan` resultava em `TypeError` e quebrava os testes unitários.
- **Correção Recomendada**: Alterar o instanciador do modelo nos testes para usar apenas campos existentes (`plan_slug`).

### [AUD-04] [Testes/Pydantic] Instanciação Inválida de Pydantic Models com Objetos UUID/Decimal e Validação Fora do Escopo
- **Evidência**: `backend/tests/test_operations_crud.py` (uso de `payload.model_dump()` ao enviar requisições JSON).
- **Impacto**: O serializador nativo do Python `json.dumps()` usado pelo `TestClient` falhava com `TypeError` ao tentar serializar instâncias de `UUID` ou `Decimal` criadas pelo Pydantic `model_dump()`.
- **Correção Recomendada**: Passar `mode="json"` na serialização (`payload.model_dump(mode="json")`), ou enviar payload puro (dict) para testar falhas de validação.

### [AUD-05] [Testes] Enum de Roles Inconsistente com Modelo Novo
- **Evidência**: `backend/tests/unit/test_registration_and_login.py` (linha 375).
- **Impacto**: O teste de integridade do Enum de Roles falhava pois a role `"client"` foi adicionada ao `UserRole` no modelo, mas a lista esperada no teste unitário estava desatualizada.
- **Correção Recomendada**: Adicionar `"client"` ao set esperado no teste.

---

## 3. Prontidão de Produção e Infraestrutura

### Banco de Dados (PostgreSQL + pgvector)
- O banco local usa imagem com suporte ao pgvector (`pgvector/pgvector:pg16`), o que é ideal para expansão de IA (Calculadora Fiscal inteligente e assistente RAG contábil).
- As chaves estrangeiras e relacionamentos de integridade referencial estão corretamente declarados nas models contábeis.

### Configurações locais versus produção
- O deploy usa o script `run_migrations.py` como `release_command` no Fly.io. O script está estruturado com tratamento de erro adequado e garante que as migrações Alembic rodem antes do startup das máquinas.
- Variáveis críticas estão isoladas e são esperadas como Secrets (como `DATABASE_URL` e `JWT_SECRET_KEY`).
