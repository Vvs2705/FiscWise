# Railway Configuration — ContaFlow Phase 5 Deploy

## Variáveis de Ambiente Obrigatórias

Configure estas variáveis no Railway dashboard para o serviço `backend`:

### 🔒 Credenciais (Geradas/Fornecidas)

```env
# Banco de dados PostgreSQL (fornecido pelo Railway plugin)
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname

# JWT (Gerar: openssl rand -hex 64)
JWT_SECRET_KEY=<gerar-com-openssl-rand-hex-64>

# Redis (se usar cache, fornecido pelo Railway plugin)
REDIS_URL=redis://:password@host:6379/0
```

### 🔧 Aplicação

```env
ENVIRONMENT=production
DEBUG=False
APP_NAME=ContaFlow
APP_VERSION=1.0.0

# Frontend URL (para CORS)
PUBLIC_URL=https://api.contabilidadeflow.com.br
ALLOWED_ORIGINS=https://contabilidadeflow.com.br,https://www.contabilidadeflow.com.br

# AI Services (opcional, pode deixar vazio se não usar)
ANTHROPIC_API_KEY=
VOYAGE_API_KEY=
```

## Configuração no Railway Dashboard

1. **Vá para:** https://railway.app/project/...
2. **Selecione:** Serviço `backend`
3. **Abra:** Variables
4. **Cole:** Variáveis acima (Railway tira as credenciais de plugins PostgreSQL/Redis automaticamente)
5. **Salve:** Redeploy acontece automaticamente

## PostgreSQL Setup

Railway deve ter plugin PostgreSQL conectado. Se não:

1. **Vá para:** Plugin Store
2. **Procure:** PostgreSQL
3. **Clique:** Add
4. **Railway gera automaticamente:** DATABASE_URL

## Comandos que Railway executa

### Build

```bash
cd backend
pip install -r requirements.txt
```

### Start

```bash
cd backend
python -m alembic upgrade head  # Migrations
gunicorn app.main:app --bind 0.0.0.0:$PORT
```

## Healthcheck

Railway está configurado para validar:
- GET `/api/v1/health` → deve retornar 200
- GET `/api/v1/ready` (com X-Tenant-ID header) → deve retornar 200 ou 503

Se falhar, Railway mata o container e faz retry.

## Verificação Pós-Deploy

Após Railway fazer redeploy (leva ~5 min):

```bash
# Health check
curl https://api.contabilidadeflow.com.br/api/v1/health

# Status
curl -H "X-Tenant-ID: 00000000-0000-0000-0000-000000000000" \
  https://api.contabilidadeflow.com.br/api/v1/ready
```

Esperado: `{"status": "ok"}` e `{"status": "ready"}`

## Se Houver Erro

1. **Vá para:** Railway Dashboard → Logs
2. **Procure:** Erro de DATABASE_URL, JWT_SECRET_KEY, REDIS_URL
3. **Corrija:** Adicione variável faltante
4. **Redeploy:** Manual ou automático (depende da config)

## Frontend (Vercel)

**Vercel já está configurado em:** https://contabilidadeflow.com.br

Variáveis de ambiente necessárias:

```env
VITE_API_URL=https://api.contabilidadeflow.com.br
```

Se houver erro, atualizar em Vercel Dashboard → Settings → Environment Variables

## Troubleshooting

| Erro | Solução |
|------|---------|
| 502 Bad Gateway | Railway backend não subiu, check logs |
| 401 Unauthorized | JWT_SECRET_KEY não set ou diferente entre deploys |
| 503 Service Unavailable | Database connection failed, check DATABASE_URL |
| CORS error | ALLOWED_ORIGINS não inclui domínio do frontend |

---

**Próximos passos:**
1. Verificar que Railway está rodando
2. Teste manual: registre user, crie client/deadline/documento/certificado
3. Validar tenant isolation
4. Validar que dashboard mostra dados reais
