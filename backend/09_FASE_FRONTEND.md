# FASE 9 - Frontend React + Dashboard UI

## 🎯 Objetivo

Implementar interface frontend completa para o ContaFlow usando React 18+, TypeScript, Vite, Tailwind CSS e Shadcn/ui. O frontend deve consumir a API backend e fornecer uma experiência de usuário moderna e responsiva.

## 📋 Escopo

### 1. **Setup do Projeto Frontend**

#### Tecnologias Base
- **React 18+** - Framework UI
- **TypeScript** - Type safety
- **Vite** - Build tool e dev server
- **React Router v6** - Roteamento SPA
- **Tailwind CSS** - Utility-first CSS
- **Shadcn/ui** - Component library
- **Lucide React** - Ícones modernos

#### Bibliotecas Adicionais
- **Axios** - HTTP client
- **React Query (TanStack Query)** - Data fetching e cache
- **Zustand** - State management
- **React Hook Form** - Form handling
- **Zod** - Schema validation
- **Recharts** - Charts e gráficos
- **date-fns** - Date manipulation
- **React Hot Toast** - Notifications

### 2. **Estrutura de Diretórios**

```
frontend/
├── public/
│   └── favicon.ico
├── src/
│   ├── api/                    # API client e endpoints
│   │   ├── client.ts           # Axios instance configurado
│   │   ├── auth.ts             # Auth endpoints
│   │   ├── knowledge.ts        # Knowledge endpoints
│   │   ├── chat.ts             # Chat endpoints
│   │   └── analytics.ts        # Analytics endpoints
│   ├── components/             # Componentes reutilizáveis
│   │   ├── ui/                 # Shadcn/ui components
│   │   ├── layout/             # Layout components
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── Layout.tsx
│   │   ├── auth/               # Auth components
│   │   │   ├── LoginForm.tsx
│   │   │   └── RegisterForm.tsx
│   │   ├── dashboard/          # Dashboard components
│   │   │   ├── StatsCard.tsx
│   │   │   ├── TokenUsageChart.tsx
│   │   │   ├── SessionsChart.tsx
│   │   │   └── DocumentsTable.tsx
│   │   ├── knowledge/          # Knowledge Base components
│   │   │   ├── DocumentUpload.tsx
│   │   │   ├── DocumentList.tsx
│   │   │   └── DocumentCard.tsx
│   │   └── chat/               # Chat components
│   │       ├── ChatInterface.tsx
│   │       ├── MessageList.tsx
│   │       ├── MessageInput.tsx
│   │       └── SessionList.tsx
│   ├── hooks/                  # Custom hooks
│   │   ├── useAuth.ts
│   │   ├── useChat.ts
│   │   ├── useAnalytics.ts
│   │   └── useKnowledge.ts
│   ├── lib/                    # Utilities
│   │   ├── utils.ts
│   │   └── constants.ts
│   ├── pages/                  # Page components
│   │   ├── LoginPage.tsx
│   │   ├── RegisterPage.tsx
│   │   ├── DashboardPage.tsx
│   │   ├── KnowledgePage.tsx
│   │   └── ChatPage.tsx
│   ├── stores/                 # Zustand stores
│   │   ├── authStore.ts
│   │   └── chatStore.ts
│   ├── types/                  # TypeScript types
│   │   ├── auth.ts
│   │   ├── knowledge.ts
│   │   ├── chat.ts
│   │   └── analytics.ts
│   ├── App.tsx                 # Root component
│   ├── main.tsx                # Entry point
│   └── index.css               # Global styles
├── .env.example
├── .gitignore
├── index.html
├── package.json
├── tsconfig.json
├── tailwind.config.js
├── vite.config.ts
└── README.md
```

### 3. **Autenticação e Autorização**

#### Auth Store (Zustand)
```typescript
interface AuthState {
  token: string | null;
  tenantId: string | null;
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => void;
  setToken: (token: string, tenantId: string) => void;
}
```

#### Axios Interceptor
- Adicionar `Authorization: Bearer {token}` em todas as requests
- Adicionar `X-Tenant-ID: {tenantId}` em todas as requests
- Redirect para login em caso de 401 Unauthorized
- Refresh token automático (se implementado no backend)

#### Protected Routes
```typescript
<Route element={<ProtectedRoute />}>
  <Route path="/dashboard" element={<DashboardPage />} />
  <Route path="/knowledge" element={<KnowledgePage />} />
  <Route path="/chat" element={<ChatPage />} />
</Route>
```

### 4. **Páginas Principais**

#### Login Page
- Form com email e password
- Validação com Zod
- Error handling
- Link para registro
- Loading state

#### Register Page (Onboarding)
- Form multi-step:
  1. Dados da empresa (company_name, subdomain)
  2. Dados do admin (full_name, email, password)
- Validação de subdomain disponível
- Preview do subdomain
- Loading state

#### Dashboard Page
- **KPI Cards**:
  - Total de tokens usados (últimos 30 dias)
  - Custo estimado em USD
  - Total de sessões de chat
  - Total de documentos
- **Charts**:
  - Token usage over time (line chart)
  - Sessions per day (bar chart)
  - Documents by status (pie chart)
- **Recent Activity**:
  - Últimas sessões de chat
  - Últimos documentos ingeridos

#### Knowledge Base Page
- **Upload Section**:
  - Text input (textarea)
  - URL input
  - File upload (futuro)
- **Documents List**:
  - Table com: title, source_type, status, chunk_count, created_at
  - Filtro por status
  - Paginação
  - Delete action

#### Chat Page
- **Layout Split**:
  - Sidebar: Lista de sessões
  - Main: Chat interface
- **Session List**:
  - Criar nova sessão
  - Listar sessões existentes
  - Selecionar sessão ativa
- **Chat Interface**:
  - Message list (scroll to bottom)
  - Message input (textarea + send button)
  - SSE streaming (progressive rendering)
  - Loading indicator
  - Error handling

### 5. **Componentes Shadcn/ui**

Instalar componentes necessários:
```bash
npx shadcn-ui@latest add button
npx shadcn-ui@latest add card
npx shadcn-ui@latest add input
npx shadcn-ui@latest add label
npx shadcn-ui@latest add textarea
npx shadcn-ui@latest add table
npx shadcn-ui@latest add dialog
npx shadcn-ui@latest add dropdown-menu
npx shadcn-ui@latest add select
npx shadcn-ui@latest add tabs
npx shadcn-ui@latest add badge
npx shadcn-ui@latest add avatar
npx shadcn-ui@latest add separator
npx shadcn-ui@latest add skeleton
```

### 6. **API Client Implementation**

#### Axios Instance
```typescript
import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  const tenantId = localStorage.getItem('tenantId');
  
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  
  if (tenantId) {
    config.headers['X-Tenant-ID'] = tenantId;
  }
  
  return config;
});

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('tenantId');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default apiClient;
```

#### Auth API
```typescript
export const authApi = {
  login: async (email: string, password: string) => {
    const formData = new FormData();
    formData.append('username', email);
    formData.append('password', password);
    
    const response = await apiClient.post('/api/v1/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    
    return response.data;
  },
  
  register: async (data: RegisterData) => {
    const response = await apiClient.post('/api/v1/onboarding/register', data);
    return response.data;
  },
  
  getMe: async () => {
    const response = await apiClient.get('/api/v1/auth/me');
    return response.data;
  },
};
```

#### Analytics API
```typescript
export const analyticsApi = {
  getDashboard: async (params?: { start_date?: string; end_date?: string; days?: number }) => {
    const response = await apiClient.get('/api/v1/analytics/dashboard', { params });
    return response.data;
  },
  
  getTokenUsage: async (params?: { start_date?: string; end_date?: string }) => {
    const response = await apiClient.get('/api/v1/analytics/token-usage', { params });
    return response.data;
  },
};
```

#### Chat API (SSE)
```typescript
export const chatApi = {
  createSession: async (title?: string) => {
    const response = await apiClient.post('/api/v1/chat/sessions', { title });
    return response.data;
  },
  
  getSessions: async () => {
    const response = await apiClient.get('/api/v1/chat/sessions');
    return response.data;
  },
  
  sendMessage: (sessionId: string, message: string, onChunk: (text: string) => void) => {
    const token = localStorage.getItem('token');
    const tenantId = localStorage.getItem('tenantId');
    
    const eventSource = new EventSource(
      `${import.meta.env.VITE_API_URL}/api/v1/chat/sessions/${sessionId}/messages?` +
      `message=${encodeURIComponent(message)}&` +
      `token=${token}&` +
      `tenant_id=${tenantId}`
    );
    
    eventSource.onmessage = (event) => {
      if (event.data === '[DONE]') {
        eventSource.close();
      } else {
        onChunk(event.data);
      }
    };
    
    eventSource.onerror = () => {
      eventSource.close();
    };
    
    return eventSource;
  },
};
```

### 7. **React Query Setup**

```typescript
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

// Usage in hooks
export const useDashboard = () => {
  return useQuery({
    queryKey: ['dashboard'],
    queryFn: () => analyticsApi.getDashboard(),
  });
};

export const useSessions = () => {
  return useQuery({
    queryKey: ['chat-sessions'],
    queryFn: () => chatApi.getSessions(),
  });
};
```

### 8. **Environment Variables**

```env
# .env.example
VITE_API_URL=http://localhost:8000
VITE_APP_NAME=ContaFlow
```

### 9. **Responsividade**

- Mobile-first approach
- Breakpoints Tailwind:
  - sm: 640px
  - md: 768px
  - lg: 1024px
  - xl: 1280px
  - 2xl: 1536px
- Sidebar colapsável em mobile
- Tables responsivas (scroll horizontal)
- Charts adaptáveis

### 10. **Acessibilidade (a11y)**

- Semantic HTML
- ARIA labels
- Keyboard navigation
- Focus management
- Color contrast (WCAG AA)
- Screen reader support

## 🚀 Entregáveis

### Arquivos a Criar

1. **Setup**:
   - `package.json` - Dependencies
   - `vite.config.ts` - Vite configuration
   - `tsconfig.json` - TypeScript configuration
   - `tailwind.config.js` - Tailwind configuration
   - `.env.example` - Environment variables template

2. **API Client**:
   - `src/api/client.ts` - Axios instance
   - `src/api/auth.ts` - Auth endpoints
   - `src/api/knowledge.ts` - Knowledge endpoints
   - `src/api/chat.ts` - Chat endpoints
   - `src/api/analytics.ts` - Analytics endpoints

3. **Types**:
   - `src/types/auth.ts` - Auth types
   - `src/types/knowledge.ts` - Knowledge types
   - `src/types/chat.ts` - Chat types
   - `src/types/analytics.ts` - Analytics types

4. **Stores**:
   - `src/stores/authStore.ts` - Auth state
   - `src/stores/chatStore.ts` - Chat state

5. **Hooks**:
   - `src/hooks/useAuth.ts` - Auth hook
   - `src/hooks/useChat.ts` - Chat hook
   - `src/hooks/useAnalytics.ts` - Analytics hook
   - `src/hooks/useKnowledge.ts` - Knowledge hook

6. **Components**:
   - Layout components (Header, Sidebar, Layout)
   - Auth components (LoginForm, RegisterForm)
   - Dashboard components (StatsCard, Charts, Tables)
   - Knowledge components (Upload, List, Card)
   - Chat components (Interface, MessageList, Input)

7. **Pages**:
   - `src/pages/LoginPage.tsx`
   - `src/pages/RegisterPage.tsx`
   - `src/pages/DashboardPage.tsx`
   - `src/pages/KnowledgePage.tsx`
   - `src/pages/ChatPage.tsx`

8. **Root Files**:
   - `src/App.tsx` - Root component with routing
   - `src/main.tsx` - Entry point
   - `src/index.css` - Global styles

### Documentação

1. `frontend/README.md` - Setup e usage instructions

## ✅ Critérios de Aceitação

- [ ] Projeto React + Vite + TypeScript configurado
- [ ] Tailwind CSS e Shadcn/ui instalados
- [ ] API client com interceptors configurado
- [ ] Auth store e protected routes funcionando
- [ ] Login e Register pages implementadas
- [ ] Dashboard page com KPIs e charts
- [ ] Knowledge Base page com upload e list
- [ ] Chat page com SSE streaming
- [ ] Responsividade mobile-first
- [ ] Build de produção funcionando

## 🎯 Próximos Passos (Fase 10)

Após conclusão da Fase 9:
- **Fase 10**: Deployment & CI/CD (Docker, Railway/Vercel, GitHub Actions)

---

**Fase 9 - Frontend: PRONTO PARA IMPLEMENTAÇÃO** ⚛️🎨🚀
