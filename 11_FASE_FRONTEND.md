# FASE 11 — Frontend Dashboard (Next.js 14 + TypeScript + Tailwind)

## PRÉ-REQUISITO
Fases 06-10 concluídas. Backend com todos os endpoints operacionais.

## CONTEXTO DO PROJETO
Backend API: `https://solo-os-api-production.up.railway.app`
Stack Frontend: Next.js 14 (App Router) + TypeScript + Tailwind CSS + shadcn/ui

---

## TAREFA

### 1. Inicializar projeto Next.js em `frontend/`
```bash
cd /raiz/do/projeto  # mesmo nível que backend/
npx create-next-app@14 frontend --typescript --tailwind --app --src-dir --import-alias "@/*"
cd frontend
npx shadcn-ui@latest init
```

Instalar dependências adicionais:
```bash
npm install axios js-cookie @types/js-cookie lucide-react react-hot-toast
```

---

### 2. Estrutura de pastas em `frontend/src/`
```
app/
  (auth)/
    login/page.tsx
    register/page.tsx
  (dashboard)/
    layout.tsx               ← sidebar + header autenticados
    page.tsx                 ← redirect para /dashboard
    dashboard/page.tsx       ← métricas e stats
    knowledge/page.tsx       ← gerenciar documentos
    chat/page.tsx            ← histórico de sessões
    chat/[sessionId]/page.tsx ← conversa específica
    widget/page.tsx          ← configurar e copiar snippet
    billing/page.tsx         ← plano atual + upgrade
    settings/page.tsx        ← perfil + tenant
lib/
  api.ts                     ← axios instance com interceptors
  auth.ts                    ← funções de autenticação
  hooks/
    useAuth.ts
    useAnalytics.ts
    useKnowledge.ts
    useChat.ts
components/
  ui/                        ← shadcn/ui components
  Sidebar.tsx
  Header.tsx
  StatCard.tsx
  DocumentList.tsx
  ChatWindow.tsx
```

---

### 3. `frontend/src/lib/api.ts`
```typescript
import axios from 'axios';
import Cookies from 'js-cookie';

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'https://solo-os-api-production.up.railway.app',
});

api.interceptors.request.use((config) => {
  const token = Cookies.get('access_token');
  const tenantId = Cookies.get('tenant_id');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  if (tenantId) config.headers['X-Tenant-ID'] = tenantId;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401) {
      Cookies.remove('access_token');
      Cookies.remove('tenant_id');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

---

### 4. `frontend/src/lib/auth.ts`
```typescript
import { api } from './api';
import Cookies from 'js-cookie';

export async function login(email: string, password: string) {
  const res = await api.post('/api/v1/auth/login', { email, password });
  const { access_token, tenant_id } = res.data;
  Cookies.set('access_token', access_token, { expires: 1 });
  Cookies.set('tenant_id', tenant_id, { expires: 1 });
  return res.data;
}

export async function register(data: {
  company_name: string;
  owner_email: string;
  owner_password: string;
  owner_full_name: string;
  plan_slug: string;
}) {
  const res = await api.post('/api/v1/onboarding/register', data);
  const { access_token, tenant_id } = res.data;
  Cookies.set('access_token', access_token, { expires: 1 });
  Cookies.set('tenant_id', tenant_id, { expires: 1 });
  return res.data;
}

export function logout() {
  Cookies.remove('access_token');
  Cookies.remove('tenant_id');
  window.location.href = '/login';
}

export function isAuthenticated() {
  return !!Cookies.get('access_token');
}
```

---

### 5. Páginas a implementar

#### `/login` — Formulário email + senha, chama `auth.login()`, redireciona para `/dashboard`

#### `/register` — Wizard 3 passos:
1. Dados da empresa (company_name)
2. Dados do owner (email, senha, nome)
3. Escolha do plano (GET /api/v1/billing/plans)
Chama `auth.register()`, redireciona para `/dashboard`

#### `/dashboard` — Cards com métricas (GET /analytics/usage):
- Total de sessões, mensagens, tokens, documentos
- Gráfico simples de uso diário (GET /analytics/usage/daily) usando recharts ou simples CSS bars

#### `/knowledge` — Lista de documentos (GET /knowledge/sources):
- Botão "Adicionar URL" → modal com input URL → POST /knowledge/ingest/url
- Botão "Adicionar Texto" → modal com textarea → POST /knowledge/ingest/text
- Status badge por documento (pending/processing/processed/failed)
- Botão deletar por documento → DELETE /knowledge/sources/{id}

#### `/chat` — Lista de sessões (GET /chat/sessions):
- Cada sessão clicável → vai para `/chat/{sessionId}`
- Botão "Nova Conversa" → POST /chat/sessions

#### `/chat/[sessionId]` — Interface de chat:
- Histórico de mensagens (GET /chat/sessions/{id}/messages)
- Input de mensagem
- POST /chat/sessions/{id}/messages retorna SSE
- Parsear SSE: `data: token` → concatenar na bolha do assistente em tempo real
- Detectar `data: [DONE]` para finalizar
- Detectar `data: [QUOTA_EXCEEDED]` para mostrar aviso

#### `/widget` — Configuração do widget:
- Mostrar snippet HTML para copiar:
```html
<script src="https://solo-os-api-production.up.railway.app/api/v1/widget/{tenant_id}.js"></script>
```
- Botão "Copiar" com feedback visual (toast)
- Preview do chat (iframe apontando para /api/v1/widget/{tenant_id}/chat)

#### `/billing` — Plano atual + upgrade:
- GET /billing/subscription → mostrar plano atual, status, data de renovação
- GET /billing/plans → listar planos disponíveis
- Botão "Fazer upgrade" → POST /billing/checkout → redirecionar para checkout_url
- Botão "Gerenciar assinatura" → POST /billing/portal → redirecionar para portal_url

#### `/settings` — Perfil do usuário:
- GET /users/me → mostrar nome, email, role
- Seção "Dados do Tenant" (nome da empresa, tenant_id para copiar)

---

### 6. Layout autenticado `(dashboard)/layout.tsx`
- Verificar `isAuthenticated()` no client side — redirecionar para `/login` se não autenticado
- Sidebar com links: Dashboard, Base de Conhecimento, Conversas, Widget, Billing, Configurações
- Header com nome do usuário + botão logout
- Design: branco/cinza com accent azul, responsivo

---

### 7. `frontend/.env.local`
```
NEXT_PUBLIC_API_URL=https://solo-os-api-production.up.railway.app
```

---

### 8. Deploy no Railway
Criar serviço frontend no Railway:
- Build command: `cd frontend && npm install && npm run build`
- Start command: `cd frontend && npm start`
- Variável: `NEXT_PUBLIC_API_URL=https://solo-os-api-production.up.railway.app`

Atualizar CORS no backend `app/core/config.py`:
```
ALLOWED_ORIGINS=https://frontend-production.up.railway.app,http://localhost:3000
```

---

## VALIDAÇÃO FINAL
```bash
cd frontend
npm run build  # deve compilar sem erros TypeScript
npm run dev    # testar em localhost:3000
```

Fluxo de teste:
1. `/register` → criar conta → redirecionar para `/dashboard`
2. `/knowledge` → adicionar URL → aguardar status `processed`
3. `/chat` → nova conversa → enviar mensagem → ver resposta SSE
4. `/widget` → copiar snippet → colar em HTML estático → testar chat
