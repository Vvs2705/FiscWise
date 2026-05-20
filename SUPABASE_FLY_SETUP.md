# Supabase + Fly.io — Setup Completo

## 📋 Pré-requisitos Completados

✅ Supabase criado: https://lkgmgbieottygodrdubi.supabase.co  
✅ Chaves guardadas na memória (nunca commitadas)  
✅ fly.toml criado  
✅ GitHub Actions workflow criado  

---

## 🔧 SETUP MANUAL NECESSÁRIO

### 1️⃣ **Supabase: Obter DATABASE_URL**

```
Supabase Dashboard → Project → Settings → Database
```

**Copie a connection string:**
```
postgresql://postgres.[PROJECT]:[PASSWORD]@aws-0-[region].pooler.supabase.com:6543/postgres
```

**Transforme em asyncpg:**
```
postgresql+asyncpg://postgres.[PROJECT]:[PASSWORD]@aws-0-[region].pooler.supabase.com:6543/postgres
```

---

### 2️⃣ **Fly.io: Criar e Conectar**

```bash
# 1. Login no Fly.io (se não fez ainda)
flyctl auth login

# 2. Criar app (primeira vez)
flyctl app create contaflow --region gru

# 3. Definir secrets (use os valores que você tem)
flyctl secrets set \
  SUPABASE_DATABASE_URL="postgresql+asyncpg://..." \
  JWT_SECRET_KEY="openssl rand -hex 64 (gere um novo)" \
  SUPABASE_SECRET_KEY="sb_secret_yi9NzmY8a6XDSTQDAwOIpQ_OHR-eFV1"
```

**Ou via Fly.io Dashboard:**
```
App → contaflow → Secrets → Add Secret
```

---

### 3️⃣ **GitHub: Configurar Secrets**

```
GitHub → Settings → Secrets and variables → Actions
```

**Crie estes 3 secrets:**

| Secret | Valor |
|--------|-------|
| `FLY_API_TOKEN` | Token gerado em Fly.io (`flyctl tokens create deploy`) |
| `SUPABASE_DATABASE_URL` | DATABASE_URL com asyncpg (de Supabase) |
| `JWT_SECRET_KEY` | Nova chave: `openssl rand -hex 64` |
| `SUPABASE_SECRET_KEY` | `sb_secret_yi9NzmY8a6XDSTQDAwOIpQ_OHR-eFV1` |

---

### 4️⃣ **Supabase: Criar Migrations no Banco**

```bash
cd backend

# Rodar migrations localmente (com DATABASE_URL)
export DATABASE_URL="postgresql+asyncpg://..."
python -m alembic upgrade head
```

**Ou deixar Fly.io rodar na primeira deploy:**
- fly.toml está configurado para rodar migrations automaticamente

---

### 5️⃣ **Primeira Deploy**

```bash
# Opção 1: Via GitHub (automático ao fazer push)
git push origin main
# GitHub Actions vai:
# - Build Docker image
# - Deploy para Fly.io
# - Rodar migrations
# - Health check

# Opção 2: Manual via CLI
flyctl deploy --remote-only
```

---

## ✅ Checklist Final

- [ ] Supabase DATABASE_URL obtido
- [ ] Fly.io app criado (`flyctl app create contaflow`)
- [ ] Fly.io secrets configurados (`flyctl secrets set ...`)
- [ ] GitHub secrets criados
- [ ] Migrations rodadas em Supabase (via `alembic upgrade head` local ou Fly.io)
- [ ] Push para main branch
- [ ] Validar deploy em https://contaflow.fly.dev/api/v1/health

---

## 🔗 URLs Importantes

| Serviço | URL |
|---------|-----|
| **App Backend** | https://contaflow.fly.dev |
| **Health Check** | https://contaflow.fly.dev/api/v1/health |
| **Supabase Dashboard** | https://app.supabase.com/project/lkgmgbieottygodrdubi |
| **Fly.io Dashboard** | https://fly.io/apps/contaflow |
| **GitHub Actions** | https://github.com/Vvs2705/ContaFlow/actions |

---

## 🆘 Troubleshooting

| Erro | Solução |
|------|---------|
| `Error: could not connect to database` | DATABASE_URL inválida, check em Supabase |
| `JWT validation failed` | JWT_SECRET_KEY não set ou vazio |
| `502 Bad Gateway` | Migrations não rodaram, rodar manual: `flyctl ssh console` e `alembic upgrade head` |
| `Health check timeout` | App não subiu, check logs: `flyctl logs` |

---

## 📝 Próximas Fases

**Phase 6:** Notificações de prazos (Cloud Scheduler em Supabase)  
**Phase 7:** Integração com APIs certificados digitais  
**Phase 8:** Dashboard financeiro avançado  

---

**Você está a 1 push de distância do production! 🚀**
