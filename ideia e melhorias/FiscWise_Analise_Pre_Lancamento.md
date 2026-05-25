# FiscWise — Análise Técnica, Segurança e Prontidão Pré-Lançamento

**Repositório analisado:** `Vvs2705/FiscWise`  
**Data da análise:** 2026-05-24  
**Tipo de análise:** revisão estática remota do repositório público no GitHub, com foco em segurança, arquitetura, produto, privacidade, operação e riscos de lançamento.

> **Limitação importante:** esta análise foi feita a partir dos arquivos visíveis no GitHub. Não executei o projeto, não rodei testes, não fiz varredura SAST/DAST, não clonei o repositório localmente e não testei o ambiente de produção. Portanto, este relatório deve ser usado como uma revisão pré-lançamento de alto valor, mas não substitui pentest autenticado, revisão de infraestrutura, auditoria LGPD, análise de banco/Supabase nem validação em staging.

---

## 1. Resumo executivo

O FiscWise é apresentado como uma plataforma SaaS multi-tenant para escritórios de contabilidade, com backend em FastAPI/Python, frontend React/TypeScript, banco PostgreSQL/Supabase, Storage, JWT, Google OAuth, funcionalidades financeiras, documentos, obrigações fiscais, certificados digitais, planos e recursos de IA.

A base tem bons sinais: separação backend/frontend, modelos multi-tenant, middleware de tenant, uso de JWT com `tenant_id`, testes backend existentes, Sentry, health checks, migrações e deploy Fly.io/Vercel. Porém, para um produto SaaS contábil que lida com CNPJ, documentos, dados fiscais, possíveis dados pessoais e informações financeiras, há pontos que devem ser corrigidos antes do lançamento.

Os principais riscos pré-lançamento são:

1. **Credenciais e segredos de desenvolvimento versionados**, incluindo senha do PostgreSQL, senha Redis e chave JWT de desenvolvimento no `docker-compose.yml`.
2. **API pública de documentação e OpenAPI exposta em produção** (`/docs`, `/redoc`, `/openapi.json`) sem condição por ambiente.
3. **Política de segredos em produção não falha de forma segura**, permitindo startup com `DATABASE_URL` ou `JWT_SECRET_KEY` ausentes e só falhando em endpoints sensíveis.
4. **Possível vazamento de parte do `DATABASE_URL` em logs**, pois a aplicação registra os primeiros caracteres da string de conexão.
5. **CORS com origem localhost dentro da configuração de produção** e `allow_credentials=True`.
6. **Rate limit em modo não estrito por padrão**, com Redis opcional, o que tende a falhar aberto em caso de ausência de Redis.
7. **Superfície administrativa emergencial exposta por rotas**, ainda que protegida por flag/token, com operações críticas por e-mail.
8. **Dockerfile roda como root e não usa hardening mínimo de container.**
9. **Dependências sem lock/hashes no backend e com ranges no frontend**, aumentando risco de supply chain.
10. **Requisitos de LGPD, auditoria, retenção, consentimento, backups e resposta a incidentes precisam estar explícitos antes do lançamento.**

**Recomendação de go/no-go:** não lançar publicamente antes de corrigir os itens P0 deste relatório, validar todos os fluxos multi-tenant em staging e executar uma bateria mínima de SAST, dependency scan, secret scan, DAST autenticado e testes de isolamento entre tenants.

---

## 2. Visão geral do produto e superfície de risco

### 2.1 O que o produto oferece

Com base no README e estrutura do repositório, o FiscWise oferece:

- Autenticação com e-mail/senha, Google OAuth, JWT e 2FA/TOTP.
- Cadastro de empresas, usuários e planos.
- Gestão de clientes.
- Upload, visualização e download de documentos.
- Financeiro: receitas, despesas, categorias e gráficos.
- Prazos e obrigações fiscais.
- Certificados digitais.
- Admin/diagnóstico.
- Billing/subscription.
- Calculadora fiscal com IA/OpenAI.
- Deploy backend na Fly.io e frontend na Vercel.

### 2.2 Dados potencialmente sensíveis

Mesmo sem ver a base de produção, o escopo indica tratamento de:

- Dados pessoais: nome, e-mail, telefone, CPF eventualmente associado a certificados.
- Dados empresariais: razão social, CNPJ, endereço, clientes.
- Dados financeiros: receitas, despesas, pagamentos.
- Dados fiscais/documentais: contratos, declarações, relatórios e obrigações.
- Segredos operacionais: tokens JWT, credenciais de banco, chaves Supabase, OAuth, OpenAI.
- Possíveis certificados digitais A1/A3 ou metadados sobre certificados.

Isso coloca o produto em um nível de criticidade **alto** para confidencialidade e isolamento de dados.

---

## 3. Priorização geral

| Prioridade | Significado | Ação esperada |
|---|---|---|
| P0 — Bloqueante | Corrigir antes do lançamento público | Lançamento deve ser bloqueado |
| P1 — Alta | Corrigir antes de escalar clientes reais | Pode lançar apenas em beta controlado com mitigação |
| P2 — Média | Corrigir no primeiro ciclo pós-lançamento | Requer backlog com data |
| P3 — Melhoria | Otimização/qualidade/produto | Planejar evolução |

---

# 4. Itens P0 — Correções obrigatórias antes do lançamento

## P0-01 — Credenciais e segredos de desenvolvimento versionados

### Evidência observada

No `docker-compose.yml` há valores fixos para:

- `DATABASE_URL=postgresql+asyncpg://fiscwise:fiscwise_dev_2026@postgres:5432/fiscwise_db`
- `REDIS_URL=redis://:fiscwise_redis_2026@redis:6379/0`
- `JWT_SECRET_KEY=fiscwise_dev_secret_key_2026_do_not_use_in_production_generate_with_openssl_rand_hex_64`
- `POSTGRES_PASSWORD: fiscwise_dev_2026`
- `redis-server --requirepass fiscwise_redis_2026`

### Risco

Mesmo sendo credenciais de desenvolvimento, o repositório é público. Isso gera três riscos:

1. Alguém pode tentar reutilizar essas credenciais contra ambientes reais.
2. Desenvolvedores podem copiar a configuração para staging/produção.
3. Ferramentas de secret scanning podem apontar o repositório como contaminado, dificultando compliance e confiança.

### Correção

Substituir os segredos por variáveis de ambiente e criar apenas exemplos inofensivos:

```yaml
environment:
  - DATABASE_URL=${DATABASE_URL}
  - REDIS_URL=${REDIS_URL}
  - DEBUG=${DEBUG:-false}
  - ENVIRONMENT=${ENVIRONMENT:-development}
  - JWT_SECRET_KEY=${JWT_SECRET_KEY}
```

Criar um `.env.example` seguro:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/fiscwise_db
REDIS_URL=redis://:change-me@localhost:6379/0
JWT_SECRET_KEY=replace-with-openssl-rand-hex-64
```

### Ações obrigatórias

- Remover segredos fixos do `docker-compose.yml`.
- Revogar/rotacionar qualquer segredo que tenha sido usado fora do ambiente local.
- Adicionar GitHub Secret Scanning/Push Protection.
- Rodar uma ferramenta como `gitleaks` ou `trufflehog` no histórico.
- Documentar que credenciais locais nunca devem ser reutilizadas em staging/prod.

---

## P0-02 — Produção pode iniciar com `DATABASE_URL` ou `JWT_SECRET_KEY` ausentes

### Evidência observada

Em `backend/app/core/config.py`, os validators de `DATABASE_URL` e `JWT_SECRET_KEY` não interrompem a aplicação em produção/staging quando faltam valores; eles registram erro crítico e retornam string vazia. Em `backend/app/main.py`, a aplicação também registra que o health check continuará saudável, mesmo quando segredos obrigatórios estão ausentes.

### Risco

Isso cria uma condição insegura de “produção parcialmente viva”:

- `/health` pode retornar OK enquanto autenticação/banco quebram.
- Monitoramento e orquestrador podem considerar o serviço saudável.
- Falhas podem aparecer somente em tempo de request.
- Em um cenário pior, uma chave JWT vazia ou fraca pode causar autenticação insegura se algum fluxo não tratar adequadamente.

### Correção recomendada

Em produção e staging, segredos obrigatórios devem ser **fail-closed**. O processo deve falhar no startup quando valores essenciais estiverem ausentes ou forem fracos.

Exemplo:

```python
@field_validator("JWT_SECRET_KEY", mode="before")
@classmethod
def validate_jwt_secret(cls, v: str, info) -> str:
    environment = info.data.get("ENVIRONMENT", "development")

    if environment in {"production", "staging"}:
        if not v:
            raise ValueError("JWT_SECRET_KEY is required in production/staging")
        if len(v) < 64:
            raise ValueError("JWT_SECRET_KEY must have at least 64 characters")
        if "dev_secret" in v.lower() or "do_not_use" in v.lower():
            raise ValueError("JWT_SECRET_KEY cannot be a development default")

    return v
```

### Ações obrigatórias

- Fazer a aplicação falhar em produção/staging se faltarem: `DATABASE_URL`, `JWT_SECRET_KEY`, `SUPABASE_SECRET_KEY`, `GOOGLE_CLIENT_ID` quando OAuth estiver habilitado, `OPENAI_API_KEY` quando a calculadora IA estiver habilitada.
- Separar health check em:
  - `/live`: processo vivo.
  - `/ready`: banco, Redis, storage, secrets e migrations OK.
- Fazer Fly.io usar `/ready` para readiness, não apenas um endpoint que não toca banco.

---

## P0-03 — Possível vazamento parcial de `DATABASE_URL` em logs

### Evidência observada

No startup, `backend/app/main.py` registra algo equivalente a:

```python
logger.info("DATABASE_URL: %s...", settings.DATABASE_URL[:40])
```

### Risco

Os primeiros caracteres de uma URL de banco normalmente incluem:

```text
postgresql+asyncpg://usuario:senha@host...
```

Mesmo que o log corte em 40 caracteres, pode vazar parte do usuário, senha ou host. Em plataformas como Fly.io/Sentry/log drains, logs podem ser acessados por terceiros internos, ferramentas ou integrações.

### Correção

Nunca logar segredos ou strings de conexão. Logar apenas estado booleano e host sanitizado, se necessário.

```python
logger.info("DATABASE_URL: configured")
```

Se precisar depurar host:

```python
from urllib.parse import urlparse

def safe_db_host(url: str) -> str:
    try:
        parsed = urlparse(url)
        return parsed.hostname or "unknown"
    except Exception:
        return "unknown"

logger.info("DATABASE_URL configured for host=%s", safe_db_host(settings.DATABASE_URL))
```

### Ações obrigatórias

- Remover log parcial de `DATABASE_URL`.
- Auditar logs existentes e rotacionar credenciais se houver qualquer chance de exposição.
- Configurar filtros/redaction no Sentry e log drains.

---

## P0-04 — Swagger, ReDoc e OpenAPI expostos em produção

### Evidência observada

Em `backend/app/main.py`, a aplicação FastAPI define:

```python
docs_url="/docs"
redoc_url="/redoc"
openapi_url="/openapi.json"
```

sem condição por ambiente.

### Risco

Documentação pública da API aumenta a superfície de ataque. Para produto SaaS contábil, expor todos os endpoints, schemas e rotas administrativas facilita enumeração de funcionalidades, automação de ataques e fuzzing direcionado.

### Correção

Desabilitar docs em produção pública ou protegê-las com autenticação forte e allowlist.

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

Se a documentação for necessária em produção:

- proteger por VPN, Cloudflare Access, Basic Auth forte ou login interno;
- rate limit específico;
- não expor schemas administrativos.

### Ações obrigatórias

- Desabilitar `/docs`, `/redoc`, `/openapi.json` em produção.
- Criar ambiente interno/staging com docs.
- Garantir que a Vercel/frontend não linke para docs públicas de produção.

---

## P0-05 — CORS de produção inclui localhost e permite credenciais

### Evidência observada

No `fly.toml`, `ALLOWED_ORIGINS` inclui domínios de produção e também `http://localhost:3000`. No `main.py`, o CORS usa `allow_credentials=True`, `allow_methods=["*"]` e `allow_headers=["*"]`.

### Risco

Ter `localhost` na allowlist de produção é perigoso quando `allow_credentials=True`, especialmente se no futuro tokens forem armazenados em cookies ou se integrações locais simularem origens confiáveis. Mesmo com Authorization Bearer, CORS permissivo aumenta risco de abuso via aplicações controladas por atacante em ambiente local da vítima/desenvolvedor.

### Correção

Separar CORS por ambiente:

```env
# production
ALLOWED_ORIGINS=https://fiscwise.com.br,https://www.fiscwise.com.br,https://app.fiscwise.com.br
```

Em desenvolvimento:

```env
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

No backend:

```python
if settings.ENVIRONMENT == "production":
    assert all("localhost" not in o for o in settings.allowed_origins_list)
```

### Ações obrigatórias

- Remover localhost de `fly.toml`.
- Remover domínios antigos/temporários de Vercel se não forem usados.
- Usar domínios finais do produto.
- Testar CORS com `Origin` malicioso.
- Adicionar teste automatizado que falha se `localhost` aparecer em produção.

---

## P0-06 — Rate limit tende a falhar aberto

### Evidência observada

Em `config.py`, `REDIS_URL` é opcional e `RATE_LIMIT_STRICT` tem default `False`. Em `main.py`, o middleware de rate limit é adicionado com Redis opcional.

### Risco

Endpoints de login, 2FA, recuperação de senha, OAuth e admin precisam de proteção contra brute force e automação. Se Redis não estiver configurado, o rate limit não deve simplesmente degradar sem controle em produção.

### Correção

- Em produção, `REDIS_URL` deve ser obrigatório se houver rate limit baseado em Redis.
- `RATE_LIMIT_STRICT=True` deve ser default em produção.
- Login, 2FA, registro, troca de senha e admin devem ter limites específicos por IP, conta, e-mail e tenant.

Exemplo de política mínima:

| Endpoint | Limite sugerido |
|---|---|
| `/auth/login` | 5 tentativas/min/IP + 10/h/e-mail |
| `/auth/login/verify-2fa` | 5 tentativas/5min/usuário |
| `/auth/register` | 10/h/IP |
| `/admin/*` | 3/min/IP + alerta |
| Upload de documentos | limite por tamanho + rate por usuário |

### Ações obrigatórias

- Tornar Redis obrigatório em produção.
- Fail-closed se `RATE_LIMIT_STRICT=True` e Redis indisponível.
- Criar testes para ausência de Redis em produção.
- Adicionar alertas de brute force.

---

## P0-07 — Rotas administrativas emergenciais precisam de proteção operacional mais forte

### Evidência observada

`backend/app/api/v1/endpoints/admin.py` define `ADMIN_EMERGENCY_TOKEN`, flag `ADMIN_OPERATIONS_ALLOWED`, `HTTPBearer`, comparação com `hmac.compare_digest` e rotas como `set-plan-by-email` e `tenant-by-email`.

### Risco

Apesar de haver token e flag, são operações sensíveis:

- alteração de plano por e-mail;
- consulta de tenant por e-mail;
- possível enumeração de usuários/tenants se token vazar;
- uso de token estático sem identidade, expiração, MFA ou auditoria estruturada;
- erro humano ativando `ADMIN_OPERATIONS_ALLOWED=true` em produção.

### Correção recomendada

Substituir “admin token estático” por um modelo administrativo auditável:

- login administrativo real com RBAC;
- MFA obrigatório;
- allowlist de IP/VPN;
- logs imutáveis;
- aprovação dupla para alteração de plano;
- expiração curta para operações emergenciais;
- assinatura de operação com motivo/ticket.

Para o curto prazo:

```python
if settings.ENVIRONMENT == "production":
    require_ip_allowlist(request)
    require_mfa_admin(current_user)
    require_audit_reason(body.reason)
```

### Ações obrigatórias

- Garantir que `ADMIN_OPERATIONS_ALLOWED=false` em produção por padrão.
- Não ativar por variável permanente; usar janela temporária.
- Registrar auditoria com: admin, IP, user-agent, tenant afetado, antes/depois, motivo, ticket.
- Não retornar mensagens que permitam enumeração por e-mail.
- Adicionar rate limit estrito nas rotas admin.

---

## P0-08 — Mismatch de variável Supabase pode quebrar storage ou induzir configuração insegura

### Evidência observada

O `config.py` espera `SUPABASE_SECRET_KEY`. O `fly.toml` comenta segredo obrigatório como `SUPABASE_SERVICE_KEY`. O README também lista Supabase anon key e service key.

### Risco

Inconsistência de nome de variável pode gerar:

- upload/storage quebrado em produção;
- uso acidental da chave anon em local da service role;
- tentativa de resolver às pressas expondo service key no frontend;
- falhas intermitentes em deploy.

### Correção

Padronizar nomes:

```env
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
```

No backend:

```python
SUPABASE_SERVICE_ROLE_KEY: str = ""
```

No frontend, nunca expor service role. Apenas `VITE_SUPABASE_ANON_KEY`, se necessário e com RLS correto.

### Ações obrigatórias

- Renomear para um padrão único.
- Atualizar `.env.example`, README, Fly secrets e código.
- Criar teste de startup para validar presença das chaves corretas em produção.
- Validar políticas RLS no Supabase.

---

## P0-09 — Isolamento multi-tenant deve ser validado como requisito de lançamento

### Evidência observada

O README afirma que toda entidade possui `tenant_id` e que o `TenantMiddleware` injeta o tenant a partir do JWT. Em `deps.py`, o token JWT contém `tenant_id`, o backend compara o `tenant_id` do token com o `tenant_id` do usuário e seta contexto PostgreSQL via `set_config('app.current_tenant_id', ...)`.

### Risco

O produto é multi-tenant; qualquer falha de filtro por `tenant_id` é crítica. Mesmo com middleware, basta um endpoint esquecer um filtro, fazer join incorreto, usar query raw, ou acessar objeto por UUID global para vazar dados entre escritórios contábeis.

### Correção obrigatória

Criar garantia em camadas:

1. **Aplicação:** todas as queries filtram por `tenant_id`.
2. **Banco:** RLS no PostgreSQL/Supabase usando `app.current_tenant_id`.
3. **Testes:** testes negativos entre tenants em todos os endpoints.
4. **Logs/Auditoria:** tenant_id sempre presente nos logs de ações sensíveis.
5. **IDs:** não confiar apenas em UUID; validar ownership.

Checklist de testes mínimos:

- usuário A do tenant 1 não acessa cliente do tenant 2;
- usuário A não baixa documento do tenant 2;
- usuário A não altera obrigação fiscal do tenant 2;
- admin de tenant não acessa dados globais;
- busca/paginação/filtros não retornam dados de outro tenant;
- importação XLSX não associa cliente a tenant errado;
- URLs/presigned links de documentos não são reutilizáveis por outro tenant.

### Ações obrigatórias

- Revisar todos os endpoints CRUD.
- Criar suíte `test_cross_tenant_isolation.py`.
- Validar RLS no Supabase/PostgreSQL.
- Bloquear lançamento sem testes de isolamento.

---

## P0-10 — Upload, storage e documentos precisam de política de segurança explícita

### Risco

O produto manipula documentos de clientes contábeis. Upload/download é uma das superfícies mais críticas:

- malware em arquivos enviados;
- arquivos grandes causando DoS;
- upload de HTML/SVG executável;
- spoofing de MIME type;
- exposição por URL pública;
- path traversal/nome de arquivo inseguro;
- vazamento entre tenants;
- ausência de retenção/expurgo LGPD;
- ausência de criptografia/controle de acesso por objeto.

### Correção obrigatória

Implementar uma política de documentos:

| Controle | Requisito |
|---|---|
| Tamanho máximo | Ex.: 10–25 MB por arquivo, conforme plano |
| Tipos permitidos | PDF, XLSX, DOCX, PNG/JPG, conforme necessidade real |
| MIME sniffing | Validar conteúdo real, não só extensão |
| Antivírus | ClamAV, serviço gerenciado ou fila assíncrona |
| Storage privado | Nunca bucket público para documentos sensíveis |
| URLs assinadas | Expiração curta, tenant/user validated |
| Nome de arquivo | Gerar UUID; armazenar nome original separado |
| Criptografia | Em repouso e em trânsito |
| Auditoria | Log de upload/download/delete |
| Retenção | Política por tenant e exclusão sob solicitação |

### Ações obrigatórias

- Criar `DocumentSecurityPolicy`.
- Adicionar validação de tamanho e MIME.
- Garantir buckets privados no Supabase.
- Impedir download direto sem autorização backend.
- Testar acesso cruzado por URL de documento.

---

## P0-11 — Proteção LGPD e privacidade ainda precisa ser tratada como requisito de produto

### Risco

O produto opera com dados pessoais, empresariais e fiscais. Antes do lançamento, é necessário ter:

- base legal definida;
- política de privacidade;
- termos de uso;
- política de retenção;
- processo de exclusão/exportação de dados;
- DPA/contrato com clientes B2B;
- registro de operadores/suboperadores;
- segurança por padrão;
- trilha de auditoria;
- plano de resposta a incidentes.

### Correção obrigatória

Criar um pacote mínimo LGPD:

1. **Política de Privacidade** específica para SaaS contábil.
2. **Termos de Uso** com limitações de responsabilidade fiscal.
3. **Contrato/DPA B2B** com papéis controlador/operador.
4. **Data map**: quais dados são coletados, onde ficam, por quanto tempo.
5. **Processo DSAR**: acesso, correção, exclusão, portabilidade.
6. **Retenção/expurgo** por tenant e tipo de dado.
7. **Subprocessadores**: Fly.io, Vercel, Supabase, Sentry, OpenAI, Google OAuth etc.
8. **Incidentes**: playbook de comunicação e contenção.

### Ações obrigatórias

- Não lançar sem política e termos.
- Adicionar telas de consentimento quando necessário.
- Registrar logs de tratamento de dados sensíveis.
- Documentar subprocessadores no site.

---

# 5. Itens P1 — Alta prioridade antes de escalar

## P1-01 — Dockerfile sem usuário não-root

### Evidência observada

O `Dockerfile` usa `python:3.12-slim`, instala dependências, copia o backend e executa `uvicorn`, mas não define `USER` não-root.

### Risco

Se houver RCE, SSRF com escrita, exploração de biblioteca de parsing ou falha no app, o processo rodando como root aumenta impacto dentro do container.

### Correção

Adicionar usuário dedicado:

```dockerfile
RUN addgroup --system app && adduser --system --ingroup app app
WORKDIR /app
COPY backend/ .
RUN chown -R app:app /app
USER app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

Complementar com:

- filesystem read-only quando possível;
- `no-new-privileges`;
- limitar capabilities;
- multi-stage build;
- remover `gcc` e ferramentas de build da imagem final;
- usar imagem digest-pinned.

---

## P1-02 — Dependências sem controle forte de supply chain

### Evidência observada

Backend usa `requirements.txt` com versões fixas para várias libs, mas sem hashes e sem lock transitive. Frontend usa `package-lock.json`, mas `package.json` possui ranges `^`.

### Risco

- Instalações futuras podem resolver versões diferentes.
- Dependências transitivas podem introduzir vulnerabilidades.
- Risco de supply-chain e typosquatting.
- Diferença entre ambiente local, CI e produção.

### Correção

Backend:

```bash
pip-compile --generate-hashes -o requirements.lock requirements.in
pip install --require-hashes -r requirements.lock
```

Frontend:

```bash
npm ci
npm audit --omit=dev
```

CI obrigatório:

- `pip-audit`
- `npm audit`
- `osv-scanner`
- `semgrep`
- `bandit`
- `gitleaks`
- build de imagem com scanner (`trivy`/`grype`)

---

## P1-03 — Headers de segurança ausentes no backend/app

### Risco

Não foi identificada configuração explícita de headers como:

- `Content-Security-Policy`
- `X-Content-Type-Options`
- `Referrer-Policy`
- `Permissions-Policy`
- `Strict-Transport-Security`
- `X-Frame-Options` ou equivalente via CSP

### Correção

Adicionar middleware:

```python
@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["X-Frame-Options"] = "DENY"
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    return response
```

No frontend, definir CSP na Vercel. Começar com `Content-Security-Policy-Report-Only`, ajustar, depois aplicar enforcement.

---

## P1-04 — JWT sem revogação, rotação e claims de segurança suficientes

### Evidência observada

`security.py` cria JWT com `sub`, `tenant_id`, `role`, `exp` e `iat`. O tempo padrão de expiração é 30 minutos.

### Risco

- Sem `jti`, não há revogação granular.
- Sem `aud`/`iss`, tokens podem ser aceitos fora do contexto esperado.
- Sem versionamento de segredo (`kid`), rotação é difícil.
- Mudanças de permissão/plano podem não invalidar tokens já emitidos.
- Não foi observado refresh token robusto com rotação/reuse detection.

### Correção

Adicionar claims:

```python
payload = {
    "iss": "https://api.fiscwise.com.br",
    "aud": "fiscwise-web",
    "sub": user_id,
    "tenant_id": tenant_id,
    "role": role,
    "jti": str(uuid.uuid4()),
    "token_version": user.token_version,
    "iat": issued_at,
    "exp": expire,
}
```

Implementar:

- refresh token rotacionado e armazenado com hash;
- logout que revoga refresh token;
- `token_version` para invalidar todos os tokens do usuário;
- rotação de `JWT_SECRET_KEY` com `kid`;
- invalidação ao trocar senha, habilitar/desabilitar 2FA, alterar role ou desativar usuário.

---

## P1-05 — Autenticação 2FA precisa de controles contra replay e força bruta

### Evidência observada

`security.py` cria token MFA de 5 minutos com `sub` e `type="mfa"`.

### Risco

O token de desafio MFA, se não estiver ligado a uma sessão de tentativa, pode ser reusado durante a janela de validade. O endpoint de verificação 2FA precisa de rate limit estrito por usuário e challenge.

### Correção

- Adicionar `jti` ao token MFA.
- Armazenar challenge MFA no Redis com TTL.
- Marcar challenge como consumido após sucesso.
- Limitar tentativas por challenge.
- Invalidar challenge após troca de senha ou nova tentativa de login.
- Registrar eventos: MFA enabled, disabled, failed, recovery used.

---

## P1-06 — Endpoint de diagnóstico retorna detalhes internos quando habilitado

### Evidência observada

`diagnostic.py` tem flag `DIAGNOSTICS_ENABLED`, autenticação e role owner. Quando habilitado, retorna enums, migrações e detalhes de erro.

### Risco

Mesmo protegido, diagnóstico detalhado em produção pode vazar:

- versões de migrations;
- estrutura interna do banco;
- erros e mensagens;
- estado operacional.

### Correção

- Nunca habilitar diagnóstico em produção pública.
- Separar diagnóstico em rota interna protegida por VPN/allowlist.
- Retornar dados mínimos no produto.
- Remover `error: str(e)` de respostas; manter detalhes apenas em logs internos.

---

## P1-07 — Admin por e-mail pode gerar enumeração e alteração indevida

### Evidência observada

Rotas admin buscam usuário por e-mail e retornam mensagens como `No user found with email`.

### Risco

Com token admin vazado, um atacante consegue enumerar e-mails e tenants. Mesmo sem vazamento, mensagens detalhadas aumentam risco operacional.

### Correção

- Responder mensagens genéricas.
- Exigir `tenant_id` + `user_id`, não apenas e-mail.
- Adicionar workflow de aprovação para alteração de plano.
- Auditar motivo e ticket.
- Criar logs estruturados e alertas.

---

## P1-08 — Configuração de produção contém domínios temporários

### Evidência observada

`fly.toml` contém origens Vercel temporárias além de domínios finais.

### Risco

Domínios temporários podem permanecer ativos, ser esquecidos ou mudar de controle, ampliando superfície CORS e confundindo ambiente.

### Correção

- Usar apenas domínios finais em produção.
- Mover domínios de preview para staging.
- Configurar Vercel Preview Deployments com backend de staging, não produção.

---

## P1-09 — Falta de política clara para IA/fiscal calculator

### Risco

A calculadora fiscal com IA pode gerar respostas erradas, incompletas ou desatualizadas. Em produto contábil, isso vira risco jurídico e reputacional.

### Correção

- IA deve ser assistiva, não fonte final de decisão.
- Exibir disclaimer: “não substitui revisão de contador”.
- Registrar prompt/resposta com cuidado e sem expor dados sensíveis.
- Não enviar documentos/dados pessoais à IA sem base legal/consentimento.
- Implementar filtros para dados sensíveis.
- Adicionar trilha de auditoria e versionamento de regras fiscais.
- Preferir motor determinístico para cálculos fiscais e IA apenas para explicação.

---

## P1-10 — Ausência de estratégia formal de backup, restore e DR

### Risco

SaaS contábil precisa recuperar dados por tenant, por ponto no tempo e em incidentes.

### Correção

Definir:

- backups automáticos diários;
- PITR quando possível;
- restore testado mensalmente;
- criptografia de backups;
- retenção por política;
- runbook de recuperação;
- RPO/RTO;
- exportação por tenant.

---

# 6. Itens P2 — Melhorias importantes

## P2-01 — Melhorar health checks

Criar três endpoints:

```text
/live   -> processo vivo, sem dependências
/ready  -> banco, migrations, storage, redis, secrets OK
/health -> status público mínimo
```

O health público não deve expor stack, banco, migrations, erro interno ou configuração.

---

## P2-02 — Adicionar `TrustedHostMiddleware`

Configurar hosts permitidos para evitar abuso de Host Header:

```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["api.fiscwise.com.br", "fiscwise.fly.dev"]
)
```

---

## P2-03 — Padronizar erros e não vazar detalhes

Evitar mensagens como:

- `No user found with email`
- `No tenant found`
- `database may not be initialized`
- stack traces ou `str(e)` em resposta

Usar:

```json
{ "detail": "Operation could not be completed" }
```

e manter detalhes em logs internos com correlação.

---

## P2-04 — Criar auditoria funcional

Eventos que devem ser auditados:

- login/logout/falha;
- 2FA habilitado/desabilitado;
- troca de senha;
- criação/alteração/exclusão de cliente;
- upload/download/delete de documento;
- alteração de plano;
- alteração de dados do escritório;
- alteração de role/usuário;
- exportação de dados;
- eventos de IA com metadados.

Campos mínimos:

```text
event_id, timestamp, tenant_id, actor_user_id, actor_role, action,
resource_type, resource_id, ip, user_agent, outcome, metadata_redacted
```

---

## P2-05 — Segurança no frontend

Pontos a validar:

- tokens não devem ficar em `localStorage` se houver risco XSS relevante;
- preferir cookies `HttpOnly`, `Secure`, `SameSite=Lax/Strict` para sessão;
- sanitizar qualquer conteúdo renderizado de documentos/importações;
- CSP forte;
- proteger rotas por autorização real no backend, não só UI;
- não expor `VITE_*` com segredos;
- configurar Sentry para não enviar PII.

---

## P2-06 — Controle de planos no backend

O README indica planos Free/Starter/Pro e troca em tempo real. Todo limite de plano precisa ser enforce no backend, não só no frontend:

- número de clientes;
- quantidade/tamanho de documentos;
- acesso a IA;
- usuários por tenant;
- obrigações/prazos;
- integrações.

Criar testes para cada limite.

---

## P2-07 — Políticas de retenção e exclusão por tenant

Implementar:

- soft delete com janela de recuperação;
- hard delete sob solicitação quando aplicável;
- expurgo assíncrono de documentos;
- retenção legal configurável;
- exportação de dados.

---

## P2-08 — Observabilidade e alertas

Alertas mínimos:

- taxa de 401/403 anormal;
- falhas de login por IP/e-mail;
- picos de upload/download;
- erros 500 por endpoint;
- falhas de migrations;
- Redis indisponível;
- Supabase/storage indisponível;
- OpenAI/IA indisponível;
- admin endpoint chamado;
- CORS bloqueado repetidamente.

---

# 7. Itens P3 — Qualidade, manutenção e produto

## P3-01 — Padronizar nomenclatura ContaFlow/FiscWise

O Dockerfile ainda contém comentário “ContaFlow Backend Dockerfile”. Remover nomes antigos para evitar confusão em auditorias, documentação e onboarding.

## P3-02 — Melhorar documentação de ambiente

Criar arquivos claros:

```text
docs/environment.md
docs/secrets.md
docs/security.md
docs/incident-response.md
docs/backup-restore.md
docs/data-retention.md
```

## P3-03 — Checklist de release

Criar `RELEASE_CHECKLIST.md` com:

- migrations aplicadas;
- secrets conferidos;
- CORS conferido;
- docs desabilitadas;
- secret scan limpo;
- dependency scan limpo;
- SAST limpo;
- DAST staging executado;
- testes cross-tenant OK;
- backup/restore testado;
- monitoramento ativo.

## P3-04 — Melhorar UX de erro

Para produto contábil, erros devem ser acionáveis:

- upload rejeitado: explicar tipo/tamanho;
- vencimento de obrigação: mostrar data e consequência;
- IA indisponível: fallback para cálculo manual;
- integração externa falhou: retry e status claro.

---

# 8. Checklist técnico antes do lançamento

## Segurança de aplicação

- [ ] `/docs`, `/redoc`, `/openapi.json` desabilitados/protegidos em produção.
- [ ] `JWT_SECRET_KEY` obrigatório e forte em produção.
- [ ] `DATABASE_URL` obrigatório em produção.
- [ ] `SUPABASE_SERVICE_ROLE_KEY` padronizado e nunca exposto no frontend.
- [ ] CORS sem localhost/domínios temporários em produção.
- [ ] Rate limit estrito em login, 2FA, registro, admin e upload.
- [ ] Security headers implementados.
- [ ] `TrustedHostMiddleware` configurado.
- [ ] Erros não vazam detalhes internos.
- [ ] Tokens JWT com `iss`, `aud`, `jti`, rotação e revogação.
- [ ] Refresh token seguro, rotativo e revogável.
- [ ] MFA com rate limit, challenge único e recuperação segura.
- [ ] Admin protegido por RBAC/MFA/IP allowlist/auditoria.

## Multi-tenant

- [ ] Testes negativos entre tenants em todos os CRUDs.
- [ ] RLS validado no PostgreSQL/Supabase.
- [ ] Toda query filtra `tenant_id`.
- [ ] Presigned URLs não vazam documentos.
- [ ] Jobs/scheduler respeitam tenant.
- [ ] Admin global não mistura contextos.

## Upload/documentos

- [ ] Bucket privado.
- [ ] URL assinada com expiração curta.
- [ ] Validação de tamanho.
- [ ] Validação de MIME real.
- [ ] Antivírus ou scanning assíncrono.
- [ ] Nome seguro por UUID.
- [ ] Auditoria de upload/download/delete.
- [ ] Política de retenção.

## Infra/DevOps

- [ ] Docker não-root.
- [ ] Build multi-stage.
- [ ] Imagem escaneada.
- [ ] Sem ferramentas de build na imagem final.
- [ ] Secrets apenas no gerenciador de secrets.
- [ ] `docker-compose.yml` sem segredos reais.
- [ ] CI com testes, lint, type-check, SAST, secret scan e dependency scan.
- [ ] Backup/restore testado.
- [ ] Health checks separados em live/ready.

## Frontend

- [ ] `npm ci` no build.
- [ ] CSP configurado.
- [ ] Tokens armazenados de forma segura.
- [ ] Nenhum segredo em `VITE_*`.
- [ ] Sentry sem PII.
- [ ] Rotas protegidas por backend, não apenas UI.
- [ ] Tratamento de erro e loading consistente.

## Produto/LGPD

- [ ] Política de privacidade publicada.
- [ ] Termos de uso publicados.
- [ ] DPA/contrato B2B pronto.
- [ ] Subprocessadores listados.
- [ ] Retenção/expurgo definido.
- [ ] Exportação de dados por tenant.
- [ ] Resposta a incidentes documentada.
- [ ] Disclaimers de IA e responsabilidade fiscal.
- [ ] Processo de suporte e SLA mínimo.

---

# 9. Plano de correção sugerido

## Sprint 0 — Bloqueio de lançamento

1. Remover segredos versionados e rodar secret scan.
2. Fazer produção falhar se segredos obrigatórios faltarem.
3. Remover log parcial de `DATABASE_URL`.
4. Desabilitar docs/OpenAPI em produção.
5. Corrigir CORS de produção.
6. Tornar rate limit estrito para autenticação/admin.
7. Travar admin endpoints com allowlist/MFA/auditoria ou desativar totalmente.
8. Padronizar Supabase env vars.
9. Criar testes cross-tenant mínimos.
10. Validar upload/download seguro por tenant.

## Sprint 1 — Hardening

1. Docker não-root e multi-stage.
2. Security headers/CSP.
3. TrustedHostMiddleware.
4. JWT com `jti`, `aud`, `iss`, refresh seguro.
5. Auditoria de eventos sensíveis.
6. CI com SAST/secret/dependency scan.
7. Backup/restore testado.

## Sprint 2 — Compliance e produto

1. LGPD: política, termos, DPA e data map.
2. Retenção/exportação/exclusão por tenant.
3. Disclaimers e governança de IA.
4. Alertas operacionais.
5. Runbooks de incidentes.
6. Plano de suporte e SLA.

---

# 10. Exemplos de ajustes práticos

## 10.1 Configuração segura de FastAPI por ambiente

```python
is_prod = settings.ENVIRONMENT == "production"

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url=None if is_prod else "/docs",
    redoc_url=None if is_prod else "/redoc",
    openapi_url=None if is_prod else "/openapi.json",
    lifespan=lifespan,
)
```

## 10.2 Validação hard fail para produção

```python
def require_secret(name: str, value: str, min_len: int = 1) -> None:
    if settings.ENVIRONMENT in {"production", "staging"}:
        if not value or len(value) < min_len:
            raise RuntimeError(f"{name} is required in {settings.ENVIRONMENT}")
```

## 10.3 Redação de logs

```python
logger.info("DATABASE_URL configured=%s", bool(settings.DATABASE_URL))
logger.info("JWT_SECRET_KEY configured=%s", bool(settings.JWT_SECRET_KEY))
```

## 10.4 CORS seguro

```python
production_origins = [
    "https://fiscwise.com.br",
    "https://www.fiscwise.com.br",
    "https://app.fiscwise.com.br",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=production_origins if is_prod else settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
```

## 10.5 Docker não-root

```dockerfile
FROM python:3.12-slim

RUN addgroup --system app && adduser --system --ingroup app app
WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
RUN chown -R app:app /app

USER app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

---

# 11. Testes mínimos recomendados

## 11.1 Segurança

- `test_production_requires_jwt_secret`
- `test_production_requires_database_url`
- `test_docs_disabled_in_production`
- `test_cors_rejects_unknown_origin`
- `test_localhost_not_allowed_in_production`
- `test_rate_limit_login`
- `test_rate_limit_2fa`
- `test_admin_requires_flag_token_mfa`
- `test_no_secret_in_logs`

## 11.2 Multi-tenant

- `test_client_cannot_access_other_tenant_client`
- `test_user_cannot_download_other_tenant_document`
- `test_obligation_filter_by_tenant`
- `test_financial_entries_filter_by_tenant`
- `test_admin_tenant_scope`
- `test_search_does_not_cross_tenant`
- `test_pagination_does_not_cross_tenant`
- `test_raw_sql_respects_rls`

## 11.3 Upload

- `test_reject_large_file`
- `test_reject_disallowed_mime`
- `test_reject_mime_spoof`
- `test_private_bucket_required`
- `test_signed_url_expiration`
- `test_download_requires_owner_tenant`
- `test_file_name_sanitized`

## 11.4 Produto/planos

- `test_free_plan_limit_clients`
- `test_plan_upgrade_allows_feature`
- `test_plan_downgrade_blocks_feature`
- `test_subscription_cancelled_blocks_premium`
- `test_billing_webhook_idempotency`

---

# 12. Matriz de riscos

| Risco | Impacto | Probabilidade | Prioridade |
|---|---:|---:|---|
| Vazamento entre tenants | Crítico | Médio | P0 |
| Segredo fraco/ausente em produção | Crítico | Médio | P0 |
| Docs públicas facilitando enumeração | Alto | Alto | P0 |
| Brute force em login/2FA | Alto | Médio | P0/P1 |
| Documentos acessíveis indevidamente | Crítico | Médio | P0 |
| Admin token vazado | Crítico | Baixo/Médio | P0/P1 |
| IA fornecendo orientação fiscal incorreta | Alto | Médio | P1 |
| Falha de backup/restore | Alto | Médio | P1 |
| Container root explorado | Alto | Baixo/Médio | P1 |
| Dependência vulnerável introduzida | Alto | Médio | P1 |

---

# 13. Decisão recomendada

## Não lançar publicamente enquanto houver qualquer item P0 aberto.

O produto está em uma categoria sensível: contabilidade, documentos, dados fiscais, informações financeiras e SaaS multi-tenant. O mínimo aceitável para lançamento é:

1. segredos e ambientes corretamente isolados;
2. documentação pública bloqueada;
3. CORS estrito;
4. rate limiting estrito;
5. isolamento multi-tenant testado;
6. documentos protegidos;
7. admin seguro/auditado;
8. LGPD mínima implementada;
9. CI com scanners;
10. backup/restore validado.

Após corrigir P0, é razoável iniciar um **beta controlado** com poucos clientes, logs reforçados, feature flags, monitoramento e plano de resposta a incidentes.

---

# 14. Referências internas analisadas

Arquivos/pontos usados nesta análise:

- `README.md`
- `docker-compose.yml`
- `fly.toml`
- `vercel.json`
- `backend/Dockerfile`
- `backend/requirements.txt`
- `backend/app/main.py`
- `backend/app/core/config.py`
- `backend/app/core/deps.py`
- `backend/app/core/security.py`
- `backend/app/api/v1/endpoints/admin.py`
- `backend/app/api/v1/endpoints/diagnostic.py`
- `backend/tests/`
- `frontend/package.json`

---

# 15. Conclusão

O FiscWise tem uma base promissora e já demonstra preocupação com multi-tenancy, autenticação, testes e deploy. Porém, antes do lançamento, precisa de um ciclo explícito de hardening, principalmente porque o produto manipula dados contábeis e documentos sensíveis.

Os bloqueadores mais importantes são: segredos versionados, fail-open de segredos/rate limit, docs públicas, CORS de produção, proteção de documentos, validação de isolamento multi-tenant e governança LGPD/IA. Corrigindo esses pontos, o produto terá uma base muito mais segura para entrar em beta e posteriormente escalar.
