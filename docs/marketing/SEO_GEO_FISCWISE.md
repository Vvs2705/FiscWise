# SEO e GEO — FiscWise

Domínio canônico: `https://www.fiscwise.com.br` (Cloudflare Pages). Estado em 2026-11-12.

## 1. O que o PR técnico entrega
- `robots.txt`: libera páginas públicas, bloqueia a área autenticada (rotas reais do app: `/painel`, `/clientes`, `/notas-fiscais`, `/portal` etc., além de `/api`, `/app`, `/dashboard`). Sitemap apontado.
- `sitemap.xml`: só páginas públicas (`/login`, `/register`, `/faq/`, `/termos`, `/privacidade`).
- Meta por rota (`RouteTitle.tsx`): descrição e canonical únicos nas páginas públicas; `noindex` em tudo que é autenticado ou inexistente.
- `og-image.png` 1200x630 (prévia WhatsApp/LinkedIn) e Open Graph completo.
- Schema.org: `SoftwareApplication`, `Organization`, `WebSite` no `index.html`; `FAQPage` em `/faq/`. O `offers` com preço 0 foi removido até os preços serem aprovados.
- Página 404 personalizada (rota `*`, noindex). Não foi criado `404.html` estático porque isso desliga o modo SPA do Cloudflare Pages e quebraria links diretos.
- `_headers`: HSTS, X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy, COOP e **CSP em modo Report-Only**.
- `noscript` com resumo do produto no `index.html`.

## 2. GEO (citação por IAs)
- `llms.txt` com descrição, públicos, funções atuais e o que ainda está em desenvolvimento (sem prometer NFS-e, e-CAC ou WhatsApp oficial).
- `/faq/` estático (HTML puro, legível por qualquer crawler sem JavaScript) com 10 respostas diretas.
- **Decisão sobre crawlers de IA:** permitir GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot, Claude-SearchBot, Claude-User, PerplexityBot, Perplexity-User, Google-Extended e Applebot-Extended nas páginas públicas. Motivo: o objetivo é ser citado; não há conteúdo público sensível. As áreas privadas continuam bloqueadas nesses grupos. Reverter é só remover o grupo.
- Limitação: o app é SPA (Vite), então só as páginas estáticas são lidas sem JS. Pré-renderizar a landing e `/precos` é o próximo passo de maior impacto.

## 3. Palavras-chave e landing pages (posicionamento da Frente D)
Proposta: "Emita notas fiscais sem complicação, mesmo sem internet. Simples para a sua empresa, organizado para o seu contador."

| Campanha / landing | Público | Palavras-chave principais | Intenção |
|---|---|---|---|
| `/emitir-nota-fiscal` | MEI e pequena empresa | emitir nota fiscal, sistema emissor de nota fiscal, emissor de nfs-e, emitir nota fiscal mei, emissor de nota fiscal online | compra |
| `/emitir-nota-sem-internet` | empresas com internet instável | emitir nota fiscal offline, sistema fiscal offline, nfc-e contingência, emissor nfe offline | diferencial |
| `/para-escritorios-contabeis` | contadores e escritórios | software contábil para escritório, sistema de gestão contábil, controle de obrigações fiscais, calendário fiscal contabilidade | compra |
| `/precos` | todos | preço sistema emissor nota fiscal, quanto custa emitir nota fiscal, emissor de nota fiscal grátis | comparação |
| `/alternativa-planilha` | contador autônomo | controle de clientes contabilidade planilha, gestão de carteira de clientes contábil | descoberta |
| Conteúdo (blog/FAQ) | todos | prazo DAS MEI, certificado digital A1 vencimento, o que é NFS-e Nacional, diferença NF-e NFC-e NFS-e | topo de funil |

Regras: uma palavra-chave principal por página; title até 60 caracteres; description até 155; só afirmar funções que existem (emissão real de NFS-e e modo offline ainda são roadmap: usar "em breve" até lançar). Preços Essencial R$79, Profissional R$149, Escritório R$349 e teste de 14 dias **só entram no site depois da aprovação do dono**; ao aprovar, adicionar `offers` no schema e a página `/precos` em texto.

## 4. Search Console e Analytics (preparação; nada publicado)
Pendências do dono:
1. Criar propriedade de domínio no Google Search Console e verificar por registro TXT no DNS (Cloudflare). Enviar `https://www.fiscwise.com.br/sitemap.xml`.
2. Definir www como domínio preferido: redirecionar o apex `fiscwise.com.br` para `www` (Redirect Rule 301 no Cloudflare) e confirmar que `www` está como domínio customizado do projeto Pages.
3. Criar a propriedade GA4 e informar o ID (`G-XXXX`). Sugestão sem custo: Cloudflare Web Analytics, que dispensa cookies.

Eventos planejados (carregar somente após consentimento LGPD, banner de cookies):
- `sign_up` (cadastro concluído), `activation` (primeiro cliente cadastrado ou primeira nota/guia criada), `trial_start`, `purchase` (assinatura), `cta_click` com parâmetro `origem` da campanha (UTM).
- Registrar `utm_source/medium/campaign` no cadastro para medir cada landing.

## 5. Pendências
- Verificação do Search Console e ID do GA4 (dono).
- Redirect apex → www e confirmação de que `www` aponta ao Cloudflare Pages (o app antigo na Vercel respondia no `www`).
- Trocar CSP Report-Only por enforcement depois de conferir o console em produção (login Google, API, Sentry).
- Pré-renderização das landings e `/precos` depois da aprovação de preços.
