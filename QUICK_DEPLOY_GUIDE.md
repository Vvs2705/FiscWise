# ⚡ ContaFlow - Quick Deploy Guide

**Guia rápido para deploy em produção em 15 minutos**

---

## 🎯 Pré-requisitos

✅ Conta Railway  
✅ Conta Vercel  
✅ Anthropic API Key  
✅ Voyage AI API Key  
✅ Repositório GitHub com código

---

## 📦 PARTE 1: Backend (Railway) - 7 minutos

### 1. Criar Projeto (2 min)
```
1. Acesse railway.app
2. New Project → Deploy from GitHub
3. Selecione repositório ContaFlow
4. Branch: main
```

### 2. Adicionar Banco de Dados (2 min)
```
1. + New → Database → PostgreSQL
2. + New → Database → Redis
3. Aguarde provisionamento (30s)
```

### 3. Configurar Variáveis (2 min)
```bash
# Gerar SECRET_KEY
openssl rand -hex 32

# Adicionar no Railway (Settings → Variables):
SECRET_KEY=<cole-aqui>
ANTHROPIC_API_KEY=sk-ant-...
VOYAGE_API_KEY=pa-...
ALLOWED_ORIGINS=*
TOP_K_RESULTS=5
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

### 4. Habilitar pgvector (1 min)
```bash
# Instalar CLI
npm install -g @railway/cli

# Login e link
railway login
railway link

# Habilitar extensão
railway run psql -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 5. Deploy Automático
```
✅ Railway detecta railway.toml
✅ Build inicia automaticamente
✅ Migrations rodam via deploy-production.sh
✅ Health check em /api/v1/health
```

**✅ Backend URL:** `https://contaflow-production.up.railway.app`

---

## 🎨 PARTE 2: Frontend (Vercel) - 5 minutos

### 1. Importar Projeto (2 min)
```
1. Acesse vercel.com
2. Add New → Project
3. Import do GitHub
4. Configure:
   - Framework: Vite
   - Root Directory: frontend
   - Build Command: npm run build
   - Output Directory: dist
```

### 2. Configurar Variáveis (1 min)
```env
VITE_API_URL=https://contaflow-production.up.railway.app
VITE_APP_NAME=ContaFlow
```

### 3. Deploy (2 min)
```
1. Clique em Deploy
2. Aguarde build (1-2 min)
3. Deploy automático
```

**✅ Frontend URL:** `https://contaflow.vercel.app`

---

## 🔄 PARTE 3: Configuração Final - 3 minutos

### 1. Atualizar CORS (1 min)
```
No Railway → Settings → Variables:
ALLOWED_ORIGINS=https://contaflow.vercel.app
```

### 2. Criar Primeiro Usuário (2 min)
```
1. Acesse https://contaflow.vercel.app/register
2. Preencha:
   - Empresa: Sua Empresa
   - Nome: Seu Nome
   - Email: seu@email.com
   - Senha: SuaSenha123!
   - Plano: Free
3. Clique em "Criar Conta"
```

---

## ✅ Validação Rápida

### Backend
```bash
curl https://contaflow-production.up.railway.app/api/v1/health
# Deve retornar: {"status":"healthy",...}
```

### Frontend
```
1. Abra https://contaflow.vercel.app
2. Faça login
3. Veja dashboard
```

### Chat (Teste Completo)
```
1. Vá em "Conversas"
2. Clique "Nova Conversa"
3. Digite: "Olá!"
4. Veja resposta streaming
```

---

## 🐛 Troubleshooting Rápido

### Backend não inicia
```bash
railway logs
# Verificar erros de migration ou API keys
```

### Frontend não conecta
```
1. Verificar VITE_API_URL no Vercel
2. Verificar ALLOWED_ORIGINS no Railway
3. F12 → Console → Ver erros CORS
```

### pgvector não habilitado
```bash
railway run psql -c "CREATE EXTENSION IF NOT EXISTS vector;"
railway restart
```

---

## 📊 URLs Finais

| Serviço | URL |
|---------|-----|
| **Backend** | https://contaflow-production.up.railway.app |
| **Frontend** | https://contaflow.vercel.app |
| **API Docs** | https://contaflow-production.up.railway.app/docs |
| **Health** | https://contaflow-production.up.railway.app/api/v1/health |

---

## 🎉 Pronto!

Seu ContaFlow está no ar em **~15 minutos**! 🚀

**Próximos passos:**
- [ ] Adicionar documentos na Base de Conhecimento
- [ ] Testar chat com perguntas reais
- [ ] Configurar custom domain (opcional)
- [ ] Configurar monitoring (opcional)

---

**THE ARCHITECT (Omega v2)**  
*Deploy rápido, código limpo, sistema resiliente.*
