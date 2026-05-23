# 🚀 Frontend (vstack-site) Deployment Checklist

**Status**: PRONTO PARA DEPLOY  
**Próximo Passo**: Deploy em Vercel  
**Data**: 2026-05-23

---

## ✅ PRÉ-REQUISITOS DE DEPLOY

- [ ] Código vstack-site atualizado com Feature #7 (Calculadora Fiscal)
- [ ] Todas as dependências instaladas: `npm install`
- [ ] Testes locais passando: `npm run test` ou `npm run dev`
- [ ] Build local funciona: `npm run build`
- [ ] Variáveis de ambiente configuradas localmente
- [ ] Backend em Fly.io online e respondendo (`https://contaflow.fly.dev/api/v1/health`)

---

## 🔧 CONFIGURAÇÃO DE AMBIENTE

### Variáveis Necessárias

#### Local (`.env.local`)
```env
# API Backend
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1

# OpenAI (Feature #7)
OPENAI_API_KEY=sk-...

# Outros (conforme necessário)
NEXT_PUBLIC_APP_NAME=FiscWise
NEXT_PUBLIC_APP_VERSION=1.0.0
```

#### Vercel (Project Settings → Environment Variables)
```env
# API Backend (PRODUÇÃO)
NEXT_PUBLIC_API_URL=https://contaflow.fly.dev/api/v1

# OpenAI (PRODUÇÃO - precisa ser gerada/validada)
OPENAI_API_KEY=sk-...

# Outros
NEXT_PUBLIC_APP_NAME=FiscWise
NEXT_PUBLIC_APP_VERSION=1.0.0
```

**⚠️ IMPORTANTE**: OpenAI API key deve ser gerada/obtida antes de fazer push para produção

---

## 📋 CHECKLIST DE DEPLOY

### Fase 1: Preparação Local

- [ ] Clonar/navegar para `vstack-site` branch
- [ ] Executar `npm install` (se necessário)
- [ ] Executar `npm run build` 
  - Esperado: Build completo sem erros
  - Verificar: Não há warnings críticos em `.next`
- [ ] Executar `npm run dev` e testar localmente
  - Navegação funciona
  - Calculadora Fiscal acessível
  - Endpoints do backend respondem

### Fase 2: Verificar Código (Code Review)

- [ ] Verificar imports corretos (sem hardcoded URLs)
- [ ] Verificar variáveis de ambiente:
  ```bash
  grep -r "localhost:8000\|contaflow.fly.dev" src/
  # Devem estar em .env.local, não no código
  ```
- [ ] Verificar que não há secrets em commits:
  ```bash
  git log -p | grep -i "sk-\|api.key\|password"
  # Não devem aparecer
  ```
- [ ] Verificar TypeScript errors: `npm run type-check`
- [ ] Verificar linting: `npm run lint`

### Fase 3: Deploy Vercel

**Opção A: Via CLI (Recomendado)**
```bash
cd vstack-site

# Login no Vercel
vercel login

# Deploy em staging (preview)
vercel --prod  # Ir para produção

# Verificar deployment
vercel --list  # Ver todos deployments
```

**Opção B: Via GitHub Push**
- Fazer push de branch feature/calculator
- Vercel criará preview URL automaticamente
- Testar em preview antes de merge
- Merge para `main` trigará deploy em produção

### Fase 4: Pós-Deploy Imediato

- [ ] Acessar URL de produção em navegador
- [ ] Verificar health: Network tab deve mostrar requests sucedendo
- [ ] Verificar console: Não deve ter erros vermelhos (`console.error`)
- [ ] Testar login: Form deve aceitar credenciais
- [ ] Testar navegação básica
- [ ] Testar acesso à Calculadora Fiscal

---

## 🧪 TESTES PÓS-DEPLOY

### Teste 1: Carregamento da Página
```
1. Abrir https://vstack-site.vercel.app/
2. Aguardar load completo (< 3 segundos)
3. Verificar: logo, menu, footer carregam
4. Verificar: nenhum erro 404 em assets
```

### Teste 2: Login
```
1. Clicar "Login" ou navegar para /login
2. Email: vsouz009@gmail.com
3. Senha: [senha de teste]
4. Esperado: Redirecionar para dashboard
5. Verificar: Token JWT armazenado em localStorage
```

### Teste 3: Navegação para Calculadora
```
1. No dashboard, encontrar "Calculadora Fiscal"
2. Clicar para abrir
3. Esperado: Carrega 3 tabs (Simulator, Chat, History)
4. Verificar: Form de entrada visível
```

### Teste 4: Simulação de Regime
```
1. Preencher "Receita Anual": 150000 (R$ 150k)
2. Clicar "Simular"
3. Esperado em <5s:
   - Carrega 3 cenários (Simples, Lucro Presumido, Lucro Real)
   - Mostra taxa efetiva para cada regime
   - Identifica regime mais vantajoso
4. Verificar: Dados consultados do backend (/calculator/simulate-regime)
```

### Teste 5: Chat com IA
```
1. Abrir tab "Chat"
2. Digitar: "Qual é o melhor regime para minha empresa?"
3. Clicar enviar
4. Esperado em <10s:
   - Mensagem aparece no histórico
   - IA responde com recomendação
   - Resposta relevante para receita da simulação anterior
5. Verificar: Network mostra POST /calculator/chat com 200 OK
```

### Teste 6: Histórico de Simulações
```
1. Abrir tab "History"
2. Esperado:
   - Simulação anterior aparece na lista
   - Data/hora corretas
   - Regime recomendado visível
3. Clicar em simulação anterior
4. Esperado: Carrega detalhes da simulação
```

### Teste 7: Plan-Based Gating
```
FREE Plan:
- Simulador funciona (números apenas)
- Chat desabilitado (mostrar "Upgrade para usar IA")
- PDF export desabilitado

INTERMEDIÁRIO Plan:
- Simulador + Chat (20 msgs/mês) 
- PDF export desabilitado
- Contador de mensagens visível

PREMIUM Plan:
- Simulador + Chat ilimitado
- PDF export habilitado
```

### Teste 8: Export PDF (Premium)
```
1. Fazer simulação
2. Clicar "Exportar PDF"
3. Esperado: Download iniciado
4. Abrir PDF em leitor
5. Verificar:
   - PDF contém cenários simulados
   - Tabelas de resultados claras
   - Logo FiscWise presente
```

---

## 🐛 Troubleshooting

### Erro: "Failed to fetch from backend"
**Causa**: NEXT_PUBLIC_API_URL incorreta ou backend offline
**Solução**:
1. Verificar `NEXT_PUBLIC_API_URL` em Vercel settings
2. Testar manualmente: `curl https://contaflow.fly.dev/api/v1/health`
3. Se offline, fazer restart: `flyctl machines restart -a contaflow`

### Erro: "OpenAI API Error"
**Causa**: API key inválida, expirada ou sem saldo
**Solução**:
1. Verificar API key em Vercel settings
2. Testar em https://platform.openai.com/account/api-keys
3. Gerar nova key se necessário
4. Redeploy: `vercel --prod`

### Erro: "Module not found / 404"
**Causa**: Assets CSS/JS não carregaram
**Solução**:
1. Verificar em Network tab qual asset falhou
2. Verificar build logs em Vercel: `vercel log --follow`
3. Reexecutar build: `vercel --prod --force`

### Erro: "CORS error"
**Causa**: Backend não permitindo requests do domínio Vercel
**Solução**:
1. Verificar CORS config em `backend/app/main.py`
2. Adicionar domínio Vercel à lista de `allow_origins`
3. Fazer rebuild backend: `flyctl deploy -a contaflow`

### Lentidão (> 5s para simulação)
**Causa**: Rede lenta ou backend sobrecarregado
**Solução**:
1. Testar direto a API: `curl https://contaflow.fly.dev/api/v1/health`
2. Verificar Fly.io logs: `flyctl logs -a contaflow`
3. Se muita carga, escalar máquina Fly.io
4. Implementar cache local no frontend

---

## 📊 Metricas Esperadas Pós-Deploy

```
Frontend (Vercel):
- First Contentful Paint (FCP): < 2s
- Time to Interactive (TTI): < 3s
- Lighthouse Score: > 80
- Build time: < 2 min
- Deployments/day: ~1-3 (durante testes)

Backend (Fly.io):
- API response time: < 500ms
- Calculator simulate: 1-3s (depende de IA)
- Chat response: 5-15s (depende de OpenAI)
- Error rate: < 1%
- Uptime: > 99.5%
```

---

## ✨ Sign-off

**Responsável**: Vinicius Souza  
**Data de Deploy**: [Data aqui]  
**Versão**: 1.0.0  
**Hotline**: Documentar em PRODUCTION_STATUS.md se houver issues

---

## 🎯 Próximo Passo Após Deploy

1. ✅ Esperar 1-2 min para Vercel finalizar deploy
2. ✅ Acessar URL de produção
3. ✅ Executar testes básicos (login, navegação, calculadora)
4. ✅ Se OK: Criar task de "Teste com Usuário Real"
5. ✅ Se erros: Investigar logs e executar rollback se necessário

---

**Status**: Pronto para deploy ✈️
