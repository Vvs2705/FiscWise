# 🚀 ContaFlow - Instruções de Deploy Manual

**Executive Director**, o código do ContaFlow está 100% pronto. Devido a problemas com o repositório Git (inicializado no Desktop em vez do diretório do projeto), precisamos fazer o deploy manualmente via Railway e Vercel.

---

## ✅ STATUS ATUAL

- ✅ Código backend completo (FastAPI + PostgreSQL + Redis + pgvector)
- ✅ Código frontend completo (React + TypeScript + Vite)
- ✅ Documentação completa
- ✅ API Keys recebidas:
  - Voyage AI: `pa-P7-iLldGgSn6XpoCPdraE2MysnkeSzq5ilD71wvXlZK`
  - Claude: `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`

---

## 🎯 OPÇÕES DE DEPLOY

### OPÇÃO 1: Deploy Manual via Railway Dashboard (RECOMENDADO)

#### Passo 1: Criar Projeto Railway
1. Acesse https://railway.app
2. Faça login com GitHub
3. Clique em "New Project"
4. Selecione "Empty Project"

#### Passo 2: Adicionar PostgreSQL
1. No projeto, clique "+ New"
2. Selecione "Database" → "PostgreSQL"
3. Aguarde provisionamento

#### Passo 3: Adicionar Redis
1. Clique "+ New" novamente
2. Selecione "Database" → "Redis"
3. Aguarde provisionamento

#### Passo 4: Habilitar pgvector
1. Clique no serviço PostgreSQL
2. Vá em "Connect"
3. Copie a DATABASE_URL
4. Execute localmente:
```bash
psql "postgresql://..." -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

#### Passo 5: Deploy Backend
1. Clique "+ New" → "GitHub Repo"
2. Conecte o repositório ContaFlow
3. Configure Root Directory: `backend`
4. Adicione variáveis de ambiente:

```env
SECRET_KEY=<gerar-com-openssl-rand-base64-64>
ANTHROPIC_API_KEY=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
VOYAGE_API_KEY=pa-P7-iLldGgSn6XpoCPdraE2MysnkeSzq5ilD71wvXlZK
ALLOWED_ORIGINS=*
TOP_K_RESULTS=5
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
PYTHONUNBUFFERED=1
```

5. Railway detectará `railway.toml` e fará deploy automático

#### Passo 6: Deploy Frontend (Vercel)
1. Acesse https://vercel.com
2. Clique "Add New" → "Project"
3. Importe repositório ContaFlow
4. Configure:
   - Framework: Vite
   - Root Directory: `frontend`
   - Build Command: `npm run build`
   - Output Directory: `dist`
5. Adicione variáveis:
```env
VITE_API_URL=<URL-DO-RAILWAY>
VITE_APP_NAME=ContaFlow
```
6. Deploy

---

### OPÇÃO 2: Corrigir Git e Fazer Push

Se preferir corrigir o Git:

```bash
# 1. Remover .git do Desktop
Remove-Item -Recurse -Force "C:\Users\VINICIUS\Desktop\.git"

# 2. Ir para o diretório correto
cd "C:\Users\VINICIUS\Videos\MEUS PROJETOS\ContaFlow"

# 3. Inicializar Git
git init
git branch -M main

# 4. Configurar identidade
git config user.email "vsouz009@gmail.com"
git config user.name "Vvs2705"

# 5. Adicionar remote
git remote add origin https://github.com/Vvs2705/ContaFlow.git

# 6. Adicionar arquivos
git add .

# 7. Commit
git commit -m "feat: ContaFlow complete - production ready"

# 8. Push (force se necessário)
git push -u origin main --force
```

---

## 📝 PRÓXIMOS PASSOS APÓS DEPLOY

1. ✅ Anotar URLs de produção
2. ✅ Atualizar CORS no backend com URL do Vercel
3. ✅ Criar primeiro usuário via `/register`
4. ✅ Testar fluxo completo
5. ✅ Validar chat com SSE streaming

---

## 🆘 SUPORTE

Se precisar de ajuda, consulte:
- `DEPLOY_EXECUTION_LOG.md` - Guia passo a passo detalhado
- `QUICK_DEPLOY_GUIDE.md` - Deploy rápido em 15 minutos
- `PRODUCTION_DEPLOYMENT_CHECKLIST.md` - Checklist completo

---

**THE ARCHITECT (Omega v2)**  
*"An Architect does not just build what is asked. An Architect builds what endures."*
