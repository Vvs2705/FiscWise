# FiscWise — Frontend

React + TypeScript SPA para gestão contábil multi-tenant.

## Stack

| Tecnologia | Versão | Uso |
|-----------|--------|-----|
| React | 18.3.1 | UI |
| TypeScript | 5.5.3 | Tipagem estática |
| Vite | 6.4.2 | Build tool (patch CVE GHSA-67mh-4wv8-2f99) |
| Tailwind CSS | 3.4.11 | Estilização |
| React Router | 6.26.0 | Roteamento SPA |
| TanStack Query | 5.56.2 | Data fetching + cache |
| Zustand | 4.5.5 | Estado global |
| Axios | 1.7.7 | HTTP client |
| React Hook Form | 7.53.0 | Formulários |
| Zod | 3.23.8 | Validação de schemas |
| Recharts | 2.12.7 | Gráficos |
| Framer Motion | 12.x | Animações |
| Lucide React | 0.441.0 | Ícones |
| React Hot Toast | 2.4.1 | Notificações toast |
| date-fns | 3.6.0 | Manipulação de datas |
| read-excel-file | 5.0.2 | Importação XLSX (substitui xlsx com CVE) |
| ESLint | 9.17.0 | Linting (flat config) |
| typescript-eslint | 8.19.0 | Regras TypeScript |

## Estrutura

```
frontend/src/
├── components/
│   ├── ui/                    # Button, Input, Card, Badge, FormField
│   ├── Header.tsx
│   ├── Sidebar.tsx            # Logo clicável → /dashboard
│   ├── ProtectedRoute.tsx
│   └── StateViews.tsx         # Loading, Error, Empty states
├── layouts/
│   └── DashboardLayout.tsx
├── lib/
│   ├── api.ts                 # Axios instance com interceptors JWT
│   ├── auth.ts                # Interfaces + funções de auth
│   ├── utils.ts               # cn() helper
│   └── hooks/
│       ├── useAuth.ts
│       └── useOperations.ts
├── pages/
│   ├── LoginPage.tsx          # Login email + Google OAuth
│   ├── RegisterPage.tsx       # Wizard 3 passos + seleção de plano
│   ├── DashboardPage.tsx      # Métricas + gráficos
│   ├── ClientsPage.tsx        # CRUD + importação XLSX
│   ├── DocumentsPage.tsx      # Upload Supabase + categorização
│   ├── FinancePage.tsx        # Receitas/despesas + gráficos
│   ├── DeadlinesPage.tsx      # Prazos fiscais + status
│   ├── CertificatesPage.tsx   # Certificados A1/A3 + validade
│   ├── SettingsPage.tsx       # 5 tabs de configuração
│   └── BillingPage.tsx        # (legado — substituído por tab em Settings)
├── stores/
│   └── authStore.ts           # Zustand: user, isAuthenticated, updateUser
├── App.tsx                    # Rotas + React.lazy + Suspense
└── main.tsx
```

## Comandos

```bash
npm install          # Instalar dependências
npm run dev          # Dev server em http://localhost:3000
npm run build        # Build de produção (TypeScript + Vite)
npm run type-check   # Verificação TypeScript sem emit
npm run lint         # ESLint 9 flat config
npm run preview      # Preview do build local
```

## Rotas

### Públicas
| Rota | Página |
|------|--------|
| `/login` | Login com email/senha ou Google OAuth |
| `/register` | Wizard 3 passos: empresa → usuário+OAuth → plano |

### Protegidas (requerem JWT)
| Rota | Página |
|------|--------|
| `/dashboard` | Métricas, gráficos, atalhos rápidos |
| `/clientes` | Lista, CRUD, importação XLSX |
| `/documentos` | Upload, categorização, associação a clientes |
| `/financeiro` | Receitas/despesas, filtros, gráficos |
| `/prazos` | Obrigações fiscais, status, alertas |
| `/certificados` | Certificados digitais, controle de validade |
| `/configuracoes` | Perfil, escritório, plano, senha, pagamento |

## Autenticação

- **Storage**: `localStorage` → `access_token`, `tenant_id`, `user` (JSON)
- **Interceptors**: Axios adiciona automaticamente `Authorization: Bearer` e `X-Tenant-ID`
- **401**: Redireciona para `/login` automaticamente
- **Google OAuth**: `@react-oauth/google` com `useGoogleLogin` (popup flow)
- **Zustand `updateUser`**: atualiza campos parciais do usuário com sync no localStorage

## Configurações (SettingsPage)

5 tabs implementadas:

| Tab | Endpoint | Descrição |
|-----|----------|-----------|
| Perfil | `PATCH /auth/me` | Nome, telefone |
| Escritório | `PATCH /auth/tenant` | Razão social, CNPJ, endereço, site |
| Plano | `PATCH /auth/tenant` | Free / Starter / Pro |
| Segurança | `POST /auth/change-password` | Troca de senha com validação |
| Pagamento | — | Estrutura preparada (Stripe futuro) |

## Registro (RegisterPage)

Wizard com `react-hook-form` por step:

1. **Step 1** — Dados da empresa (nome + CNPJ)
2. **Step 2** — Dados do contador (nome, email, telefone, senha) + botão Google OAuth
3. **Step 3** — Seleção de plano (Free / Starter / Pro com feature list)

Layout split: painel escuro com brand (lg+) + painel de formulário.

## Performance

| Métrica | Valor |
|---------|-------|
| Chunks gerados | 30+ |
| Maior chunk | 393 kB (recharts, gzip ~108 kB) |
| Build time | ~6s |
| Code splitting | React.lazy + Suspense em todas as páginas |
| Vendor chunks | react, query, charts, motion, form, utils |

## Segurança

- `npm audit`: **0 vulnerabilidades**
- `xlsx` (Prototype Pollution + ReDoS) → substituído por `read-excel-file`
- `vite` 6.4.2 corrige GHSA-67mh-4wv8-2f99 (esbuild)
- ESLint 9 sem packages deprecados

## Variáveis de Ambiente

```env
VITE_API_URL=https://contaflow.fly.dev
VITE_GOOGLE_CLIENT_ID=<google-oauth-client-id>
```

---

**FiscWise** por Vstack Solutions | Atualizado: 21/05/2026
