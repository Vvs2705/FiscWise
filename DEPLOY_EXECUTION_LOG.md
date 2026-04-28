# 🚀 ContaFlow - Deploy Execution Log

**Data de Início:** 28/04/2026 00:27  
**Executado por:** THE ARCHITECT (Omega v2)  
**Status:** 🔄 EM EXECUÇÃO

---

## 📋 INSTRUÇÕES PARA O EXECUTIVE DIRECTOR

Este documento guia a execução do deploy em produção. Siga os passos abaixo na ordem apresentada.

---

## FASE 1: PREPARAÇÃO (5 minutos)

### 1.1 Verificar Pré-requisitos

**Contas Necessárias:**
- [ ] Conta Railway criada em [railway.app](https://railway.app)
- [ ] Conta Vercel criada em [vercel.com](https://vercel.com)
- [ ] Repositório GitHub com código do ContaFlow

**API Keys Necessárias:**
- [ ] Anthropic Claude API Key (sk-ant-...)
- [ ] Voyage AI API Key (pa-...)

**Ferramentas CLI (Opcional):**
```bash
# Instalar Railway CLI (opcional, mas recomendado)
npm install -g @railway/cli

# Instalar Vercel CLI (opcional)
npm install -g vercel
```

---

## FASE 2: DEPLOY DO BACKEND (Railway) - 10 minutos

### 2.1 Criar Projeto Railway

**Passo a passo:**
1. Acesse [railway.app](https://railway.app)
2. Clique em **"New Project"**
3. Selecione **"Deploy from GitHub repo"**
4. Conecte sua conta GitHub (se ainda não conectou)
5. Selecione o repositório **ContaFlow**
6. Selecione a branch **main**
7. Aguarde Railway criar o projeto

**✅ Checkpoint:** Projeto Railway criado

---

### 2.2 Adicionar PostgreSQL

**Passo a passo:**
1. No projeto Railway, clique em **"+ New"**
2. Selecione **"Database"**
3. Selecione **"PostgreSQL"**
4. Aguarde provisionamento (~30 segundos)
5. Railway criará automaticamente a variável `DATABASE_URL`

**✅ Checkpoint:** PostgreSQL provisionado

---

### 2.3 Adicionar Redis

**Passo a passo:**
1. No projeto Railway, clique em **"+ New"**
2. Selecione **"Database"**
3. Selecione **"Redis"**
4. Aguarde provisionamento (~30 segundos)
5. Railway criará automaticamente a variável `REDIS_URL`

**✅ Checkpoint:** Redis provisionado

---

### 2.4 Habilitar pgvector Extension

**Opção A: Via Railway CLI (Recomendado)**
```bash
# Login no Railway
railway login

# Link ao projeto (selecione o projeto ContaFlow)
railway link

# Habilitar pgvector
railway run psql -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Verificar
railway run psql -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

**Opção B: Via Railway Web Console**
1. Clique no serviço PostgreSQL
2. Vá em "Connect"
3. Copie o comando psql
4. Execute localmente:
```bash
psql <DATABASE_URL> -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

**✅ Checkpoint:** pgvector habilitado

---

### 2.5 Configurar Environment Variables

**Gerar SECRET_KEY:**
```bash
# No terminal (Windows PowerShell)
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | % {[char]$_})

# Ou use um gerador online: https://randomkeygen.com/
```

**Adicionar Variáveis no Railway:**
1. Clique no serviço do backend (não PostgreSQL/Redis)
2. Vá em **"Variables"**
3. Clique em **"+ New Variable"**
4. Adicione as seguintes variáveis:

```env
SECRET_KEY=<cole-a-chave-gerada-acima>
ANTHROPIC_API_KEY=sk-ant-<sua-chave>
VOYAGE_API_KEY=pa-<sua-chave>
ALLOWED_ORIGINS=*
TOP_K_RESULTS=5
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
PYTHONUNBUFFERED=1
```

**IMPORTANTE:** 
- `DATABASE_URL` e `REDIS_URL` já foram criadas automaticamente
- `ALLOWED_ORIGINS=*` será atualizado depois com a URL do Vercel

**✅ Checkpoint:** Variáveis configuradas

---

### 2.6 Aguardar Deploy Automático

**O que acontece:**
1. Railway detecta `railway.toml` no repositório
2. Inicia build usando Dockerfile
3. Executa `scripts/deploy-production.sh`
4. Aplica migrations do Alembic
5. Inicia aplicação com Uvicorn
6. Executa health check em `/api/v1/health`

**Acompanhar:**
1. Vá em **"Deployments"** no Railway
2. Clique no deployment em andamento
3. Veja os logs em tempo real

**Aguarde até ver:**
```
✅ Migrations aplicadas
✅ pgvector extension enabled
✅ Application started
✅ Health check passed
```

**✅ Checkpoint:** Backend deployado com sucesso

---

### 2.7 Anotar URL do Backend

**Obter URL:**
1. No serviço backend, vá em **"Settings"**
2. Vá em **"Domains"**
3. Copie a URL gerada (ex: `contaflow-production.up.railway.app`)

**Testar:**
```bash
curl https://<sua-url-railway>/api/v1/health
```

**Resposta esperada:**
```json
{
  "status": "healthy",
  "service": "contaflow-api",
  "version": "1.0.0"
}
```

**📝 ANOTE AQUI:**
```
Backend URL: https://_______________________________________
```

**✅ Checkpoint:** Backend acessível e saudável

---

## FASE 3: DEPLOY DO FRONTEND (Vercel) - 7 minutos

### 3.1 Importar Projeto no Vercel

**Passo a passo:**
1. Acesse [vercel.com](https://vercel.com)
2. Clique em **"Add New"** → **"Project"**
3. Clique em **"Import Git Repository"**
4. Conecte sua conta GitHub (se ainda não conectou)
5. Selecione o repositório **ContaFlow**
6. Clique em **"Import"**

**✅ Checkpoint:** Repositório importado

---

### 3.2 Configurar Build Settings

**Configure os seguintes campos:**

| Campo | Valor |
|-------|-------|
| **Framework Preset** | Vite |
| **Root Directory** | `frontend` |
| **Build Command** | `npm run build` |
| **Output Directory** | `dist` |
| **Install Command** | `npm install` |

**✅ Checkpoint:** Build settings configurados

---

### 3.3 Configurar Environment Variables

**Antes de fazer deploy, adicione as variáveis:**

1. Clique em **"Environment Variables"**
2. Adicione:

```env
VITE_API_URL=https://<sua-url-railway>
VITE_APP_NAME=ContaFlow
```

**IMPORTANTE:** Substitua `<sua-url-railway>` pela URL anotada na Fase 2.7

**✅ Checkpoint:** Variáveis configuradas

---

### 3.4 Fazer Deploy

**Passo a passo:**
1. Clique em **"Deploy"**
2. Aguarde build (~2-3 minutos)
3. Acompanhe logs de build

**Aguarde até ver:**
```
✅ Installing dependencies
✅ Building application
✅ Deployment ready
```

**✅ Checkpoint:** Frontend deployado

---

### 3.5 Anotar URL do Frontend

**Obter URL:**
1. Após deploy, Vercel mostrará a URL
2. Copie a URL (ex: `contaflow.vercel.app`)

**Testar:**
1. Abra a URL no navegador
2. Deve carregar a página de login

**📝 ANOTE AQUI:**
```
Frontend URL: https://_______________________________________
```

**✅ Checkpoint:** Frontend acessível

---

## FASE 4: CONFIGURAÇÃO FINAL - 5 minutos

### 4.1 Atualizar CORS no Backend

**Passo a passo:**
1. Volte ao Railway
2. Vá no serviço backend → **"Variables"**
3. Edite a variável `ALLOWED_ORIGINS`
4. Substitua `*` por:
```
https://<sua-url-vercel>,https://<sua-url-vercel-preview>
```

**Exemplo:**
```
ALLOWED_ORIGINS=https://contaflow.vercel.app,https://contaflow-git-main.vercel.app
```

5. Salve
6. Railway reiniciará automaticamente o backend

**✅ Checkpoint:** CORS atualizado

---

### 4.2 Testar Integração Frontend ↔ Backend

**Passo a passo:**
1. Abra o frontend no navegador
2. Abra DevTools (F12)
3. Vá na aba **"Network"**
4. Tente fazer login (pode falhar, mas deve chamar a API)
5. Verifique se há requisição para `/api/v1/auth/login`
6. Verifique se não há erros de CORS

**✅ Checkpoint:** Integração funcionando (sem erros CORS)

---

### 4.3 Criar Primeiro Usuário

**Opção A: Via Frontend (Recomendado)**
1. Acesse `https://<sua-url-vercel>/register`
2. Preencha o wizard:

**Passo 1 - Empresa:**
```
Nome da Empresa: ContaFlow Demo
```

**Passo 2 - Usuário:**
```
Nome Completo: Admin User
Email: admin@contaflow.com
Senha: Admin@123456
```

**Passo 3 - Plano:**
```
Selecione: Free
```

3. Clique em **"Criar Conta"**
4. Deve redirecionar para `/dashboard`

**Opção B: Via Railway CLI**
```bash
railway run python scripts/seed_admin.py
```

**📝 ANOTE AS CREDENCIAIS:**
```
Email: _______________________________________
Senha: _______________________________________
Tenant ID: ___________________________________ (visível em /settings)
```

**✅ Checkpoint:** Primeiro usuário criado

---

## FASE 5: VALIDAÇÃO COMPLETA - 10 minutos

### 5.1 Testar Autenticação

- [ ] Login com credenciais criadas
- [ ] Redirect para `/dashboard`
- [ ] Nome do usuário aparece no header
- [ ] Botão "Sair" funciona

**✅ Checkpoint:** Autenticação OK

---

### 5.2 Testar Dashboard

- [ ] Cards de métricas carregam (valores zerados OK)
- [ ] Gráfico renderiza (vazio OK)
- [ ] Sem erros no console (F12)

**✅ Checkpoint:** Dashboard OK

---

### 5.3 Testar Base de Conhecimento

**Adicionar documento de teste:**
1. Vá em **"Base de Conhecimento"**
2. Clique em **"Adicionar URL"**
3. Cole: `https://docs.python.org/3/tutorial/index.html`
4. Título: `Python Tutorial`
5. Clique em **"Adicionar"**
6. Aguarde status mudar para `processing` ou `processed`

- [ ] URL adicionada
- [ ] Status atualiza
- [ ] Documento aparece na lista

**✅ Checkpoint:** Knowledge Base OK

---

### 5.4 Testar Chat (TESTE CRÍTICO)

**Criar conversa:**
1. Vá em **"Conversas"**
2. Clique em **"Nova Conversa"**
3. Digite: `Olá! Você pode me ajudar com Python?`
4. Envie

**Verificar:**
- [ ] Mensagem enviada aparece
- [ ] Resposta começa a aparecer em tempo real (streaming)
- [ ] Resposta completa é exibida
- [ ] Mensagens ficam no histórico

**✅ Checkpoint:** Chat com SSE streaming OK

---

### 5.5 Testar Widget

1. Vá em **"Widget"**
2. Código de integração é exibido
3. Botão "Copiar" funciona
4. Preview carrega (pode estar vazio)

**✅ Checkpoint:** Widget OK

---

### 5.6 Testar Billing

1. Vá em **"Billing"**
2. Plano atual exibido (Free)
3. Cards de planos exibidos

**✅ Checkpoint:** Billing OK

---

### 5.7 Testar Settings

1. Vá em **"Configurações"**
2. Dados do usuário exibidos
3. Tenant ID exibido

**✅ Checkpoint:** Settings OK

---

## FASE 6: VERIFICAÇÃO DE LOGS - 5 minutos

### 6.1 Backend Logs (Railway)

```bash
# Via CLI
railway logs

# Ou via Web
# Railway → Serviço Backend → Deployments → View Logs
```

**Verificar:**
- [ ] Sem erros críticos
- [ ] Requests sendo logados
- [ ] Migrations aplicadas

**✅ Checkpoint:** Logs OK

---

### 6.2 Frontend Logs (Vercel)

1. Vercel → Projeto → Deployments
2. Clique no deployment atual
3. Veja "Build Logs"

**Verificar:**
- [ ] Build sem erros
- [ ] Sem warnings críticos

**✅ Checkpoint:** Build logs OK

---

### 6.3 Database Verification

```bash
# Via Railway CLI
railway run alembic current

# Verificar tabelas
railway run psql -c "\dt"

# Contar registros
railway run psql -c "SELECT COUNT(*) FROM tenants;"
railway run psql -c "SELECT COUNT(*) FROM users;"
```

**Verificar:**
- [ ] Migration atual: `<anotar-aqui>`
- [ ] Todas as 12 tabelas criadas
- [ ] Pelo menos 1 tenant e 1 user

**✅ Checkpoint:** Database OK

---

## FASE 7: DOCUMENTAÇÃO FINAL

### 7.1 URLs de Produção

```
Backend (Railway):  https://_______________________________________
Frontend (Vercel):  https://_______________________________________
API Docs:           https://_______________________________________/docs
Health Check:       https://_______________________________________/api/v1/health
```

### 7.2 Credenciais de Acesso

```
Email:              _______________________________________
Senha:              _______________________________________
Tenant ID:          _______________________________________
```

### 7.3 API Keys (Guardar em local seguro)

```
Anthropic:          sk-ant-_______________________________________
Voyage AI:          pa-_______________________________________
Secret Key:         _______________________________________
```

---

## ✅ CHECKLIST FINAL DE VALIDAÇÃO

- [ ] ✅ Backend deployado e rodando
- [ ] ✅ Frontend deployado e rodando
- [ ] ✅ PostgreSQL com pgvector habilitado
- [ ] ✅ Redis configurado
- [ ] ✅ Migrations aplicadas
- [ ] ✅ CORS configurado
- [ ] ✅ Primeiro usuário criado
- [ ] ✅ Login em produção funcionando
- [ ] ✅ Dashboard carregando
- [ ] ✅ Base de conhecimento processando documentos
- [ ] ✅ Chat com SSE streaming funcionando
- [ ] ✅ Widget configurado
- [ ] ✅ Billing exibindo planos
- [ ] ✅ Settings exibindo dados
- [ ] ✅ Logs sem erros críticos
- [ ] ✅ URLs documentadas
- [ ] ✅ Credenciais armazenadas

---

## 🎉 DEPLOY CONCLUÍDO

**Status:** ⏳ AGUARDANDO EXECUÇÃO  
**Última atualização:** 28/04/2026 00:27

**Quando todos os checkpoints estiverem marcados, o deploy estará completo!**

---

**THE ARCHITECT (Omega v2)**  
*"An Architect does not just build what is asked. An Architect builds what endures."*
