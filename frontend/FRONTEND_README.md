# FiscWise Frontend - React + TypeScript + Vite

## Status: CONCLUIDO

Frontend completo implementado com todas as funcionalidades especificadas na Fase 11.

## Stack Tecnologica

- **React 18.3.1** - Biblioteca UI
- **TypeScript 5.5.3** - Tipagem estática
- **Vite 5.4.3** - Build tool e dev server
- **Tailwind CSS 3.4.11** - Estilização
- **React Router v6.26.0** - Roteamento
- **TanStack Query 5.56.2** - Data fetching e cache
- **Zustand 4.5.5** - State management
- **Axios 1.7.7** - HTTP client
- **React Hook Form 7.53.0 + Zod 3.23.8** - Formulários e validação
- **Recharts 2.12.7** - Gráficos
- **Lucide React 0.441.0** - Ícones
- **React Hot Toast 2.4.1** - Notificações
- **date-fns 3.6.0** - Manipulação de datas

## Estrutura do Projeto

```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/                    # Componentes UI reutilizáveis
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Card.tsx
│   │   │   └── Badge.tsx
│   │   ├── Header.tsx             # Header do dashboard
│   │   ├── Sidebar.tsx            # Sidebar de navegação
│   │   └── ProtectedRoute.tsx    # HOC para rotas protegidas
│   ├── layouts/
│   │   └── DashboardLayout.tsx   # Layout principal do dashboard
│   ├── lib/
│   │   ├── api.ts                # Axios instance com interceptors
│   │   ├── auth.ts               # Funções de autenticação
│   │   ├── utils.ts              # Utilitários (cn)
│   │   └── hooks/                # Custom hooks
│   │       ├── useAuth.ts
│   │       ├── useAnalytics.ts
│   │       ├── useKnowledge.ts
│   │       └── useChat.ts
│   ├── pages/
│   │   ├── LoginPage.tsx         # Página de login
│   │   ├── RegisterPage.tsx      # Wizard de registro (3 passos)
│   │   ├── DashboardPage.tsx     # Dashboard com métricas
│   │   ├── KnowledgePage.tsx     # Gerenciamento de documentos
│   │   ├── ChatPage.tsx          # Lista de sessões de chat
│   │   ├── ChatSessionPage.tsx   # Interface de chat com SSE
│   │   ├── WidgetPage.tsx        # Configuração do widget
│   │   ├── BillingPage.tsx       # Planos e billing
│   │   └── SettingsPage.tsx      # Configurações do usuário
│   ├── stores/
│   │   └── authStore.ts          # Zustand store para autenticação
│   ├── App.tsx                   # Configuração de rotas
│   ├── main.tsx                  # Entry point
│   ├── index.css                 # Estilos globais + Tailwind
│   └── vite-env.d.ts            # TypeScript declarations
├── .env                          # Variáveis de ambiente
├── .env.example                  # Template de variáveis
├── package.json                  # Dependências
├── tsconfig.json                 # Configuração TypeScript
├── vite.config.ts               # Configuração Vite
├── tailwind.config.js           # Configuração Tailwind
└── postcss.config.js            # Configuração PostCSS
```

## Comandos Disponíveis

```bash
# Instalar dependências
npm install

# Iniciar servidor de desenvolvimento (porta 3000)
npm run dev

# Build para produção
npm run build

# Preview do build de produção
npm run preview

# Verificação de tipos TypeScript
npm run type-check

# Lint do código
npm run lint
```

## Rotas Implementadas

### Rotas Públicas
- `/login` - Página de login
- `/register` - Wizard de registro (3 passos)

### Rotas Protegidas (requerem autenticação)
- `/` - Redirect para `/dashboard`
- `/dashboard` - Dashboard com métricas e gráficos
- `/knowledge` - Gerenciamento da base de conhecimento
- `/chat` - Lista de sessões de chat
- `/chat/:sessionId` - Interface de chat com streaming SSE
- `/widget` - Configuração e preview do widget
- `/billing` - Planos e gerenciamento de assinatura
- `/settings` - Configurações do usuário e tenant

## Autenticação

- **Login**: Email + senha via OAuth2 Password Flow
- **Registro**: Wizard de 3 passos (empresa → usuário → plano)
- **Storage**: localStorage para `access_token`, `tenant_id` e `user`
- **Interceptors**: Axios adiciona automaticamente token e X-Tenant-ID
- **Redirect**: 401 redireciona para `/login` automaticamente

## Funcionalidades Principais

### Dashboard
- Cards com métricas (sessões, mensagens, tokens, custo)
- Gráfico de uso diário (últimos 30 dias)
- Análise de sessões (média de mensagens e tokens)
- Status da base de conhecimento

### Base de Conhecimento
- Adicionar documentos via URL
- Adicionar documentos via texto
- Visualizar status (pending, processing, processed, failed)
- Deletar documentos
- Badges de status coloridos

### Chat
- Lista de sessões com histórico
- Criar nova sessão
- Interface de chat com mensagens
- **Streaming SSE** em tempo real
- Detecção de quota excedida
- Scroll automático
- Timestamps e contagem de tokens

### Widget
- Código de integração para copiar
- Preview do widget em iframe
- Informações do tenant ID

### Billing
- Visualização do plano atual
- Barra de progresso de uso de tokens
- Cards de planos disponíveis (Free, Starter, Pro)
- Botões de upgrade

### Settings
- Perfil do usuário (nome, email, role)
- Informações do tenant
- Tenant ID para integração

## Design System

### Cores (Tailwind CSS Variables)
- `--background`: Fundo principal
- `--foreground`: Texto principal
- `--card`: Fundo de cards
- `--primary`: Cor primária (azul)
- `--muted`: Cor secundária
- `--accent`: Cor de destaque
- `--destructive`: Cor de erro/delete

### Componentes UI
- **Button**: 4 variantes (default, outline, ghost, destructive) + 3 tamanhos
- **Input**: Estilizado com focus states
- **Card**: Header, Title, Description, Content, Footer
- **Badge**: 5 variantes (default, success, warning, error, info)

## State Management

### Zustand (authStore)
- `user`: Dados do usuário logado
- `isAuthenticated`: Status de autenticação
- `setUser()`: Atualizar usuário
- `logout()`: Fazer logout
- `checkAuth()`: Verificar autenticação

### TanStack Query
- Cache automático de requisições
- Invalidação inteligente
- Loading e error states
- Retry automático (1x)

## Variáveis de Ambiente

```env
VITE_API_URL=http://localhost:8000
```

Para produção:
```env
VITE_API_URL=https://contaflow.fly.dev
```

## Validação

### TypeScript
```bash
npm run type-check
```
Status: Sem erros de compilação

### Dev Server
```bash
npm run dev
```
Status: Rodando em http://localhost:3000

## Próximos Passos

1. **Deploy no Railway/Vercel**
   - Configurar variável `VITE_API_URL` para produção
   - Build command: `npm run build`
   - Output directory: `dist`

2. **Configurar CORS no Backend**
   - Adicionar URL do frontend em `ALLOWED_ORIGINS`

3. **Testes**
   - Testar fluxo completo de registro
   - Testar adição de documentos
   - Testar chat com streaming
   - Testar widget

## Notas Técnicas

- **Proxy Vite**: Configurado para `/api` → `http://localhost:8000`
- **Path Aliases**: `@/*` aponta para `src/*`
- **SSE Streaming**: Implementado com Fetch API nativa
- **Responsive**: Design mobile-first com Tailwind
- **Dark Mode**: Suporte via CSS variables (não implementado toggle)

## Conformidade com Especificação

- Todas as páginas especificadas implementadas
- Autenticação com JWT + X-Tenant-ID
- SSE streaming para chat
- Gráficos com Recharts
- Formulários com React Hook Form + Zod
- State management com Zustand
- Data fetching com TanStack Query
- TypeScript sem erros
- Tailwind CSS + componentes reutilizáveis
- Rotas protegidas com ProtectedRoute

---

**FiscWise Frontend**
**Data**: 27/04/2026
**Fase**: 11 - Frontend Dashboard
