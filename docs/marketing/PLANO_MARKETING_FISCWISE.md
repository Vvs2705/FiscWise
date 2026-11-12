# Plano de Marketing e Identidade — FiscWise

> **Status: rascunho 1 (esqueleto).** Seções marcadas com 🔒 aguardam insumos das Frentes D (posicionamento e preços) e C (tokens de design). Nada aqui foi gerado com crédito pago nem publicado.

## Índice
1. Posicionamento, público e mensagens-chave 🔒 (Frente D)
2. Logo: diagnóstico e 3 direções de evolução
3. Vídeos em IA: 5 roteiros 🔒 (Frente D)
4. Folders e banners: formatos, textos e direção visual
5. Calendário de lançamento de 30 dias e métricas
6. Regras de honestidade e compliance
7. Pendências e decisões do dono

---

## 1. Posicionamento, público e mensagens-chave 🔒

*A preencher com a saída da Frente D (público principal, dor principal, frase de proposta de valor, planos e preços).*

Insumos já disponíveis no repositório (README e tela de login atual):
- **Público declarado:** contadores autônomos, pequenos e médios escritórios, BPO contábil/financeiro.
- **Promessa atual do login:** clientes, obrigações e documentos no mesmo ambiente; rotina previsível (saber o que vence hoje); dados protegidos em ambiente exclusivo.

Estrutura a entregar nesta seção: público principal e secundário · dor principal · frase de proposta de valor (≤ 12 palavras) · 3 pilares de mensagem · 3 provas (segurança/LGPD, rotina previsível, carteira em um só lugar) · tom de voz (direto, profissional, sem jargão de IA) · palavras a evitar.

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

**Direção B — "Calendário/Prazo" (comunica a rotina fiscal)**
- Conceito: a promessa real do produto é "saber o que vence hoje". Símbolo = uma folha de calendário/guia estilizada cujo canto dobrado forma a letra F.
- Cores: azul-petróleo escuro como base, laranja como destaque único (o "dia de hoje").
- Tipografia: wordmark em duas palavras de pesos diferentes (**Fisc**Wise: Fisc 700, Wise 400) para explorar o nome.
- Prompt (placeholder): *"Flat vector logo mark, stylized calendar page with folded top-right corner forming the letter F, deep teal-navy shape with one small orange square highlighting a single day, geometric, minimal, solid colors, no gradient, works in one color, square canvas, white background"*

**Direção C — "Selo Wise" (confiança e segurança)**
- Conceito: selo/escudo de contorno limpo com uma barra ascendente única dentro (crescimento seguro). Transmite LGPD/segurança sem usar cadeado clichê.
- Cores: azul-petróleo + laranja, com versão negativa pensada para fundo escuro (sidebar/login).
- Tipografia: wordmark em caixa-alta espaçada para uso institucional (folder, rodapé de proposta).
- Prompt (placeholder): *"Minimal emblem logo, rounded shield outline with a single ascending bar and a small dot inside, line weight consistent, navy and orange, flat vector, no gradient, monochrome-friendly, symmetrical, white background, app icon safe area"*

**Recomendação provisória:** Direção A para o menor risco e a menor quebra visual com a interface atual; Direção B se a Frente D definir "rotina previsível/prazos" como pilar central. Decisão final: dono.

### 2.3 Kit mínimo de entrega da logo (checklist para quando houver a arte final)
- [ ] Ícone e logo completa em SVG com **texto convertido em curvas**
- [ ] Versões: colorida, negativa (fundo escuro), monocromática preta e branca
- [ ] Favicon 16/32/48 + PNG 180 (apple-touch), 192 e 512 (PWA) + maskable
- [ ] Imagem Open Graph 1200×630
- [ ] Área de respiro (1× altura do "F") e tamanho mínimo (ícone 16 px, logo completa 96 px de largura)
- [ ] Remover tagline fixa dos SVGs ou unificá-la com o posicionamento da Frente D
- [ ] Atualizar `Logo.tsx`, `public/*.svg`, `index.html` e `theme-color` juntos (um único PR de identidade)

## 3. Vídeos em IA — 5 roteiros 🔒

*Os roteiros dependem da frase de proposta de valor e do público da Frente D.* A estrutura de cada roteiro, para não perder tempo depois:

| Campo | Conteúdo |
|---|---|
| Duração e formato | 15–60 s · vertical 9:16 (Reels/Stories/TikTok) ou 16:9 (site/YouTube) |
| Gancho (0–3 s) | frase/imagem que prende |
| Cenas | numeradas, com enquadramento e texto em tela |
| Locução PT-BR | texto com marcação de pausa e ritmo |
| Prompt por ferramenta | **Higgsfield** (vídeo/imagem gerada) · **ElevenLabs** (voz da locução) · **HyperFrames** (telas do produto e tipografia animada em HTML) |
| CTA final | teste grátis / link |

**Temas candidatos (confirmar com a Frente D):**
1. *"O que vence hoje?"* — a rotina do contador sem planilha paralela (15–20 s)
2. *Antes × depois* da carteira de clientes (30 s)
3. *Fechamento mensal + dossiê em PDF* (30–45 s, demonstração em tela)
4. *Portal do cliente* — o cliente envia documentos sem WhatsApp perdido (30 s)
5. *Segurança e LGPD em 20 segundos* (20 s, institucional)

**Divisão de ferramentas recomendada:** demonstrações de tela → HyperFrames (custo baixo e fidelidade ao produto real); cenas humanas/ambiente → Higgsfield; locução → ElevenLabs. **Regra:** nenhum prompt é executado enquanto não houver aprovação de orçamento pelo dono; Higgsfield e ElevenLabs consomem crédito.

## 4. Folders e banners

### 4.1 Formatos

| Peça | Medida | Uso | Observação |
|---|---|---|---|
| Feed quadrado | 1080×1080 | Instagram/LinkedIn | texto ≤ 20% da área, headline curta |
| Feed retrato | 1080×1350 | Instagram | melhor alcance orgânico |
| Stories/Reels capa | 1080×1920 | Instagram/WhatsApp Status | manter 250 px livres no topo e na base (interface das redes) |
| Banner de site (hero) | 1920×600 (desktop) + 750×900 (mobile) | página inicial/landing | WebP/AVIF, ≤ 150 KB |
| Open Graph | 1200×630 | prévia no WhatsApp/LinkedIn | logo + frase de valor, sem letras miúdas |
| Capa LinkedIn | 1584×396 | página da empresa | |
| Anúncio horizontal | 1200×628 | Meta/LinkedIn Ads | só publicar com aprovação e orçamento do dono |
| Folder A4 | 210×297 mm, 3 mm de sangria, 300 dpi, CMYK para gráfica / RGB para PDF digital | e-mail, WhatsApp, evento | 2 dobras (3 painéis) ou frente e verso |
| Assinatura de e-mail | 600 px de largura | equipe | |

### 4.2 Estrutura de texto (modelo, a fechar com a Frente D)
- **Headline:** a proposta de valor, até 8 palavras.
- **Subtítulo:** para quem é e o benefício principal, até 20 palavras.
- **3 benefícios:** verbo no início, sem jargão, sem número que o produto não prove.
- **Prova:** segurança/LGPD e "teste grátis sem cartão" **somente se for verdade** no checkout vigente.
- **CTA:** "Teste grátis" + URL curta.
- **Rodapé legal:** CNPJ e contato quando o dono fornecer.

### 4.3 Direção visual 🔒
Alinhada ao `DESIGN.md` (Frente C): tokens de cor, no máximo 2 famílias tipográficas, grid de espaçamento em escala, sombras discretas. Hoje, na interface, a fonte de display é Syne e a de corpo é Geist, com primária laranja sobre fundos azul-petróleo escuros; **confirmar com a Frente C** se permanecem. Regras provisórias: fundo claro ou petróleo escuro, um único destaque laranja por peça, capturas de tela reais do produto em moldura limpa (sem mockups de dados falsos apresentados como reais), fotografia só se for gerada/licenciada sem custo ou fornecida pelo dono.

### 4.4 Cuidado com o que a peça promete
O README do produto marca vários módulos como parciais ou em roadmap (NFS-e com provider de simulação, e-CAC/SERPRO, WhatsApp oficial, certificado como cofre). **Nenhuma peça pode anunciar esses itens como funcionando.** Usar somente o que está ✅ operacional: carteira de clientes, documentos, financeiro, obrigações fiscais, fechamento mensal com dossiê PDF, portal do cliente, IA operacional (calculadora/assistente).

## 5. Calendário de lançamento de 30 dias 🔒 (esqueleto)

Premissas: sem anúncio pago sem aprovação; foco em canais orgânicos e comunidade de contadores; clientes ainda inexistentes, então prova social começa do zero (usar demonstração e transparência, nunca depoimentos inventados).

| Semana | Objetivo | Entregas | Responsável |
|---|---|---|---|
| **Pré (D-7 a D-1)** | Preparar a base | Identidade unificada (logo/ícones/OG), landing e página de preços no ar (Frente E), analytics + eventos com consentimento LGPD, lista de espera/WhatsApp de contato | Dono + Frentes C/E |
| **Semana 1 (D1–D7)** | Anunciar | Post de lançamento, vídeo 1 ("O que vence hoje?"), carta pessoal do fundador a contatos contadores, página de FAQ | Dono (publicação) |
| **Semana 2 (D8–D14)** | Demonstrar | Vídeo 3 (fechamento + dossiê), carrossel "5 erros de controle com planilha", live curta/demonstração gravada | Dono |
| **Semana 3 (D15–D21)** | Provar | Vídeo 4 (portal do cliente), conteúdo de segurança/LGPD (vídeo 5), 5 a 10 contadores convidados para o piloto, coleta de feedback | Dono |
| **Semana 4 (D22–D30)** | Converter | Estudo de caso do piloto **com autorização por escrito**, oferta de teste estendido, e-mail de nutrição, revisão das métricas e decisão sobre anúncio pago | Dono + orquestrador |

Cadência sugerida: 3 posts por semana (1 vídeo, 1 carrossel/imagem, 1 texto), mais respostas diárias a comentários e mensagens.

### Métricas a acompanhar
| Etapa | Métrica | Fonte |
|---|---|---|
| Alcance | impressões, visitas ao site, origem do tráfego | Analytics, Search Console |
| Interesse | taxa de clique em CTA, visualização de vídeo até 50% | Analytics, redes |
| Cadastro | cadastros/visitante (meta inicial a definir após 2 semanas de base) | evento `cadastro` |
| Ativação | % que cadastra 1º cliente e sobe 1 documento em 48 h | evento `ativacao` |
| Receita | assinaturas, conversão do teste em pago, churn | evento `assinatura`, gateway |
| Qualidade | NPS do piloto, tickets de suporte por usuário | pesquisa curta |

Metas numéricas ficam em aberto até a Frente D fornecer preços e até haver linha de base real; **não inventar benchmarks**.

## 6. Regras de honestidade e compliance
- Não prometer integração governamental, emissão fiscal ou envio de WhatsApp que o produto ainda não realiza (ver 4.4).
- Sem depoimentos, números de clientes ou selos fictícios.
- LGPD: consentimento de cookies/analytics; lista de contatos só com base legal; descadastro em todo e-mail.
- Uso de mídia gerada por IA identificado quando exigido pela plataforma; sem imitar pessoa real.
- Direitos: fontes, imagens e músicas com licença livre ou geradas por ferramenta contratada.

## 7. Pendências e decisões do dono
- Escolher a direção de logo (A, B ou C) e aprovar a unificação de identidade.
- Aprovar orçamento de crédito para Higgsfield/ElevenLabs/HyperFrames antes de gerar qualquer mídia.
- Fornecer CNPJ, contatos e redes sociais oficiais para rodapés e folder.
- Confirmar se o "teste grátis" exige cartão (afeta o texto de todas as peças).
- Definir quem publica e responde nas redes durante os 30 dias.

---
*Rascunho 1 · Frente F · revisar após insumos das Frentes D e C.*
