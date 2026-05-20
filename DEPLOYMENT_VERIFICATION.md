# 🔍 Verificação das 3 Frentes — ContaFlow Production

**Data:** 2026-05-20  
**Status:** Verificação em progresso  

---

## 1️⃣ VERCEL (Frontend)

### ✅ Verificar

```
Abra: https://contabilidadeflow.com.br
```

**Esperado:**
- [ ] Página carrega
- [ ] Navbar com menu (Dashboard, Clientes, Prazos, Documentos, Certificados, Financeiro)
- [ ] No console: sem erros críticos
- [ ] Network requests → API_URL apontando para backend

**Se tudo OK:**
```
VERCEL: ✅ FUNCIONANDO
```

---

## 2️⃣ SUPABASE (Database)

### ✅ Verificar

```
Supabase Dashboard → https://app.supabase.com/project/lkgmgbieottygodrdubi
```

**Checar:**
- [ ] Project está ativo (Status: Healthy)
- [ ] Database → Tables: 
  - `users` ✅
  - `tenants` ✅
  - `accounting_clients` ✅
  - `deadline_items` ✅
  - `client_documents` ✅
  - `digital_certificates` ✅
  - `account_receivables` ✅
- [ ] Connection pooler está ativo
- [ ] Storage bucket criado (se configurado)

**Se tudo OK:**
```
SUPABASE: ✅ FUNCIONANDO
```

---

## 3️⃣ FLY.IO (Backend)

### ✅ Verificar — Opção A: Dashboard

```
Fly.io Dashboard → https://fly.io/apps/contaflow
```

**Checar:**
- [ ] App Status: Running (verde)
- [ ] Machines: ≥1 máquina ativa
- [ ] Recent Deploys: commit recente (e805912)
- [ ] Logs: sem erros críticos

### ✅ Verificar — Opção B: CLI (PowerShell)

```powershell
flyctl status --app contaflow
flyctl logs --app contaflow --lines 50
```

**Esperado:**
```
App: contaflow
  Deployment Status
    ID          VERSION REGION DESIRED STATUS HEALTH
    xxxxx       1       gru    2       running passed
    
Logs:
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Alembic successfully upgraded to head
```

### ✅ Verificar — Health Check

```bash
# Via curl
curl https://contaflow.fly.dev/api/v1/health

# Esperado: 
# {"status": "ok"}
```

**Se tudo OK:**
```
FLY.IO: ✅ FUNCIONANDO
```

---

## 4️⃣ INTEGRAÇÃO (Frontend → Backend → Database)

### ✅ Teste Completo

**No browser (https://contabilidadeflow.com.br):**

1. **Registrar novo usuário:**
   ```
   Email: teste@contaflow.dev
   Senha: TestPass123!
   Tenant: TestTenant
   ```
   - [ ] POST /api/v1/auth/register retorna JWT
   - [ ] Supabase: novo registro em `users` table

2. **Dashboard deve mostrar:**
   ```
   0 Clientes
   0 Prazos
   0 Certificados vencendo
   0 Recebiveis pendentes
   ```
   - [ ] GET /api/v1/dashboard/overview retorna dados

3. **Criar Cliente:**
   - Click "Clientes" → "Novo Cliente"
   - Preenche: Nome, CNPJ, Tipo, Regime
   - Click "Salvar"
   - [ ] POST /api/v1/clients cria em Supabase
   - [ ] Cliente aparece na tabela
   - [ ] Supabase: novo registro em `accounting_clients`

4. **Criar Prazo:**
   - Click "Prazos" → "Novo Prazo"
   - Tipo: "ECF", Prazo: amanhã, Cliente: o criado acima
   - [ ] POST /api/v1/deadlines salva em Supabase
   - [ ] Aparece em cards

5. **Criar Documento:**
   - Click "Documentos" → "Novo Documento"
   - Tipo: "RPA", URL: "https://example.com/doc.pdf"
   - [ ] POST /api/v1/documents salva
   - [ ] Supabase: novo registro

6. **Criar Certificado:**
   - Click "Certificados" → "Novo Certificado"
   - N°: 123456, Tipo: A1, Vencimento: 2026-12-31
   - [ ] POST /api/v1/certificates salva
   - [ ] Card mostra dias restantes

7. **Criar Recebível:**
   - Click "Financeiro" → "Novo Recebível"
   - Valor: 5000, Vencimento: próx mês, Cliente: o criado
   - [ ] POST /api/v1/receivables salva
   - [ ] Status: "pending"
   - [ ] Click "Marcar como Pago" → status muda para "paid"

**Se tudo passou:**
```
INTEGRAÇÃO: ✅ FUNCIONANDO
```

---

## 5️⃣ TENANT ISOLATION (Segurança)

**Se conseguir 2 browser windows:**

1. **Window 1:** Registra user_a
2. **Window 2:** Registra user_b
3. **user_a cria cliente**
4. **user_b tenta acessar clientes**
   - [ ] Lista vazia (isolamento funciona!)
   - [ ] NÃO consegue ver clientes de user_a

**Se passou:**
```
SEGURANÇA: ✅ TENANT ISOLATION OK
```

---

## 6️⃣ PERFORMANCE

### ✅ Verificar

```
Frontend (Vercel):
- [ ] Lighthouse Score ≥ 80
- [ ] First Contentful Paint < 2s
- [ ] Time to Interactive < 3s

Backend (Fly.io):
- [ ] GET /api/v1/clients responde em < 500ms
- [ ] POST /api/v1/clients responde em < 1s
- [ ] Database queries são rápidas (Supabase pooler)
```

---

## 7️⃣ LOGS E MONITORAMENTO

### ✅ Checar Logs

**Vercel:**
```
GitHub → Actions → Deploy workflow
Vercel Dashboard → Logs
```

**Fly.io:**
```
flyctl logs --app contaflow
```

**Supabase:**
```
Supabase Dashboard → Logs → Postgres
```

---

## ✅ CHECKLIST FINAL

- [ ] Vercel Frontend carrega e funciona
- [ ] Supabase Database tem todas as tables
- [ ] Fly.io Backend está running
- [ ] Health check retorna 200 OK
- [ ] Registro de usuário funciona
- [ ] CRUD de cliente funciona (create, read, update, delete)
- [ ] CRUD de prazo funciona
- [ ] CRUD de documento funciona
- [ ] CRUD de certificado funciona
- [ ] CRUD de recebível funciona
- [ ] Dashboard mostra dados reais
- [ ] Tenant isolation funciona (2 users isolados)
- [ ] Supabase recebe todas as queries
- [ ] Sem erros 500 ou 502
- [ ] Logs limpos (sem warnings críticos)

---

## 🎯 SE TUDO PASSOU

```
✅ CONTAFLOW EM PRODUÇÃO — PRONTO PARA PILOTOS!
```

**Próximas fases:**
- Phase 6: Notificações de prazos
- Phase 7: Integração certificados digitais
- Phase 8: Dashboard financeiro avançado

---

## ❌ SE ALGO FALHOU

**Erro comum | Solução:**
| Erro | Solução |
|------|---------|
| 502 Bad Gateway | Fly.io backend não respondendo, check: `flyctl logs` |
| CORS error | ALLOWED_ORIGINS não inclui domínio Vercel, update `fly.toml` |
| Database connection failed | DATABASE_URL inválida em Fly.io secrets |
| 401 Unauthorized | JWT_SECRET_KEY não set ou diferente entre deploys |
| Timeout na request | Fly.io cold start longo, máquina pode estar hibernando |

---

**Execute este checklist e reporte status! 🚀**
