# 🚀 ContaFlow - Production Deployment Checklist

**Data:** 28/04/2026  
**Executado por:** THE ARCHITECT (Omega v2)

---

## ✅ PRÉ-REQUISITOS

### Contas e Acessos
- [ ] Conta Railway ativa
- [ ] Conta Vercel ativa
- [ ] Repositório GitHub configurado
- [ ] API Keys disponíveis:
  - [ ] Anthropic Claude API Key
  - [ ] Voyage AI API Key

### Ferramentas CLI
```bash
# Instalar Railway CLI
npm install -g @railway/cli

# Instalar Vercel CLI
npm install -g vercel

# Verificar instalação
railway --version
vercel --version
```

---

## 🗄️ FASE 1: DEPLOY DO BACKEND (Railway)

### 1.1 Criar Projeto Railway
- [ ] Acessar [railway.app](https://railway.app)
- [ ] Criar novo projeto
- [ ] Conectar repositório GitHub
- [ ] Selecionar branch `main`

### 1.2 Adicionar PostgreSQL
- [ ] Adicionar serviço PostgreSQL
- [ ] Verificar `DATABASE_URL` gerada automaticamente
- [ ] Anotar credenciais do banco

### 1.3 Habilitar pgvector Extension
```bash
# Login no Railway
railway login

# Link ao projeto
railway link

# Conectar ao PostgreSQL e habilitar pgvector
railway run psql -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Verificar extensão
railway run psql -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```
- [ ] Extensão pgvector habilitada
- [ ] Verificação bem-sucedida

### 1.4 Adicionar Redis
- [ ] Adicionar serviço Redis
- [ ] Verificar `REDIS_URL` gerada automaticamente

### 1.5 Configurar Environment Variables

**Gerar SECRET_KEY:**
```bash
openssl rand -hex 32
```

**Adicionar no Railway:**
```env
# Auto-geradas
DATABASE_URL=<auto>
REDIS_URL=<auto>

# Configurar manualmente
SECRET_KEY=<generated-key>
ANTHROPIC_API_KEY=sk-ant-...
VOYAGE_API_KEY=pa-...
ALLOWED_ORIGINS=https://contaflow.vercel.app,https://contaflow-frontend.vercel.app
TOP_K_RESULTS=5
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
PYTHONUNBUFFERED=1
```

- [ ] Todas as variáveis configuradas
- [ ] SECRET_KEY gerada e adicionada
- [ ] API Keys adicionadas
- [ ] ALLOWED_ORIGINS configurado (atualizar após deploy do frontend)

### 1.6 Deploy Backend
```bash
# Fazer push para main
git add .
git commit -m "feat: production deployment"
git push origin main
```

- [ ] Push realizado
- [ ] Build iniciado no Railway
- [ ] Build concluído com sucesso
- [ ] Migrations executadas automaticamente
- [ ] Health check passou

### 1.7 Verificar Backend
```bash
# Obter URL do Railway
railway status

# Testar health endpoint
curl https://<railway-url>/api/v1/health
```

**Resposta esperada:**
```json
{
  "status": "healthy",
  "service": "contaflow-api",
  "version": "1.0.0"
}
```

- [ ] URL do backend anotada: `_______________________________`
- [ ] Health check retornou 200 OK
- [ ] Logs sem erros críticos

---

## 🎨 FASE 2: DEPLOY DO FRONTEND (Vercel)

### 2.1 Build Local (Teste)
```bash
cd frontend

# Atualizar .env com URL do Railway
echo "VITE_API_URL=https://<railway-url>" > .env

# Testar build
npm run build

# Verificar output
ls -la dist/
```

- [ ] Build local bem-sucedido
- [ ] Pasta `dist/` criada
- [ ] Sem erros TypeScript

### 2.2 Importar Projeto no Vercel
- [ ] Acessar [vercel.com](https://vercel.com)
- [ ] Clicar em "Add New" → "Project"
- [ ] Importar repositório do GitHub
- [ ] Configurar:
  - **Framework Preset:** Vite
  - **Root Directory:** `frontend`
  - **Build Command:** `npm run build`
  - **Output Directory:** `dist`

### 2.3 Configurar Environment Variables
```env
VITE_API_URL=https://<railway-url>
VITE_APP_NAME=ContaFlow
```

- [ ] Variáveis adicionadas no Vercel
- [ ] `VITE_API_URL` aponta para Railway

### 2.4 Deploy Frontend
- [ ] Clicar em "Deploy"
- [ ] Build iniciado
- [ ] Build concluído com sucesso
- [ ] Deploy realizado

### 2.5 Verificar Frontend
- [ ] URL do frontend anotada: `_______________________________`
- [ ] Página de login carrega
- [ ] Sem erros no console do navegador
- [ ] Assets carregando corretamente

---

## 🔄 FASE 3: CONFIGURAÇÃO FINAL

### 3.1 Atualizar CORS no Backend
```bash
# No Railway, atualizar ALLOWED_ORIGINS
ALLOWED_ORIGINS=https://<vercel-url>,https://<vercel-url-preview>
```

- [ ] CORS atualizado com URL do Vercel
- [ ] Backend reiniciado automaticamente
- [ ] Verificar logs do Railway

### 3.2 Testar Integração Frontend ↔ Backend
- [ ] Abrir frontend no navegador
- [ ] Abrir DevTools (F12) → Network
- [ ] Tentar fazer login (pode falhar, mas deve chamar API)
- [ ] Verificar requisição para `/api/v1/auth/login`
- [ ] Verificar headers CORS na resposta

### 3.3 Criar Primeiro Usuário (Seed)

**Opção 1: Via Railway CLI**
```bash
railway run python scripts/seed_admin.py
```

**Opção 2: Via Registro no Frontend**
- [ ] Acessar `/register`
- [ ] Preencher wizard (3 passos)
- [ ] Criar conta com plano Free

**Credenciais de Teste:**
```
Empresa: ContaFlow Demo
Nome: Admin User
Email: admin@contaflow.com
Senha: Admin@123456
Plano: Free
```

- [ ] Primeiro usuário criado
- [ ] Credenciais anotadas em local seguro

---

## 🧪 FASE 4: VALIDAÇÃO COMPLETA

### 4.1 Fluxo de Autenticação
- [ ] Login com credenciais criadas
- [ ] Redirect para `/dashboard`
- [ ] Token JWT armazenado no localStorage
- [ ] Tenant ID armazenado no localStorage
- [ ] Header com nome do usuário exibido

### 4.2 Dashboard
- [ ] Cards de métricas carregam (valores zerados OK)
- [ ] Gráfico renderiza (vazio OK)
- [ ] Sem erros no console

### 4.3 Base de Conhecimento
- [ ] Página `/knowledge` carrega
- [ ] Botão "Adicionar URL" funciona
- [ ] Adicionar URL de teste: `https://docs.python.org/3/`
- [ ] Status muda para "processing" ou "processed"
- [ ] Documento aparece na lista

### 4.4 Chat
- [ ] Página `/chat` carrega
- [ ] Botão "Nova Conversa" funciona
- [ ] Redirect para `/chat/:sessionId`
- [ ] Enviar mensagem de teste: "Olá, você pode me ajudar?"
- [ ] Resposta streaming em tempo real
- [ ] Mensagens aparecem no histórico

### 4.5 Widget
- [ ] Página `/widget` carrega
- [ ] Código de integração exibido
- [ ] Botão "Copiar" funciona
- [ ] Preview do widget carrega (pode estar vazio)

### 4.6 Billing
- [ ] Página `/billing` carrega
- [ ] Plano atual exibido (Free)
- [ ] Cards de planos exibidos

### 4.7 Settings
- [ ] Página `/settings` carrega
- [ ] Dados do usuário exibidos
- [ ] Tenant ID exibido

---

## 📊 FASE 5: MONITORING & LOGS

### 5.1 Backend Logs (Railway)
```bash
# Ver logs em tempo real
railway logs

# Verificar erros
railway logs | grep ERROR
```

- [ ] Logs acessíveis
- [ ] Sem erros críticos
- [ ] Requests sendo logados

### 5.2 Frontend Logs (Vercel)
- [ ] Acessar Deployments no Vercel
- [ ] Verificar Build Logs
- [ ] Verificar Function Logs (se houver)

### 5.3 Database
```bash
# Verificar migrations
railway run alembic current

# Verificar tabelas
railway run psql -c "\dt"

# Contar registros
railway run psql -c "SELECT COUNT(*) FROM tenants;"
railway run psql -c "SELECT COUNT(*) FROM users;"
```

- [ ] Migrations aplicadas: `_______________________________`
- [ ] Todas as tabelas criadas
- [ ] Dados de seed presentes

---

## 🔐 FASE 6: SEGURANÇA

### 6.1 Verificações de Segurança
- [ ] HTTPS habilitado (Railway + Vercel)
- [ ] CORS configurado corretamente
- [ ] JWT tokens com expiração (30 min)
- [ ] Passwords hasheados (bcrypt)
- [ ] API Keys não expostas no frontend
- [ ] Environment variables seguras

### 6.2 Testes de Segurança
```bash
# Testar endpoint sem autenticação
curl https://<railway-url>/api/v1/analytics/usage

# Deve retornar 401 Unauthorized
```

- [ ] Endpoints protegidos retornam 401
- [ ] Login com senha errada retorna 401
- [ ] X-Tenant-ID obrigatório em rotas protegidas

---

## 📝 FASE 7: DOCUMENTAÇÃO FINAL

### 7.1 URLs de Produção
```
Backend (Railway):  https://_______________________________
Frontend (Vercel):  https://_______________________________
Database (Railway): postgresql://_______________________________
Redis (Railway):    redis://_______________________________
```

### 7.2 Credenciais de Acesso
```
Email:    _______________________________
Senha:    _______________________________
Tenant ID: _______________________________
```

### 7.3 API Keys (Armazenar em Vault)
```
Anthropic: sk-ant-_______________________________
Voyage AI: pa-_______________________________
Secret Key: _______________________________
```

### 7.4 Próximos Passos
- [ ] Configurar custom domain (opcional)
- [ ] Configurar monitoring (Sentry, DataDog)
- [ ] Configurar backups automáticos
- [ ] Configurar alertas (PagerDuty, Opsgenie)
- [ ] Documentar runbook de operações
- [ ] Treinar equipe de suporte

---

## ✅ CHECKLIST FINAL

- [ ] ✅ Backend deployado e rodando
- [ ] ✅ Frontend deployado e rodando
- [ ] ✅ Database com pgvector habilitado
- [ ] ✅ Migrations aplicadas
- [ ] ✅ CORS configurado
- [ ] ✅ Primeiro usuário criado
- [ ] ✅ Login em produção realizado com sucesso
- [ ] ✅ Todas as páginas funcionando
- [ ] ✅ Chat com streaming SSE funcionando
- [ ] ✅ Base de conhecimento processando documentos
- [ ] ✅ Logs sem erros críticos
- [ ] ✅ URLs documentadas
- [ ] ✅ Credenciais armazenadas com segurança

---

## 🎉 DEPLOYMENT CONCLUÍDO

**Status:** ⏳ EM PROGRESSO  
**Última atualização:** 28/04/2026 00:18  
**Executado por:** THE ARCHITECT (Omega v2)

**Assinatura de Conclusão:**
```
[ ] Deployment validado e aprovado
[ ] Handoff para equipe de operações realizado
[ ] Documentação entregue
```

---

**THE ARCHITECT (Omega v2)**  
*"An Architect does not just build what is asked. An Architect builds what endures."*
