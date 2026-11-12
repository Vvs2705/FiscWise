# Plano de Marketing e Identidade — FiscWise

> **Status: rascunho 2.** Posicionamento da Frente D incorporado. Seções marcadas com 🔒 aguardam os tokens de design da Frente C. Nada aqui foi gerado com crédito pago nem publicado.

## Índice
1. Posicionamento, público e mensagens-chave
2. Logo: diagnóstico e 3 direções de evolução
3. Vídeos em IA: 5 roteiros
4. Folders e banners: formatos, textos e direção visual
5. Calendário de lançamento de 30 dias e métricas
6. Regras de honestidade e compliance
7. Pendências e decisões do dono

---

## 1. Posicionamento, público e mensagens-chave

Fonte: Frente D (`docs/marketing/PESQUISA_CONCORRENTES_PRECOS.md`, PR #66, coleta de 2026-11-12). **Preços e planos são proposta, ainda não aprovada pelo dono: não aparecem em nenhuma peça pública até a aprovação.**

- **Público principal:** donos de pequenas empresas e MEIs que emitem notas fiscais. **Secundário (e canal de indicação):** escritórios contábeis que cuidam da carteira deles.
- **Dor principal:** emitir nota é caro, complicado e para quando a internet cai ou o sistema fica lento; ERP completo custa demais para quem só quer emitir e organizar.
- **Proposta de valor:** "Emita notas fiscais sem complicação, mesmo sem internet. Simples para a sua empresa, organizado para o seu contador."
- **Pilares de mensagem:** (1) emissão em poucos cliques; (2) continua funcionando sem internet e sincroniza ao voltar; (3) o contador acessa tudo, sem planilha nem e-mail.
- **Provas de confiança:** servidores no Brasil, LGPD, 14 dias grátis sem cartão.
- **Faixa de mercado:** concorrentes diretos cobram de R$ 62,90 a R$ 135,92 na entrada (Focus NFe Retail, Simplifique Essencial) e ERPs partem de R$ 200 a R$ 340; a proposta ocupa a faixa R$ 79 a R$ 349 (Essencial, Profissional, Escritório).
- **Tom de voz:** direto, calmo, profissional; frases curtas; sem jargão de IA, sem exclamações em excesso, sem "revolucionário".
- **Palavras a evitar:** "100% automático", "sem erros", "garantido pela Receita", "grátis para sempre", comparação nominal com concorrentes em peça paga.

### 1.1 Trava de honestidade: o que o produto faz hoje x o que a mensagem promete

O README do repositório (estado de hoje) marca emissão de NFS-e como dependente de homologação (provider de simulação) e não cita NF-e/NFC-e nem modo offline; offline e sincronização são a Frente G, ainda em arquitetura. Portanto:

| Mensagem | Condição para ir ao ar |
|---|---|
| "Emissão de NF-e, NFS-e e NFC-e" | emissão real homologada na SEFAZ/prefeitura, por tipo de nota; anunciar só os tipos que funcionam |
| "Funciona sem internet" | PWA/offline entregue e testado (Frente G); texto obrigatório: **offline a nota fica "Pendente de transmissão"; só a SEFAZ autoriza** |
| "Contador com acesso nativo" | acesso do contador / portal em produção (hoje há Portal do Cliente) |
| "14 dias grátis sem cartão" | fluxo de cadastro e cobrança configurados assim |
| "Servidores no Brasil / LGPD" | já sustentável: Cloud Run SP, Supabase SP, Cloudflare; manter política de privacidade atualizada |

**Regra:** o calendário de 30 dias só começa (D1) depois que os três primeiros itens estiverem em produção. Até lá, valem apenas peças de pré-lançamento/lista de espera, sem prometer a função.


## 2. Logo

### 2.1 Diagnóstico da logo atual

Fontes analisadas: `frontend/public/logo.svg`, `logo-dark.svg`, `favicon.svg`, `frontend/src/components/Logo.tsx`, `frontend/index.html` e os tokens em `frontend/src/index.css`.

**Achados**

| # | Achado | Evidência | Gravidade |
|---|---|---|---|
| 1 | **Duas identidades de cor convivem.** Os SVGs estáticos e o favicon são índigo (`#5B6FEE → #3A52C9`); o componente `Logo.tsx`, o `theme-color` e o `--primary` da interface são laranja (`#e05e18`/`hsl(21 81% 49%)`). | `public/*.svg` vs `Logo.tsx`, `index.html:19`, `index.css:14` | Alta |
| 2 | **Duas taglines diferentes.** SVGs dizem "GESTÃO CONTÁBIL"; `Logo.tsx` diz "ROTINA FISCAL"; o `<title>` diz "Gestão Contábil Inteligente". | idem | Alta |
| 3 | **Duas famílias tipográficas no wordmark.** SVGs usam Inter; o componente usa Syne + Geist. Wordmark em `<text>` depende da fonte carregada, então muda de aparência (ou cai em system-ui) quando a fonte falha. | `logo.svg:21`, `Logo.tsx` | Alta |
| 4 | **Símbolo genérico.** Três barras crescentes + linha de tendência + seta de alta é o clichê de "dashboard financeiro"; serve a qualquer fintech e não comunica fiscal/contábil nem o nome. | `favicon.svg` | Média |
| 5 | **Excesso de elementos para tamanhos pequenos.** Três opacidades (0,55/0,78/1), linha de tendência a 45% e seta a 90% sobre gradiente: em 16–32 px as camadas somem e viram borrão. | `favicon.svg` | Média |
| 6 | **Gradiente no ícone** dificulta uso em 1 cor (carimbo, fax/impressão P&B, bordado, relevo) e em fundos coloridos. | `bg`/`bg2` | Média |
| 7 | **Sem versões de uso:** não há monocromática, negativa (fundo escuro) com ícone próprio, nem área de respiro/tamanho mínimo definidos. | pasta `public/` | Média |
| 8 | **`apple-touch-icon` aponta para SVG**, que o iOS ignora; ícone PWA ausente em PNG 180/192/512. | `index.html:8` | Baixa (afeta atalho no celular e a futura PWA) |
| 9 | **Mascote da marca ausente / nome não explorado.** "Wise" (sábio) e "Fisc" (fisco) têm potencial gráfico não usado. | — | Oportunidade |

**Conclusão:** o ativo mais urgente não é redesenhar, é **unificar** (uma cor, uma tagline, uma fonte, vetores com texto convertido em curvas). A evolução visual abaixo parte dessa base.

### 2.2 Três direções de evolução 🔒 (cores e tipografia finais dependem dos tokens da Frente C)

Cada direção traz: conceito, paleta provisória, tipografia, aplicação e **prompt pronto** (para gerar em IA depois, sem execução agora). Paletas usam a cor primária atual (laranja) como âncora até a Frente C confirmar os tokens.

**Direção A — "Monograma FW" (evolução conservadora)**
- Conceito: mantém o quadrado arredondado, troca as três barras por um monograma **F + W** em traço único, com um pequeno "check" no vértice (conferido/em dia).
- Cores: laranja primário + azul-petróleo escuro (`--foreground`) + branco. Sem gradiente (cor chapada, versão 1 cor trivial).
- Tipografia: wordmark em sans geométrica (família do DESIGN.md), peso 700, sem tagline fixa no lockup principal.
- Prompt (placeholder): *"Minimalist app icon, rounded square, solid orange (#E05E18) background, white monogram letters F and W formed by a single continuous line, tiny check mark at the top-right vertex, flat vector, no gradient, no shadow, high contrast, readable at 16px, centered, plain background"*

**Direção B — "Nota/Documento" (comunica a emissão simples)**
- Conceito: a promessa passa a ser "nota fiscal sem complicação". Símbolo = uma folha de nota/documento estilizada cujo canto dobrado forma a letra F.
- Cores: azul-petróleo escuro como base, laranja como destaque único (o "ok" da nota).
- Tipografia: wordmark em duas palavras de pesos diferentes (**Fisc**Wise: Fisc 700, Wise 400) para explorar o nome.
- Prompt (placeholder): *"Flat vector logo mark, stylized invoice document page with folded top-right corner forming the letter F, deep teal-navy shape with one small orange check square, geometric, minimal, solid colors, no gradient, works in one color, square canvas, white background"*

**Direção C — "Selo Wise" (confiança e segurança)**
- Conceito: selo/escudo de contorno limpo com uma barra ascendente única dentro (crescimento seguro). Transmite LGPD/segurança sem usar cadeado clichê.
- Cores: azul-petróleo + laranja, com versão negativa pensada para fundo escuro (sidebar/login).
- Tipografia: wordmark em caixa-alta espaçada para uso institucional (folder, rodapé de proposta).
- Prompt (placeholder): *"Minimal emblem logo, rounded shield outline with a single ascending bar and a small dot inside, line weight consistent, navy and orange, flat vector, no gradient, monochrome-friendly, symmetrical, white background, app icon safe area"*

**Recomendação provisória:** Direção A para o menor risco e a menor quebra visual com a interface atual; Direção B, agora favorecida: o posicionamento da Frente D gira em torno da nota fiscal. Decisão final: dono.

### 2.3 Kit mínimo de entrega da logo (checklist para quando houver a arte final)
- [ ] Ícone e logo completa em SVG com **texto convertido em curvas**
- [ ] Versões: colorida, negativa (fundo escuro), monocromática preta e branca
- [ ] Favicon 16/32/48 + PNG 180 (apple-touch), 192 e 512 (PWA) + maskable
- [ ] Imagem Open Graph 1200×630
- [ ] Área de respiro (1× altura do "F") e tamanho mínimo (ícone 16 px, logo completa 96 px de largura)
- [ ] Remover "GESTÃO CONTÁBIL"/"ROTINA FISCAL" dos lockups ou trocar por "Notas fiscais sem complicação" (posicionamento da Frente D); o README e o `<title>` também falam em gestão contábil e precisam ser alinhados
- [ ] Atualizar `Logo.tsx`, `public/*.svg`, `index.html` e `theme-color` juntos (um único PR de identidade)

## 3. Vídeos em IA — 5 roteiros

Todos em PT-BR, vertical 9:16 salvo indicação, legenda queimada obrigatória (a maioria assiste sem som). Frases de locução ≤ 12 palavras. **Nenhum prompt foi executado**; Higgsfield e ElevenLabs consomem crédito e dependem de aprovação do dono. Divisão de ferramentas: telas do produto e tipografia animada → **HyperFrames** (HTML, fiel ao produto real e barato); cenas de pessoas e ambiente → **Higgsfield**; locução → **ElevenLabs**. Vídeos com tela do produto só podem ser gravados quando a função existir (ver 1.1).

### Vídeo 1 — "Sem internet, sem problema" (30 s) · lançamento principal
- **Gancho (0–3 s):** dono de loja, balcão cheio, o Wi-Fi cai. Texto em tela: "A internet caiu. E a fila?"
- **Cenas:** (1) 0–3 s balcão e ícone de Wi-Fi cortado · (2) 3–9 s tela do FiscWise com indicador "Offline" e a nota sendo preenchida normalmente · (3) 9–15 s nota marcada "Pendente de transmissão" · (4) 15–22 s a rede volta, indicador "Sincronizando" e a nota vira "Autorizada" · (5) 22–30 s logo, frase de valor, "Teste grátis por 14 dias. Sem cartão."
- **Locução:** "A internet caiu. [pausa curta] Sua loja não precisa parar. No FiscWise você continua preenchendo as notas. Quando a conexão volta, tudo é enviado e autorizado. Emita notas sem complicação, mesmo sem internet."
- **Ferramentas:** cena 1 Higgsfield · cenas 2–4 HyperFrames · voz ElevenLabs.
- **Prompt Higgsfield (cena 1):** *"Vertical 9:16, small Brazilian shop owner behind a busy counter, customers waiting, phone screen showing no Wi-Fi signal, warm natural light, realistic, handheld, 4 seconds, no text, no logos"*
- **Prompt ElevenLabs:** voz feminina ou masculina brasileira, calma e confiante, ritmo médio, sem sotaque regional marcado; texto da locução acima.
- **Prompt HyperFrames:** *"Product demo, 9:16, dark teal background, FiscWise UI mockup: status pill changes Offline → Pendente de transmissão → Sincronizando → Autorizada, calm easing, orange accent, large legible captions in Portuguese"*

### Vídeo 2 — "Emitir nota em poucos cliques" (20 s)
- **Gancho:** "Quanto tempo você leva para emitir uma nota?" (texto em tela, relógio correndo)
- **Cenas:** tela de emissão passo a passo (cliente, itens, emitir), contador de cliques na lateral ("3 cliques"), resultado com PDF/DANFE baixado.
- **Locução:** "Cliente, itens, emitir. Em poucos cliques a nota está pronta. Sem menus escondidos. FiscWise: emitir nota, sem complicação."
- **Ferramentas:** HyperFrames (gravar a tela real) · ElevenLabs.
- **Prompt HyperFrames:** *"Screen-recording style, 9:16, step counter 1-2-3 overlay, cursor clicks, soft zoom on key fields, no real customer data, fictional example names"*
- **Condição:** só gravar com a emissão real funcionando; usar dados fictícios.

### Vídeo 3 — "Seu contador, no mesmo lugar" (30 s)
- **Gancho:** "Você ainda manda nota por e-mail para o contador?"
- **Cenas:** (1) pilha de e-mails e planilhas · (2) dono e contador vendo a mesma tela, cada um com seu acesso · (3) contador baixando o XML do mês em um clique · (4) CTA.
- **Locução:** "Chega de mandar nota por e-mail. No FiscWise seu contador acessa tudo direto. Menos retrabalho para você, mais organização para ele."
- **Ferramentas:** cena 1 Higgsfield (ou HyperFrames com tipografia animada) · cenas 2–3 HyperFrames · ElevenLabs.
- **Prompt Higgsfield:** *"Vertical, cluttered desktop with email notifications and spreadsheet printouts, soft clutter turning into a clean single screen, shallow depth of field, realistic, no readable text"*
- **Condição:** acesso do contador em produção.

### Vídeo 4 — "Para escritórios contábeis" (45 s, 16:9 para site e LinkedIn)
- **Gancho:** "30 clientes. 30 jeitos de mandar nota."
- **Cenas:** painel multiempresa, importação de XML em lote, perfis de acesso por cliente, onboarding assistido, CTA "Plano Escritório" **(sem preço até a aprovação)**.
- **Locução:** "Uma carteira, um painel. Todos os clientes, as notas do mês e os XMLs no mesmo lugar. Seu escritório ganha tempo e seus clientes ganham clareza."
- **Ferramentas:** HyperFrames · ElevenLabs.
- **Prompt HyperFrames:** *"16:9 product walkthrough, multi-company dashboard, list of fictional companies, batch XML import progress bar, clean white UI on teal frame, calm motion"*
- **Condição:** painel multiempresa e importação em lote entregues.

### Vídeo 5 — "Seus dados no Brasil, com LGPD" (20 s)
- **Gancho:** "Onde ficam os dados da sua empresa?"
- **Cenas:** mapa do Brasil com marcador em São Paulo, ícone de proteção, texto "LGPD", "14 dias grátis. Sem cartão."
- **Locução:** "Os dados da sua empresa ficam em servidores no Brasil, protegidos conforme a LGPD. Teste o FiscWise por 14 dias, sem cartão."
- **Ferramentas:** HyperFrames · ElevenLabs.
- **Prompt HyperFrames:** *"Minimal motion graphic, 9:16, stylized Brazil outline, one pulsing marker on São Paulo, shield icon, calm teal and orange palette, large Portuguese captions"*
- **Condição:** política de privacidade e termos publicados e coerentes com o texto (já existem páginas de Privacidade e Termos no sistema; revisar).

## 4. Folders e banners

### 4.1 Formatos

| Peça | Medida | Uso | Observação |
|---|---|---|---|
| Feed quadrado | 1080×1080 | Instagram/LinkedIn | texto ≤ 20% da área, headline curta |
| Feed retrato | 1080×1350 | Instagram | melhor alcance orgânico |
| Stories/Reels capa | 1080×1920 | Instagram/WhatsApp Status | manter 250 px livres no topo e na base |
| Banner de site (hero) | 1920×600 (desktop) + 750×900 (mobile) | landing | WebP/AVIF, ≤ 150 KB |
| Open Graph | 1200×630 | prévia no WhatsApp/LinkedIn | logo + frase de valor |
| Capa LinkedIn | 1584×396 | página da empresa | |
| Anúncio horizontal | 1200×628 | Meta/LinkedIn Ads | só com aprovação e orçamento do dono |
| Folder A4 | 210×297 mm, 3 mm de sangria, 300 dpi, CMYK (gráfica) / RGB (digital) | e-mail, WhatsApp, evento | 3 painéis ou frente e verso |
| Assinatura de e-mail | 600 px de largura | equipe | |

### 4.2 Textos prontos (por peça)

**Campanha 1 — Dono de pequena empresa/MEI**
- Headline: **Emita notas sem complicação. Até sem internet.**
- Subtítulo: Emissão em poucos cliques, continua funcionando sem conexão e sincroniza quando a rede volta.
- Benefícios: Emita NF-e, NFS-e e NFC-e em poucos cliques* · Trabalhe sem internet e sincronize depois · Seu contador acessa tudo, sem planilha nem e-mail.
- Prova: Dados em servidores no Brasil · LGPD · 14 dias grátis, sem cartão.
- CTA: **Teste grátis por 14 dias**.
- Nota legal obrigatória (pequena, mas legível): *Sem internet, a nota fica "Pendente de transmissão" e só é autorizada pela SEFAZ quando a conexão voltar.*
- *\*Listar apenas os tipos de nota realmente liberados na data da publicação.*

**Campanha 2 — Escritório contábil**
- Headline: **Toda a carteira de notas dos seus clientes em um só painel.**
- Subtítulo: Simples para a empresa, organizado para o contador.
- Benefícios: Painel multiempresa · Importação de XML em lote · Perfis de acesso por cliente.
- CTA: **Fale com a gente / Teste grátis**.

**Banner de site (hero):** H1 "Emita notas fiscais sem complicação, mesmo sem internet." · sub "Simples para a sua empresa, organizado para o seu contador." · botão "Teste grátis por 14 dias" · linha de confiança "Servidores no Brasil · LGPD · Sem cartão".

**Stories (3 telas):** (1) "A internet caiu?" · (2) "Continue emitindo. Envia quando voltar." · (3) "Teste grátis por 14 dias" + link.

**Folder A4 (3 painéis):** capa = headline + logo · miolo = 3 benefícios com ícones + mini captura de tela + passo a passo "Cadastre → Emita → Seu contador acompanha" · contracapa = prova (Brasil, LGPD), CTA com QR code para a página de cadastro, contato. Tabela de planos **só entra no folder depois da aprovação de preços**.

### 4.3 Direção visual 🔒 (a fechar com os tokens da Frente C)
Alinhada ao `DESIGN.md` da Frente C: tokens de cor, no máximo 2 famílias tipográficas, espaçamento em escala. Hoje a interface usa Syne (display) e Geist (corpo), laranja primário e azul-petróleo escuro; **confirmar com a Frente C**. Regras provisórias: fundo claro ou petróleo escuro; um único destaque laranja por peça; capturas de tela reais com dados fictícios; pessoas só se geradas ou licenciadas sem custo extra, sem imitar pessoa real; fotografia opcional.

### 4.4 Cuidado com o que a peça promete
O README marca NFS-e (provider de simulação), e-CAC/SERPRO e WhatsApp oficial como roadmap, e a Frente G (offline) está em arquitetura. Nenhuma peça pode usar função ainda não liberada em produção; aplicar a tabela da seção 1.1 antes de cada publicação. A nota legal sobre "Pendente de transmissão" acompanha toda peça que cite o modo offline.

## 5. Calendário de lançamento de 30 dias

Premissas: sem anúncio pago sem aprovação; canais orgânicos, comunidades de pequenos empreendedores e contadores; sem clientes ainda, então nada de depoimentos inventados. **D1 só acontece com os 3 primeiros itens da seção 1.1 em produção.** Enquanto isso, vale a fase Pré (lista de espera).

| Fase | Objetivo | Entregas | Responsável |
|---|---|---|---|
| **Pré (D-14 a D-1)** | Preparar base | Identidade unificada (logo, ícones, OG); landing e FAQ (Frente E); analytics com consentimento LGPD; lista de espera; aprovação de preços; gravação das telas | Dono + Frentes C/E |
| **Semana 1 (D1–D7)** | Anunciar | Post de lançamento; Vídeo 1 ("Sem internet, sem problema"); mensagem pessoal a 30 contatos (empresários e contadores); FAQ no ar | Dono |
| **Semana 2 (D8–D14)** | Demonstrar | Vídeo 2 (poucos cliques); carrossel "5 problemas de emitir nota em sistema pesado"; demonstração gravada de 3 min | Dono |
| **Semana 3 (D15–D21)** | Aproximar contadores | Vídeo 3 (contador no mesmo lugar); Vídeo 4 (escritórios); convidar 5 a 10 escritórios para o piloto; coleta de feedback | Dono |
| **Semana 4 (D22–D30)** | Converter | Vídeo 5 (Brasil e LGPD); relato do piloto **com autorização por escrito**; e-mail de fim de teste (dia 12 dos 14); revisão das métricas e decisão sobre anúncio pago | Dono + orquestrador |

Cadência: 3 posts por semana (1 vídeo, 1 carrossel/imagem, 1 texto) e respostas diárias.

### Métricas a acompanhar
| Etapa | Métrica | Fonte |
|---|---|---|
| Alcance | impressões, visitas, origem do tráfego | Analytics, Search Console |
| Interesse | cliques no CTA, vídeo assistido até 50% | Analytics, redes |
| Cadastro | cadastros por visitante; custo por cadastro se houver anúncio | evento `cadastro` |
| Ativação | % que emite a 1ª nota (ou cadastra 1º cliente) em 48 h | evento `ativacao` |
| Retenção do teste | % ativo no dia 7 e no dia 14 | evento de uso |
| Receita | teste → pago, plano escolhido, churn | evento `assinatura`, gateway |
| Offline | uso do modo offline, notas pendentes que viram autorizadas, rejeições na reconexão | telemetria da Frente G |
| Qualidade | NPS do piloto, tickets por usuário | pesquisa curta |

Metas numéricas ficam abertas até haver linha de base de 2 semanas; não usar benchmarks inventados.

## 6. Regras de honestidade e compliance
- Não prometer emissão fiscal, offline, integração governamental ou WhatsApp que o produto ainda não realiza (ver 1.1 e 4.4).
- Offline: nunca dizer que a nota é "emitida" ou "autorizada" sem rede; usar "pendente de transmissão".
- Preços e planos só em peça pública depois de aprovados pelo dono.
- Sem depoimentos, números de clientes ou selos fictícios.
- LGPD: consentimento de cookies/analytics; lista de contatos só com base legal; descadastro em todo e-mail.
- Uso de mídia gerada por IA identificado quando exigido pela plataforma; sem imitar pessoa real.
- Direitos: fontes, imagens e músicas com licença livre ou geradas por ferramenta contratada.

## 7. Pendências e decisões do dono
- Escolher a direção de logo (A, B ou C) e aprovar a unificação de identidade.
- Aprovar orçamento de crédito para Higgsfield/ElevenLabs/HyperFrames antes de gerar qualquer mídia.
- Fornecer CNPJ, contatos e redes sociais oficiais para rodapés e folder.
- Aprovar (ou ajustar) os 3 planos e preços da Frente D (PR #66).
- Confirmar que o teste de 14 dias é sem cartão no fluxo real de cadastro.
- Definir quem publica e responde nas redes durante os 30 dias.

---
*Rascunho 2 · Frente F · falta fechar paleta/tipografia com a Frente C.*
