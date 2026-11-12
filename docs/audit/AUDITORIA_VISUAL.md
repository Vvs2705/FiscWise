# Auditoria visual do front — FiscWise (Frente C, 2026-11-12)

Base auditada: `main` em `485093f`. Front: **Vite 6 + React 18 + Tailwind 3 +
shadcn (manual) + framer-motion**, hospedado no **Cloudflare Pages** (não é
Next.js; o `vercel.json` é legado). Build base: 6,3 s; lint 0 erros; 14 testes.

## 1. Diagnóstico geral

O visual tem os sinais clássicos de "feito com IA": muitos efeitos ao mesmo
tempo e pouca hierarquia. Nada está quebrado, mas nada parece decidido.

| Área | Achado | Evidência |
|---|---|---|
| Hierarquia | Login tem 2 h1-like, 3 badges em caixa alta, 3 cards de confiança, 4 métricas flutuantes, radar animado e 3 chips, tudo na mesma tela | `LoginBrandPanel.tsx`, `FloatingMetricCards.tsx`, `FiscalRadarAnimation.tsx` |
| Tipografia | 3 famílias carregadas (Syne, Geist, JetBrains Mono) e **Syne nunca é usada** (`font-display`: 0 ocorrências). 10 pesos pedidos ao Google Fonts | `index.html`, `tailwind.config.js` |
| Cor | Identidade dividida: SVGs estáticos índigo (#5B6FEE), app laranja (#e05e18) | `public/*.svg` vs `Logo.tsx` |
| Contraste | `text-muted-foreground/80`, `/90` e textos de 10–11px sobre vidro (`bg-white/5 backdrop-blur`) ficam abaixo de 4.5:1 | login, sidebar |
| Superfícies | `backdrop-filter: blur(12px)` em todo card (`.fiscwise-surface`), `background-attachment: fixed` com 3 gradientes no body, grade de fundo (`.fiscwise-grid`) | `index.css` |
| Sombra | `0 28px 80px` e "glow" laranja em botões; sombras coloridas hard-coded (`rgba(224,94,24,…)`) | `Button.tsx`, `index.css` |
| Raio | 7 raios diferentes em uso (6, 8, 12, 16, 18, 28, 30px) | login, cards |
| Badges | Pílulas em caixa alta com `tracking-[0.2em]` como decoração ("Fiscal Intelligence OS", "Login seguro") | login, sidebar |
| Movimento | Ícones crescem no hover (`group-hover:scale-110`), botões sobem no hover, 2 animações infinitas no login, stagger em toda lista. `prefers-reduced-motion` só cobre framer-motion, não as classes CSS | `Sidebar.tsx`, `Card.tsx`, `index.css` |
| Componentes | `EmptyState` duplicado (`ui/EmptyState.tsx` e `ui/StateViews.tsx`) com visuais diferentes; `Skeleton` anima duas vezes (`skeleton` + `animate-pulse`); botão `premium` com gradiente | `components/ui` |
| Estados | Erro sem ação de "tentar novamente"; `PageLoader` é um spinner de tela cheia em vez de skeleton | `StateViews.tsx`, `App.tsx` |
| Responsividade | Login força `body { overflow: hidden }` em ≥ 1024px; sidebar sem fechar em mobile, só ícones; header 64px com frase de boas-vindas que trunca | `LoginPage.tsx`, `Header.tsx` |
| Header | Mapa de títulos desatualizado (`/dashboard`, `/agenda-prazos`) — a maioria das rotas mostra "FiscWise" | `Header.tsx` |

## 2. Desempenho do front (medido no build)

| Item | Achado | Impacto |
|---|---|---|
| Dependências mortas | `recharts`, `react-hot-toast`, `date-fns`, `embla-carousel-react`, `@tanstack/react-table`, 3 pacotes `@radix-ui` têm 0 imports (o Rollup já não os empacotava; removidos para encolher `npm ci`, `npm audit` e o lockfile) | 55 pacotes a menos no `node_modules` |
| framer-motion no login | 128 kB (42 kB gz) carregado na rota pública só para fade-in | LCP do login |
| Fontes | 2 requisições bloqueantes ao Google Fonts, 10 pesos | FOUT/LCP; dependência externa |
| Efeitos de GPU | `backdrop-filter` em todos os cards + `background-attachment: fixed` | jank em celular fraco |
| React Query | `staleTime` 0 → refetch em toda navegação | tráfego no banco (Neon já suspendeu por excesso) |
| Debounce | Só em Clientes e Documentos; outras 8 buscas filtram a cada tecla | CPU em listas grandes |
| Imagens | 2 `<img>` sem `loading="lazy"` / `decoding="async"` | pequeno |
| Google OAuth script | `GoogleOAuthProvider` carrega o script do Google em todas as rotas | terceiro em rotas que não precisam |
| Cache | `/assets/*` imutável OK; fontes e SVGs sem regra | pequeno |
| SSR | SPA pura: `/login`, `/termos`, `/privacidade` não têm HTML pré-renderizado | SEO (Frente E); pendência |

Baseline de tamanho (gzip): vendor-react 53,7 kB · vendor-motion 42,2 kB ·
vendor-utils 27,6 kB · vendor-query 12,8 kB · SettingsPage 17,9 kB ·
ClientDetailCockpit 16,8 kB · DashboardPage 10,4 kB.

## 3. Decisões (ver `DESIGN.md`)

1. Identidade única: laranja #e05e18 + navy; 2 famílias (Geist + JetBrains Mono), autoinstaladas.
2. Superfícies planas, borda 1px, 3 sombras discretas, raio 6/8/12.
3. Sem vidro, sem blobs, sem grade, sem gradiente em botão, sem glow.
4. Movimento ≤ 250 ms, só opacity/transform, reduced-motion global em CSS.
5. Um `EmptyState`, um `ErrorState` com retry, skeletons com a forma do conteúdo.
6. Login reescrito só com CSS, com o posicionamento da Frente D.

## 4. Plano de PRs

| PR | Conteúdo | Merge |
|---|---|---|
| C1 — Sistema de design e base | tokens, fontes, componentes base, shell (sidebar/header), motion, identidade dos SVGs | sim, com CI verde |
| C2 — Desempenho do front | deps mortas, chunks, React Query, debounce, imagens, OAuth lazy, headers | sim, com CI verde |
| C3 — Login reformulado | nova tela de login com posicionamento D | **não** (autenticação: fila de aprovação) |
