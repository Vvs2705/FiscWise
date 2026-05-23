# Plano de Correções Priorizado - FiscWise

Este documento descreve a priorização das correções dos problemas diagnosticados na auditoria técnica, seguindo a criticidade estabelecida (P0, P1, P2, P3).

---

## Tabela de Priorização e Status

| ID | Prioridade | Área | Descrição do Achado | Arquivo Alvo | Responsável | Status |
|----|------------|------|---------------------|--------------|-------------|--------|
| **AUD-01** | **P0** | Segurança | Brecha de isolamento de Tenant em endpoints de autenticação protegidos | `backend/app/core/middleware.py` | enterprise-architect / security-compliance | **Corrigido** e **Validado** |
| **AUD-02** | **P0** | Funcional | Fluxo de convite do Client Portal (/api/v1/portal/invites/*) quebrado por falta de tenant header | `backend/app/core/middleware.py` | enterprise-architect | **Corrigido** e **Validado** |
| **AUD-03** | **P1** | Estabilidade | Risco de dupla execução e crash de rotas no `RateLimitMiddleware` | `backend/app/core/rate_limit.py` | enterprise-architect | **Corrigido** e **Validado** |
| **AUD-04** | **P1** | Testes | Falta de X-Tenant-ID nos clientes de teste | `backend/tests/conftest.py` | qa-test-automation / test-writer | **Corrigido** e **Validado** |
| **AUD-05** | **P1** | Testes | Atributos inválidos slug/plan na instanciação de Tenant | `backend/tests/test_operations_crud.py` | test-writer | **Corrigido** e **Validado** |
| **AUD-06** | **P1** | Testes | Falha de serialização de UUID/Decimal nas requisições JSON de testes | `backend/tests/test_operations_crud.py` | test-writer | **Corrigido** e **Validado** |
| **AUD-07** | **P2** | Testes | Inconsistência de Enum no teste de UserRole com a inclusão do papel 'client' | `backend/tests/unit/test_registration_and_login.py` | test-writer | **Corrigido** e **Validado** |
| **AUD-08** | **P3** | Docs / Env | Ajuste de APP_NAME nos arquivos de ambiente de desenvolvimento de 'ContaFlow' para 'FiscWise' | `backend/.env`, `backend/.env.example` | devops-sre-cloud | **Corrigido** e **Validado** |

---

## Detalhes das Ações Tomadas e Validação

### AUD-01 (Segurança - P0) & AUD-02 (Funcional - P0)
- **Ação**: O `TenantMiddleware` foi refinado. Removido o bypass completo para `/api/v1/auth` e adicionados caminhos estritos excluídos: `/api/v1/auth/login`, `/api/v1/auth/google`, `/api/v1/auth/logout`. Também adicionado o prefixo de rota de convites públicos `/api/v1/portal/invites` e o endpoint `/api/v1/ready` à lista de exclusão do cabeçalho obrigatório.
- **Validação**: Testes em `tests/unit/test_multitenant_isolation.py` e `tests/test_tenant_middleware.py` executados com sucesso.

### AUD-03 (Estabilidade - P1)
- **Ação**: O `RateLimitMiddleware` foi corrigido para não encapsular a chamada `call_next(request)` dentro do seu bloco `try-except` principal. Agora ele apenas intercepta erros de conexão ou operações do Redis, assegurando que exceções do endpoint propaguem naturalmente sem re-executar a rota.
- **Validação**: Testes de integração de endpoints executados com sucesso.

### AUD-04, AUD-05, AUD-06, AUD-07 (Testes - P1/P2)
- **Ação**:
  - Injetado `X-Tenant-ID` nas fixtures de login (`client_with_auth_a` / `client_with_auth_b`).
  - Removidos atributos `slug` e `plan` das instâncias mock de `Tenant` no SQLAlchemy.
  - Atualizadas rotas de testes para passarem dicionários raw nas requisições JSON.
  - Atualizado set de assertions do teste de enums com a role `"client"`.
- **Validação**: Rerun do pytest retornando **110 testes executados com 100% de sucesso**.

### AUD-08 (Configurações - P3)
- **Ação**: Modificado o valor de `APP_NAME` nos arquivos `.env` e `.env.example` do backend para `"FiscWise"`.
- **Validação**: Teste unitário de imports executado com sucesso.
