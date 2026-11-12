# DESIGN.md — Sistema de design do FiscWise

Fonte de verdade para cores, espaçamento, tipografia, raio, sombra, movimento e
estados dos componentes. Tokens vivem em `frontend/src/index.css` (CSS custom
properties) e são expostos ao Tailwind em `frontend/tailwind.config.js`.
Componentes base ficam em `frontend/src/components/ui/`.

## 1. Princípios

1. **Ferramenta de trabalho, não landing page.** Quem usa o FiscWise passa horas
   nele. Superfícies planas, bordas de 1px, densidade confortável e cor só onde
   carrega significado.
2. **Uma hierarquia por tela.** Um título, um subtítulo, uma ação primária. O
   resto é secundário ou terciário.
3. **Cor é semântica.** Laranja = ação primária e marca. Verde, âmbar, vermelho e
   azul = status. Nunca usar cor de status como decoração.
4. **Movimento curto e com propósito.** Resposta imediata ao toque (≤150 ms),
   entrada de conteúdo discreta (≤250 ms), nada em loop fora de spinner e
   skeleton. `prefers-reduced-motion` é respeitado globalmente.
5. **Desempenho é requisito de design.** Nada de `backdrop-filter`, blobs com
   `blur()`, gradientes empilhados ou sombras de 80px. Cada tela precisa abrir
   bem em celular fraco com 4G lento.

O que foi retirado de propósito (marcas de "feito com IA"): glassmorphism,
fundo em grade, blobs desfocados, badges em caixa alta com `tracking` largo
espalhados pela tela, botões com gradiente, ícones que crescem no hover,
raios de 28–30px, três famílias de fonte.

## 2. Cor

Todas em HSL sem a função, para `hsl(var(--x) / alpha)` funcionar.

| Token | Claro | Escuro | Uso |
|---|---|---|---|
| `--background` | 210 20% 98% | 215 28% 8% | fundo da aplicação |
| `--foreground` | 215 30% 14% | 210 20% 93% | texto principal |
| `--card` | 0 0% 100% | 215 25% 12% | superfícies (cards, tabelas, modais) |
| `--muted` | 210 16% 94% | 215 20% 16% | fundos secundários, skeleton |
| `--muted-foreground` | 215 12% 42% | 215 12% 62% | texto secundário (contraste ≥ 4.5:1 sobre card) |
| `--border` | 214 16% 88% | 215 16% 22% | bordas de 1px |
| `--primary` | 21 81% 37% | 22 85% 60% | ação primária e links; laranja da marca ajustado para AA (o #e05e18 cheio fica no ícone da logo) |
| `--primary-foreground` | 0 0% 100% | 22 60% 8% | texto sobre primário (escuro no tema escuro: branco sobre laranja claro dá 2.6:1) |
| `--accent` | 24 100% 95% | 22 40% 16% | fundo de destaque suave (hover, seleção) |
| `--success` | 152 60% 28% | 152 50% 48% | autorizado, pago, em dia |
| `--warning` | 31 92% 31% | 35 90% 55% | pendente, vence em breve |
| `--destructive` | 0 72% 44% | 0 85% 66% | rejeitado, vencido, erro |
| `--info` | 206 85% 36% | 206 80% 58% | informativo, em processamento |
| `--ring` | = primary | = primary | anel de foco |

Sidebar (navy, fixa nos dois temas): `--sidebar-bg 215 50% 11%`,
`--sidebar-fg 210 30% 94%`, `--sidebar-muted 215 15% 66%`,
`--sidebar-hover-bg 215 40% 16%`, `--sidebar-border 215 35% 18%`,
item ativo = `--sidebar-active-bg` (laranja `21 81% 37%` nos dois temas) com texto branco.

Regras:
- Texto secundário nunca abaixo de 4.5:1 sobre a superfície em que está.
- Texto colorido (primary/status) sobre fundo da mesma cor: no máximo `/10`
  parado e `/15` no hover. Acima disso o contraste cai abaixo de 4.5:1.
- Texto sobre fundo de status (`bg-success`, `bg-destructive`...) usa o
  `*-foreground` do token, nunca `text-white` (no escuro o foreground é escuro).
- Logo em tela cujo fundo segue o tema: `<Logo theme="auto" />`. `light`/`dark`
  só sobre fundo fixo (ex.: sidebar navy).
- Nada de `bg-white`, `text-black`, `gray-*`/`slate-*` fora de `print:`: use os
  tokens (`bg-card`, `text-foreground`, `text-muted-foreground`...).
- O CI roda `frontend/e2e/contrast.spec.ts` (axe, WCAG AA, claro e escuro, todas
  as telas) e reprova em qualquer violação.
- Status sempre com fundo `/10`, borda `/25` e texto na cor cheia (ver `Badge`).
- Gradiente só no ícone da logo.

## 3. Tipografia

Duas famílias, autoinstaladas (sem Google Fonts em runtime):

- **Geist** (variável) — toda a interface. Pesos usados: 400, 500, 600.
- **JetBrains Mono** (variável) — dados: CNPJ/CPF, chaves de acesso, valores em
  tabela, códigos. Pesos: 400, 500.

Escala (tamanho / altura de linha / peso):

| Papel | Classe | Valor |
|---|---|---|
| Título de página | `text-xl font-semibold tracking-tight` | 20/28 · 600 |
| Título de seção/card | `text-base font-semibold` | 16/24 · 600 |
| Corpo | `text-sm` | 14/20 · 400 |
| Rótulo de campo | `text-sm font-medium` | 14/20 · 500 |
| Apoio / meta | `text-xs text-muted-foreground` | 12/16 · 400 |
| Número de destaque | `text-2xl font-semibold tabular-nums` | 24/32 · 600 |
| Hero (login) | `text-3xl md:text-4xl font-semibold tracking-tight` | 30–36 · 600 |

Números sempre com `tabular-nums`. Nada em caixa alta com `tracking` largo,
exceto o rótulo de grupo da sidebar (11px, 500, `tracking-wide`).

## 4. Espaçamento

Escala de 4px (Tailwind padrão). Usar só: 1 (4) · 2 (8) · 3 (12) · 4 (16) ·
5 (20) · 6 (24) · 8 (32) · 10 (40) · 12 (48).

- Padding de card: `p-5` (20px). Em telas pequenas `p-4`.
- Gap entre cards: `gap-4`. Entre seções de página: `space-y-6`.
- Padding da página: `p-4 md:p-6`.
- Altura de controles: input/botão `h-10` (40px); compacto `h-8`; destaque `h-11`.
- Largura máxima de formulário: `max-w-md` (448px). De conteúdo de leitura: `max-w-3xl`.

## 5. Raio

| Token | Valor | Uso |
|---|---|---|
| `--radius-sm` | 6px | badges, chips, checkbox |
| `--radius` | 8px | botões, inputs, menus |
| `--radius-lg` | 12px | cards, modais, drawers |
| `rounded-full` | — | avatar, status dot, toggle |

Tailwind: `rounded-sm` → 6px, `rounded-md` → 8px, `rounded-lg` → 12px.
Aliases legados `rounded-card` e `rounded-panel` resolvem para 12px.

## 6. Sombra

Três níveis, todos discretos. Superfícies de página (cards) usam só borda.

| Token | Valor | Uso |
|---|---|---|
| `--shadow-sm` | `0 1px 2px hsl(215 30% 14% / 0.06)` | botão primário, input em foco |
| `--shadow-md` | `0 4px 12px -2px hsl(215 30% 14% / 0.10)` | popover, dropdown, card em hover (quando clicável) |
| `--shadow-lg` | `0 16px 40px -12px hsl(215 30% 14% / 0.18)` | modal, drawer, cartão de login |

Sem "glow" e sem sombra colorida.

## 7. Movimento

Tokens em `frontend/src/lib/motion.ts` e utilitários em `index.css`.

| Nome | Duração | Easing | Uso |
|---|---|---|---|
| `instant` | 100 ms | ease-out | hover/active de botões e links |
| `fast` | 150 ms | ease-out | troca de cor/opacidade, toggle |
| `base` | 200 ms | `cubic-bezier(0.2, 0, 0, 1)` | abrir popover, mostrar badge |
| `enter` | 250 ms | `cubic-bezier(0.2, 0, 0, 1)` | entrada de página/card (`fade + 6px`) |

Regras:
- Entrada de página: fade + translateY(6px), 250 ms, uma vez. Sem stagger acima de 4 itens, e com passo de 40 ms.
- Nada de `scale` em hover. Pressionar = `active:scale-[0.98]` apenas em botões.
- Loop permitido só em spinner e skeleton.
- Animar só `opacity` e `transform`. Nunca `height`, `box-shadow`, `filter`.
- `@media (prefers-reduced-motion: reduce)` zera animações e transições no CSS global, e `MotionConfig reducedMotion="user"` cobre o framer-motion.
- framer-motion fica fora das rotas públicas (login, cadastro, termos). Lá só CSS.

## 8. Componentes base e estados

Todos em `frontend/src/components/ui/`.

| Componente | Variantes | Estados obrigatórios |
|---|---|---|
| `Button` | `default` (primário), `secondary`, `outline`, `ghost`, `destructive`, `link` · tamanhos `sm` `md` `lg` · `loading` | hover, active, focus-visible (anel 2px), disabled (opacity 50), loading (spinner + texto, largura estável) |
| `Input` / `Select` / `Textarea` | — · `invalid` | hover (borda), focus (anel), disabled, invalid (borda destructive + mensagem) |
| `FormField` | — | rótulo, ajuda, erro, obrigatório |
| `Card` | `Card` `CardHeader` `CardTitle` `CardDescription` `CardContent` `CardFooter` · `interactive` | hover só quando `interactive` |
| `Badge` / `StatusBadge` | `neutral` `success` `warning` `danger` `info` `primary` | — |
| `EmptyState` | ícone, título, descrição, ação opcional | único componente (o duplicado em `StateViews` reexporta este) |
| `ErrorState` | mensagem, ação "tentar novamente" | — |
| `Skeleton` | `Skeleton` `SkeletonCard` `SkeletonTable` `SkeletonList` | shimmer; estático com reduced-motion |
| `PageHeader` | título, subtítulo, ações, breadcrumb | — |
| `Dialog` / `Drawer` | — | foco preso, Esc fecha, backdrop `bg-foreground/40` |
| `Table` | — | cabeçalho fixo, linhas 44px, números em mono tabular |

Toda listagem tem os quatro estados: carregando (skeleton com a mesma forma do
conteúdo), vazio (EmptyState com próxima ação), erro (ErrorState com retry) e
conteúdo.

## 9. Responsividade

- Mobile first. Breakpoints Tailwind: `sm 640` `md 768` `lg 1024` `xl 1280`.
- Sidebar: ícones em `< md`, completa em `≥ md`. Header 56px.
- Tabelas largas viram cards em `< md` ou ganham scroll horizontal com a
  primeira coluna fixa; nunca quebram o layout da página.
- Alvo de toque mínimo 40×40px.
- Sem `overflow: hidden` em `body`.

## 10. Login (rota pública)

Objetivo: em 5 segundos o visitante entende o que é, para quem é e o benefício.

- Barra superior de largura total: logo à esquerda, "Criar conta grátis" à direita.
- Esquerda: formulário sem cartão e sem distração (Google, e-mail, senha, entrar,
  linha de segurança abaixo do botão).
- Direita (≥ lg): painel claro quente com o posicionamento e "Como funciona" em
  3 passos. Abaixo de lg vira versão compacta embaixo do formulário.
- Nada de métricas inventadas, radar ou gráficos decorativos.
- Texto oficial vem de `docs/marketing/` (Frente D). Sem preços na tela de login.
- Só CSS. Sem framer-motion, sem animação em loop, sem imagem pesada. Entrada única de 200 ms.

## 11. Checklist de revisão visual (PR)

- [ ] Uma ação primária por tela.
- [ ] Nenhum `backdrop-blur`, `blur-3xl`, gradiente em botão ou sombra "glow".
- [ ] Raio só 6/8/12/full.
- [ ] Espaçamento só da escala.
- [ ] Texto secundário com contraste ≥ 4.5:1 (claro e escuro); `contrast.spec.ts` verde.
- [ ] Estados carregando/vazio/erro presentes.
- [ ] Funciona em 360px de largura sem scroll horizontal.
- [ ] Animações só em opacity/transform, ≤ 250 ms, respeitam reduced-motion.

## 12. Identidade (decisão única)

A identidade estava dividida: os SVGs estáticos em `frontend/public/` eram
índigo (#5B6FEE) com Inter e a tagline "Gestão contábil"; o `Logo.tsx`, o
`theme-color` e o `--primary` eram laranja (#e05e18) com Syne e "Rotina fiscal".

**Decisão: laranja + navy.** É a cor que a aplicação já usa em todos os
botões, estados ativos e no ícone renderizado pelo React, e é a cor da marca
V-Stack.

| Elemento | Valor |
|---|---|
| Ícone (fundo) | gradiente `#e05e18 → #f07028`, raio 25% do lado |
| Ícone (barras e seta) | branco, opacidades 0.55 / 0.78 / 1.0 |
| Wordmark | "FiscWise", Geist 600, `letter-spacing -0.02em`; navy `#1A2540` no claro, `#EEF1FA` no escuro |
| Tagline | nenhuma dentro da logo (ilegível em 32px e muda com o posicionamento) |
| `theme-color` | `#e05e18` |
| Favicon | mesmo ícone, 48×48, fundo laranja |

`favicon.svg`, `logo.svg` e `logo-dark.svg` em `frontend/public/` seguem esta
tabela e o `Logo.tsx` é a referência geométrica.
