# CLAUDE_REALIZAR — Equipe Segurança e Infraestrutura

**Responsável:** Claude (equipe segurança)  
**Prioridade absoluta:** Tudo aqui é pré-requisito para o produto escalar e vender.  
**Regra de ouro:** Não toque em nenhum domínio de feature (invoices, ecac, billing, portal, etc.) — deixe para a equipe Antigravyti. Sua função é blindar o que existe e preparar a infraestrutura.

---

## Fronteiras desta equipe

### Você PODE modificar
- `backend/app/core/` (config, security, middleware, exceptions)
- `backend/app/api/deps.py`
- `backend/alembic/` (migrations de infraestrutura, não de feature)
- `backend/Dockerfile` e `docker-compose.yml`
- `.github/workflows/` (CI/CD pipelines)
- `.gitignore`
- `docs/SECURITY_CORRECTIONS.md`
- `README.md` (reescrita comercial e técnica)
- `fly.toml` e `fly.staging.toml` (health probes)

### Você NÃO PODE modificar
- Qualquer arquivo dentro de `backend/app/domain/` que tenha lógica de negócio ativa (clientes, documentos, cobrança, tarefas, portal existente)
- Qualquer arquivo de frontend (a não ser variáveis de ambiente ou CSP headers)
- Schemas de banco de dados de domínios de feature — somente leia-os para entender o contexto

---

## Tarefa 1 — Desativar documentação pública em produção

**Arquivo:** `backend/app/main.py`  
**Profundidade:** cirurgia mínima, sem refatorar o arquivo inteiro.

O FastAPI expõe `/docs`, `/redoc` e `/openapi.json` por padrão. Em produção, essas rotas devem retornar 404.

```python
# Condicionalmente desabilitar docs em produção
import os
app = FastAPI(
    docs_url=None if os.getenv("ENV") == "production" else "/docs",
    redoc_url=None if os.getenv("ENV") == "production" else "/redoc",
    openapi_url=None if os.getenv("ENV") == "production" else "/openapi.json",
)
```

**Critério de aceite:**
- `ENV=production` → GET `/docs` retorna 404
- `ENV=development` → GET `/docs` retorna 200
- Escrever teste em `backend/tests/test_security.py`: `test_docs_disabled_in_production`

---

## Tarefa 2 — Remover `localhost` do CORS de produção

**Arquivo:** `backend/app/core/config.py` ou onde `ALLOWED_ORIGINS` é definido.  
**Profundidade:** apenas a lista de origens e sua lógica de validação.

Validar que `localhost` e `127.0.0.1` nunca estejam presentes quando `ENV=production`. Se estiverem, a aplicação deve falhar no startup com `ValueError` claro.

```python
if settings.ENV == "production":
    invalid = [o for o in settings.ALLOWED_ORIGINS if "localhost" in o or "127.0.0.1" in o]
    if invalid:
        raise ValueError(f"CORS contém origens inseguras em produção: {invalid}")
```

**Critério de aceite:**
- Startup com `localhost` em `ALLOWED_ORIGINS` e `ENV=production` → crash com mensagem clara
- Teste: `test_cors_rejects_localhost_in_production`

---

## Tarefa 3 — Secrets fail-closed no startup

**Arquivo:** `backend/app/core/config.py`  
**Profundidade:** apenas validação no bloco de inicialização do Settings.

Variáveis obrigatórias que devem falhar o startup se ausentes em produção:

```
JWT_SECRET_KEY
SUPABASE_URL
SUPABASE_SECRET_KEY
DATABASE_URL
REDIS_URL (se rate limit ativo)
```

Usar `@model_validator(mode="after")` no Pydantic v2:

```python
@model_validator(mode="after")
def validate_production_secrets(self):
    if self.ENV == "production":
        required = ["JWT_SECRET_KEY", "SUPABASE_SECRET_KEY", "DATABASE_URL"]
        missing = [k for k in required if not getattr(self, k, None)]
        if missing:
            raise ValueError(f"Secrets obrigatórios ausentes em produção: {missing}")
    return self
```

**Critério de aceite:**
- Startup sem `JWT_SECRET_KEY` e `ENV=production` → falha imediata com log claro
- Teste: `test_startup_fails_without_required_secrets`

---

## Tarefa 4 — Redação de DATABASE_URL nos logs

**Arquivo:** todo lugar onde `DATABASE_URL` ou strings de conexão são logadas.  
**Profundidade:** busca global + correção pontual, sem refatorar o sistema de log inteiro.

Executar: `grep -r "DATABASE_URL\|asyncpg://\|postgresql://" backend/ --include="*.py"` e auditar cada resultado.

Regra: nunca passar `settings.DATABASE_URL` para `logger.info/debug/error`. Se precisar logar, usar:

```python
logger.info("Database conectado: %s", settings.DATABASE_URL.split("@")[-1])  # exibe apenas host/db
```

**Critério de aceite:**
- Nenhum grep por `DATABASE_URL` em chamadas de log retorna resultado de log real
- Teste: `test_database_url_not_in_logs` (capture log output e verifique)

---

## Tarefa 5 — Health probes `/live` e `/ready`

**Arquivo:** `backend/app/api/routes/health.py` (criar se não existir) + `fly.toml` / `fly.staging.toml`  
**Profundidade:** endpoints simples e configuração do Fly.io.

```python
# GET /live → 200 se processo está vivo
# GET /ready → 200 se banco e Redis respondem; 503 se não

@router.get("/live")
async def liveness():
    return {"status": "alive"}

@router.get("/ready")
async def readiness(db: AsyncSession = Depends(get_db), redis=Depends(get_redis)):
    try:
        await db.execute(text("SELECT 1"))
        await redis.ping()
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
```

Atualizar `fly.toml`:
```toml
[checks]
  [checks.readiness]
    grace_period = "10s"
    interval = "15s"
    method = "GET"
    path = "/ready"
    timeout = "5s"
```

**Critério de aceite:**
- GET `/live` → 200 sempre que o processo roda
- GET `/ready` → 200 com banco ativo; 503 se banco estiver down
- Fly.io configurado para usar `/ready` como readiness probe

---

## Tarefa 6 — Rate limit estrito com Redis em produção

**Arquivo:** `backend/app/core/rate_limiter.py` (criar ou evoluir o existente)  
**Profundidade:** middleware/decorator configurável por endpoint, com Redis obrigatório em prod.

Aplicar limites diferenciados:

| Endpoint | Limite | Janela |
|---|---|---|
| `POST /auth/login` | 5 tentativas | 60s por IP |
| `POST /auth/register` | 3 tentativas | 300s por IP |
| `POST /auth/2fa` | 5 tentativas | 60s por IP |
| `POST /documents/upload` | 20 uploads | 60s por tenant |
| `POST /billing/webhook` | 100 req | 60s por IP |
| `GET /portal/*` | 30 req | 60s por IP |
| `POST /admin/*` | 10 req | 60s por IP |

Se `REDIS_URL` não estiver configurado em produção → falha no startup (ver Tarefa 3).

**Critério de aceite:**
- 6ª tentativa de login no mesmo IP dentro de 60s → 429 com header `Retry-After`
- Teste cross-IP: limite não vaza entre IPs diferentes
- Em `ENV=development` com Redis ausente → usa fallback in-memory sem travar o dev

---

## Tarefa 7 — Storage privado e URLs assinadas com TTL curto

**Arquivo:** `backend/app/core/storage.py` ou `backend/app/services/storage_service.py`  
**Profundidade:** serviço de storage central que todos os domínios usam.

Regras:
1. Nenhum bucket do Supabase Storage deve ser público.
2. Toda URL de download deve ser gerada via `supabase.storage.from_("bucket").create_signed_url(path, expires_in=300)`.
3. TTL padrão: 300 segundos (5 minutos). Máximo permitido: 3600s (1h) para downloads manuais.
4. Upload deve passar por MIME sniffing real antes de persistir (ver Tarefa 9).

```python
async def get_signed_url(bucket: str, path: str, ttl_seconds: int = 300) -> str:
    if ttl_seconds > 3600:
        raise ValueError("TTL máximo de URL assinada é 3600 segundos")
    response = supabase.storage.from_(bucket).create_signed_url(path, ttl_seconds)
    return response["signedURL"]
```

**Critério de aceite:**
- Nenhum endpoint retorna URL de storage sem expiração
- Teste: URL gerada com TTL > 3600 lança `ValueError`
- Teste cross-tenant: usuário do tenant A não consegue URL de arquivo do tenant B

---

## Tarefa 8 — Testes cross-tenant em todos os fluxos sensíveis

**Arquivo:** `backend/tests/test_cross_tenant_isolation.py`  
**Profundidade:** cobertura de todos os recursos que têm `tenant_id` na tabela.

Para cada recurso listado abaixo, escrever um teste que:
1. Cria recurso com `tenant_A`
2. Tenta acessar com `tenant_B` (leitura, atualização, deleção)
3. Valida que recebe 403 ou 404, nunca 200

Recursos a cobrir (mínimo obrigatório):
- `clients`
- `documents`
- `tasks`
- `obligations`
- `certificates`
- `billing_charges`
- `portal_invites`
- Qualquer recurso novo que Antigravyti criar com `tenant_id`

Template de teste:
```python
async def test_{resource}_cross_tenant_read_returns_404(
    client_a: AsyncClient,
    client_b: AsyncClient,
    tenant_a_resource_id: UUID,
):
    response = await client_b.get(f"/api/v1/{resource}/{tenant_a_resource_id}")
    assert response.status_code in (403, 404)
```

**Critério de aceite:**
- Todos os testes passam
- Nenhum recurso de tenant A é visível para tenant B em nenhuma operação

---

## Tarefa 9 — MIME sniffing real no upload

**Arquivo:** `backend/app/core/file_validator.py` (criar)  
**Profundidade:** validador reutilizável chamado antes de qualquer persistência de arquivo.

```python
import magic  # python-magic

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "application/xml",
    "text/xml",
    "application/zip",
}

def validate_file_mime(content: bytes, declared_content_type: str) -> str:
    real_mime = magic.from_buffer(content, mime=True)
    if real_mime not in ALLOWED_MIME_TYPES:
        raise ValueError(f"Tipo de arquivo não permitido: {real_mime}")
    if real_mime != declared_content_type:
        raise ValueError(f"MIME declarado ({declared_content_type}) difere do real ({real_mime})")
    return real_mime
```

Adicionar `python-magic` (e `python-magic-bin` no Windows) ao `requirements.txt`.

**Critério de aceite:**
- Upload de `.exe` com Content-Type `application/pdf` → rejeitado
- Upload de PDF real → aceito
- Teste: `test_mime_sniffing_rejects_disguised_executable`

---

## Tarefa 10 — Limite de tamanho de arquivo por endpoint

**Arquivo:** `backend/app/api/routes/documents.py` e qualquer rota que receba `UploadFile`.  
**Profundidade:** validação na entrada da rota, antes de qualquer processamento.

```python
MAX_FILE_SIZE_MB = {
    "document": 25,
    "certificate": 5,
    "xml": 10,
}

async def validate_upload_size(file: UploadFile, category: str):
    content = await file.read()
    max_bytes = MAX_FILE_SIZE_MB.get(category, 10) * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(413, f"Arquivo excede limite de {MAX_FILE_SIZE_MB[category]}MB")
    await file.seek(0)
    return content
```

**Critério de aceite:**
- Arquivo de 30MB em endpoint de `document` → 413
- Teste: `test_upload_rejects_oversized_file`

---

## Tarefa 11 — Substituir admin token estático

**Arquivo:** `backend/app/core/admin_auth.py` ou equivalente.  
**Profundidade:** remover token estático; implementar usuário admin real com role e middleware.

O token estático (`ADMIN_TOKEN` hardcoded ou em env simples) deve ser substituído por:
1. Usuário com `role = "admin"` no banco (tabela `users`).
2. Autenticação via JWT normal (mesmo fluxo de login).
3. Middleware que verifica `user.role == "admin"` para rotas `/admin/*`.
4. Adicionar campo `is_active` para permitir desativar admin sem deletar.

Não implementar MFA ou IP allowlist agora — isso é Onda 0, não Onda 5. Apenas remover o token estático e usar RBAC via JWT.

**Critério de aceite:**
- Nenhuma rota `/admin/*` aceita `ADMIN_TOKEN` fixo
- Usuário com `role != "admin"` → 403 em qualquer rota admin
- Teste: `test_admin_route_requires_admin_role`

---

## Tarefa 12 — Docker rodando como usuário não-root

**Arquivo:** `backend/Dockerfile`  
**Profundidade:** adicionar `USER` não-root, sem mudar a lógica de build.

```dockerfile
# No final do Dockerfile, antes do CMD:
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser
```

Se o processo precisar de portas < 1024, alterar para usar porta 8000+ (o Fly.io mapeia externamente).

**Critério de aceite:**
- `docker run fiscwise-backend whoami` → retorna `appuser`, não `root`
- Build e startup funcionam normalmente

---

## Tarefa 13 — CI: Secret scanning + Dependency scan + SAST básico

**Arquivo:** `.github/workflows/security.yml` (criar)  
**Profundidade:** pipeline separado do CI principal, rodando em PRs e pushes para main.

```yaml
name: Security Scan
on: [push, pull_request]
jobs:
  secret-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: TruffleHog Secret Scan
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: main
          extra_args: --only-verified

  dependency-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Safety Check (Python)
        run: pip install safety && safety check -r backend/requirements.txt

  sast:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Bandit SAST
        run: pip install bandit && bandit -r backend/app/ -ll -x backend/app/tests/
```

**Critério de aceite:**
- Pipeline roda em todo PR
- Falha se secret conhecido for detectado no código
- Falha se dependency com CVE crítico for detectada

---

## Tarefa 14 — Auditoria obrigatória para operações fiscais sensíveis

**Arquivo:** `backend/app/core/audit.py` (criar ou evoluir o existente)  
**Profundidade:** decorator/helper reutilizável que registra ações sensíveis em tabela dedicada.

```python
# Tabela: audit_logs
# Campos: id, tenant_id, user_id, action, resource_type, resource_id, metadata, ip, created_at

async def audit_log(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    action: str,           # ex: "document.uploaded", "certificate.accessed"
    resource_type: str,
    resource_id: UUID | None,
    metadata: dict | None,
    request: Request,
):
    ...
```

Criar migration Alembic para a tabela `audit_logs` com RLS habilitado (tenant_id filter).

Operações que OBRIGATORIAMENTE devem gerar audit log (mínimo desta onda):
- `document.uploaded`
- `document.downloaded`
- `certificate.accessed`
- `user.login`
- `user.login_failed`
- `admin.action`

A equipe Antigravyti usará este helper para seus novos domínios — ela não cria o sistema de auditoria, usa o que você criou aqui.

**Critério de aceite:**
- Após upload de documento, linha existe em `audit_logs`
- `tenant_id` de `audit_logs` sempre bate com o tenant do usuário logado
- RLS impede que tenant B leia logs do tenant A
- Teste: `test_audit_log_created_on_document_upload`

---

## Tarefa 15 — Logs estruturados sem PII sensível

**Arquivo:** `backend/app/core/logging_config.py`  
**Profundidade:** configuração central de log, sem refatorar cada logger individual.

Regras:
1. Formato JSON estruturado em produção (usar `structlog` ou `python-json-logger`).
2. Nunca logar: CPF, CNPJ completo, senha, token JWT, chave de API, `DATABASE_URL`.
3. Redactar automaticamente campos sensíveis via processor/filter de log.

```python
SENSITIVE_FIELDS = {"password", "token", "jwt", "cpf", "cnpj", "api_key", "secret"}

def redact_sensitive(logger, method, event_dict):
    for key in list(event_dict.keys()):
        if any(s in key.lower() for s in SENSITIVE_FIELDS):
            event_dict[key] = "[REDACTED]"
    return event_dict
```

**Critério de aceite:**
- Log de uma requisição de login nunca contém o valor da senha
- Teste: `test_password_not_in_log_output`

---

## Tarefa 16 — README reescrito (comercial e técnico)

**Arquivo:** `README.md`  
**Profundidade:** reescrita completa. O README atual já tem boa estrutura — expanda as seções técnicas, remova trechos que soem como "em construção", adicione `.env.example` e instrução de testes.

Estrutura obrigatória:
1. O que é o FiscWise (2-3 linhas, direto ao ponto)
2. Para quem é (contador autônomo → escritório → BPO)
3. Módulos principais (lista)
4. Stack completa (backend + frontend)
5. Como rodar localmente (pré-requisitos, `docker-compose up`, variáveis de ambiente via `.env.example`)
6. Como rodar testes (`pytest backend/` + `npm run test` no frontend)
7. Como fazer deploy (Fly.io backend, Vercel frontend)
8. Link: `docs/SECURITY_CORRECTIONS.md`

Não deve conter: histórico de fases, lista de commits, planos internos, roadmap, frases como "em breve" ou "em construção".

---

## Progresso e handoff

Ao completar cada tarefa:
1. Registrar em `docs/SECURITY_CORRECTIONS.md` (seção "Correções Onda 0") com: o que foi corrigido, como testar, data.
2. Commit atômico por tarefa com mensagem clara: `security: [descrição]` ou `infra: [descrição]`.
3. Não agrupar múltiplas tarefas em um único commit.
4. Após todas as 16 tarefas: abrir PR para `main` com título `chore(security): onda-0 blindagem e infraestrutura`.

**Ordem de execução recomendada (sem dependências entre 1-5 e 6-16):**
- Executar em paralelo: Tarefas 1, 2, 3, 4, 5
- Depois: Tarefas 6, 7, 8 (dependem de infra pronta)
- Depois: Tarefas 9, 10, 11 (dependem de storage e auth prontos)
- Por último: 12, 13, 14, 15, 16 (independentes entre si)
