# RAILWAY DEPLOY AGENT — ContaFlow Backend

## MISSÃO
Você é um engenheiro DevOps autônomo. Sua missão é garantir que o backend ContaFlow esteja **100% operacional no Railway** com healthcheck verde antes de encerrar.

---

## CONTEXTO DO PROJETO

### Stack
- **Backend**: FastAPI 0.115 + Python 3.12
- **Banco**: PostgreSQL 16 + pgvector (extensão vetorial)
- **Cache**: Redis 7
- **ORM**: SQLAlchemy 2.0 async + Alembic
- **AI**: Voyage AI (embeddings 1024 dims) + Anthropic Claude
- **Deploy**: Railway (Dockerfile + railway.toml)

### Repositório GitHub
```
https://github.com/Vvs2705/ContaFlow.git
Branch: main
```

### Railway — IDs do Projeto
```
Project ID:     00d3b902-6f5a-4677-ac35-9dd62a25a322
Service ID:     c6943d82-ca06-449e-884e-fe187aea4a72  (ContaFlow app)
Environment ID: 2c94a254-32bc-4a8b-9c02-44c3d365a878  (production)
URL pública:    https://contaflow-production.up.railway.app
```

### railway.toml (em backend/)
```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"
[deploy]
startCommand = "bash scripts/deploy-production.sh"
healthcheckPath = "/api/v1/health"
healthcheckTimeout = 100
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
```

---

## ESTADO ATUAL

### O que já foi feito
1. ✅ Repositório GitHub criado e código pushado (`main`)
2. ✅ Railway configurado: Postgres + Redis + ContaFlow service
3. ✅ 16 variáveis de ambiente configuradas no Railway
4. ✅ Root directory = `backend/`
5. ✅ Build do Dockerfile: **SUCESSO**
6. ✅ Deploy do container: **SUCESSO**
7. ❌ Healthcheck `/api/v1/health`: **FALHOU**

### Causa Raiz Identificada e Corrigida
O Railway injeta `DATABASE_URL=postgresql://user:pass@host/db` mas o SQLAlchemy async exige `postgresql+asyncpg://`. O app crashava no import antes de subir.

**Fix aplicado** (já no repositório):
- `backend/app/core/config.py`: validator Pydantic que converte a URL
- `backend/alembic/env.py`: função `get_url()` com a mesma conversão

---

## VARIÁVEIS DE AMBIENTE NO RAILWAY

```
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
JWT_SECRET_KEY=contaflow-jwt-super-secret-key-2024-change-me
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ANTHROPIC_API_KEY=<já configurada pelo usuário>
VOYAGE_API_KEY=<já configurada pelo usuário>
EMBEDDING_DIMENSIONS=1024
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K_RESULTS=5
PYTHONUNBUFFERED=1
ENVIRONMENT=production
LOG_LEVEL=INFO
ALLOWED_ORIGINS=http://localhost:3000
PUBLIC_URL=https://contaflow-production.up.railway.app
```

---

## TAREFAS EM ORDEM DE PRIORIDADE

### TAREFA 1 — Verificar deploy pós-fix
Acesse o Railway e verifique se o deploy mais recente passou no healthcheck.

- URL do serviço: `https://railway.com/project/00d3b902-6f5a-4677-ac35-9dd62a25a322/service/c6943d82-ca06-449e-884e-fe187aea4a72?environmentId=2c94a254-32bc-4a8b-9c02-44c3d365a878`
- Se ainda estiver em build, aguarde (~2 min)
- Se falhou novamente, leia os logs e diagnostique

### TAREFA 2 — Testar healthcheck publicamente
Quando o status for "Active", faça uma requisição GET:
```
GET https://contaflow-production.up.railway.app/api/v1/health
```
Resposta esperada:
```json
{"status": "healthy", "service": "contaflow-api", "version": "1.0.0"}
```

Também teste:
```
GET https://contaflow-production.up.railway.app/health
GET https://contaflow-production.up.railway.app/docs
```

### TAREFA 3 — Verificar pgvector no PostgreSQL
A migration `394d97d5da14` cria a extensão com `CREATE EXTENSION IF NOT EXISTS vector`. Verifique se ela foi executada.

Se necessário, conecte ao PostgreSQL Railway e execute:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
SELECT * FROM pg_extension WHERE extname = 'vector';
```

### TAREFA 4 — Verificar todas as migrations
O banco deve ter todas as 5 tabelas principais:
- `tenants`, `users` (migration inicial)
- `documents`, `document_chunks` (pgvector migration)
- `chat_sessions`, `chat_messages` (chat migration)
- tabelas de analytics

Verifique com:
```
GET https://contaflow-production.up.railway.app/api/v1/health/ready
```
Resposta esperada:
```json
{"status": "ready", "database": "connected", "service": "contaflow-api"}
```

### TAREFA 5 — Se deploy falhar novamente: diagnóstico
Leia os logs do Railway. Os erros mais prováveis são:

**Erro A — Import error na startup:**
```
ModuleNotFoundError: No module named 'XXX'
```
→ Adicione o pacote ao `requirements.txt` e faça push

**Erro B — Alembic migration falha:**
```
sqlalchemy.exc.OperationalError: could not connect to server
```
→ Verifique se `DATABASE_URL` está sendo injetada corretamente

**Erro C — Port binding:**
```
uvicorn: error: Address already in use
```
→ Verifique o `deploy-production.sh` — deve usar `${PORT:-8000}`

**Erro D — pgvector não disponível:**
```
ProgrammingError: type "vector" does not exist
```
→ Habilite a extensão manualmente no PostgreSQL do Railway

### TAREFA 6 — Ajustar healthcheckTimeout se necessário
Se as migrations demorarem mais de 100s, atualize o `backend/railway.toml`:
```toml
healthcheckTimeout = 300
```
Faça push e redeploy.

---

## ARQUIVOS CHAVE DO PROJETO

```
ContaFlow/
├── backend/
│   ├── Dockerfile
│   ├── railway.toml
│   ├── requirements.txt
│   ├── scripts/
│   │   └── deploy-production.sh
│   ├── alembic/
│   │   ├── env.py              ← fix DATABASE_URL aplicado
│   │   └── versions/
│   │       ├── a2f1a2feaa87_initial_schema.py
│   │       ├── 394d97d5da14_add_knowledge_base_pgvector_tables.py
│   │       ├── 43813716b407_alter_embedding_dim_to_1024.py
│   │       ├── 68c375818212_add_chat_tables.py
│   │       └── d9e4ace766be_add_analytics_tables.py
│   └── app/
│       ├── main.py
│       ├── core/
│       │   ├── config.py       ← fix DATABASE_URL aplicado
│       │   └── deps.py
│       └── api/v1/endpoints/
│           └── health.py
```

---

## CRITÉRIO DE SUCESSO

O deploy está completo quando:

1. ✅ Railway mostra status **"Active"** (verde) no serviço ContaFlow
2. ✅ `GET /api/v1/health` retorna `{"status": "healthy"}`
3. ✅ `GET /api/v1/health/ready` retorna `{"status": "ready", "database": "connected"}`
4. ✅ `GET /docs` carrega o Swagger UI sem erro
5. ✅ Nenhum erro crítico nos logs de deploy

---

## APÓS CONCLUSÃO

Informe ao usuário (Vinicius):
- URL pública do backend funcionando
- Status de cada serviço (Postgres, Redis, ContaFlow)
- Próximos passos: **Phase 09 — Widget** via Cline

---

## IMPORTANTE

- Comunique em **português brasileiro**
- Todo código/commit em **inglês**
- Nunca hardcode credenciais
- Se encontrar novos erros não listados acima, diagnostique, corrija e faça push autonomamente
- O repositório GitHub já está conectado ao Railway — qualquer push dispara deploy automático
