# FiscWise — Segurança, Auditoria e Infraestrutura

Este documento consolida as diretrizes de segurança, o histórico de correções técnicas (auditorias), a configuração do ambiente de staging/observabilidade e o checklist de blindagem de produção.

---

## 1. Histórico de Auditoria e Correções Técnicas

As seguintes vulnerabilidades e melhorias foram identificadas e totalmente resolvidas na arquitetura do sistema:

### [AUD-01] [Segurança Crítica] Brecha de Isolamento Multi-Tenant em Endpoints de Autenticação
- **Problema**: O middleware `TenantMiddleware` incluía o prefixo `/api/v1/auth` na lista de rotas excluídas. Isso permitia que endpoints protegidos localizados sob `/auth` (como `/auth/me`, `/auth/change-password`) ignorassem a validação do cabeçalho `X-Tenant-ID`, gerando risco de vazamento de dados ou alteração de senhas entre tenants.
- **Resolução**: Removido o bypass genérico para `/api/v1/auth`. Adicionada exclusão estrita e exata apenas para rotas realmente públicas: `/api/v1/auth/login`, `/api/v1/auth/google`, `/api/v1/auth/logout`.

### [AUD-02] [Funcional] Falta de Tenant em Endpoints do Portal de Convites do Cliente
- **Problema**: O fluxo de convites sob `/api/v1/portal/invites/*` quebrava ao exigir `X-Tenant-ID` antes do usuário estar autenticado e associado ao tenant.
- **Resolução**: Inserido o prefixo de rota de convites públicos `/api/v1/portal/invites` na lista de exclusão do cabeçalho obrigatório do middleware.

### [AUD-03] [Estabilidade] Risco de Dupla Execução no RateLimitMiddleware
- **Problema**: O middleware de rate limit encapsulava a chamada de rota `call_next` dentro de um bloco genérico de captura de erros. Isso causava re-execuções da rota caso o endpoint falhasse, gerando crashes e logs inconsistentes.
- **Resolução**: Ajustado o middleware para tratar apenas conexões com o Redis, deixando que exceções do endpoint propaguem naturalmente de forma limpa.

### [AUD-04] [Testes] Falta de X-Tenant-ID nos Clientes de Teste
- **Problema**: Com o middleware de tenant ativo, os clientes de teste de integração falhavam com `400 Bad Request` devido à falta do header `X-Tenant-ID`.
- **Resolução**: Atualizado o `tests/conftest.py` para injetar o header correspondente ao tenant do usuário nas fixtures `client_with_auth_a` e `client_with_auth_b`.

### [AUD-05] [Testes] Campos Inválidos no Modelo de Tenant nos Mocks
- **Problema**: Instanciações de `Tenant` passavam campos obsoletos (`slug` e `plan`), gerando `TypeError` nas models de testes.
- **Resolução**: Corrigido o instanciador para usar apenas os campos ativos do banco, como `plan_slug`.

### [AUD-06] [Testes] Serialização de UUID/Decimal nas Requisições JSON
- **Problema**: O serializador do `TestClient` falhava com tipos complexos (UUID, Decimal) obtidos via `.model_dump()`.
- **Resolução**: Ajustados os payloads para passarem dicionários simples com serialização nativa para JSON ou usando `.model_dump(mode="json")`.

### [AUD-07] [Testes] Enum de Roles Inconsistente nos Testes Unitários
- **Problema**: Inclusão do papel `"client"` quebrava os assertions estáticos de tipos de usuários.
- **Resolução**: Atualizada a asserção para incluir `"client"` no set de valores válidos de `UserRole`.

### [AUD-08] [Configurações] Ajuste de Nomenclatura ContaFlow -> FiscWise
- **Problema**: Referências remanescentes em arquivos de ambiente e scripts de teste referenciavam o nome antigo do projeto.
- **Resolução**: Substituídas todas as instâncias para `"FiscWise"`.

---

## 2. Checklist de Blindagem de Segurança (Produção)

Para garantir que a operação do FiscWise esteja blindada contra vulnerabilidades comuns e adequada a escritórios contábeis exigentes, os seguintes controles devem ser permanentemente aplicados e testados:

1. **Desativação de Docs Públicos**: Desabilitar `/docs`, `/redoc` e `/openapi.json` em ambiente de produção (usando a variável `ENV=production` ou similar no backend).
2. **Restrição de CORS**: Desativar `localhost` nas origens permitidas em produção, mantendo apenas o domínio oficial do frontend no `ALLOWED_ORIGINS`.
3. **Redação de Logs**: Nunca imprimir strings de conexões de banco de dados (`DATABASE_URL`) ou segredos nos logs da aplicação.
4. **Startup Fail-Closed**: Falhar imediatamente na inicialização da aplicação caso segredos cruciais (como `JWT_SECRET_KEY`, `SUPABASE_SECRET_KEY`) não estejam definidos.
5. **Probes de Health**: Disponibilizar e configurar Probes `/live` e `/ready` no backend para controle do orquestrador (Fly.io).
6. **Rate Limiting**: Aplicar regras estritas de limite de requisições baseadas em IP/Token para endpoints de login, cadastro, upload e billing, utilizando Redis em produção.
7. **Upload Seguro**: Armazenar documentos contábeis em buckets privados do Supabase/S3, gerando URLs assinadas (Signed URLs) com tempo de expiração curto (TTL < 5 min).
8. **Isolamento de Tenants**: Validar que toda consulta ao banco de dados e arquivos de storage aplique o filtro `tenant_id` derivado da autenticação do usuário.

---

## 3. Ambiente Staging e Observabilidade

### Alvos de Staging
- **Backend API**: `fiscwise-staging` no Fly.io
- **Frontend SPA**: Deploy preview e branch staging na Vercel
- **Database/Storage**: Projeto isolado no Supabase para staging

### Configurações de Secrets (Fly.io Staging)
```bash
flyctl secrets set \
  DATABASE_URL="<conexao-postgres-staging>" \
  JWT_SECRET_KEY="<chave-secreta-hex>" \
  SUPABASE_URL="<url-supabase-staging>" \
  SUPABASE_SECRET_KEY="<chave-service-role-staging>" \
  OPENAI_API_KEY="<chave-openai>" \
  ADMIN_EMERGENCY_TOKEN="<token-emergência>" \
  ADMIN_OPERATIONS_ALLOWED=false \
  SENTRY_DSN="<dsn-sentry-backend>" \
  -a fiscwise-staging
```

### Deploy para Staging (Backend)
```bash
fly deploy -c fly.staging.toml -a fiscwise-staging
```

---

## 4. Testes e Validação Contínua

### Teste de Fumaça (Smoke Test)
Após qualquer deploy, execute as seguintes consultas para verificar a integridade da API e do frontend:
1. `GET /api/v1/health` (esperado: status online da API)
2. `GET /ready` (esperado: status online e conectividade OK com DB)
3. Acesso à URL principal do Frontend na Vercel (garantir renderização da página de login).
