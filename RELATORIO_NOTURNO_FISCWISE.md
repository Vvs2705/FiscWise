# Relatório da missão noturna — FiscWise

Missão: `MISSAO_FISCWISE_NOTURNA.md`, executada de 11/11/2026 à noite até 12/11/2026 às 10:46 UTC.
Estado da `main` ao fechar este relatório: commit `818392e` (merge do offline-first, PR #70).

## 1. Resumo executivo

- As 7 frentes (A a G) terminaram, e uma frente extra corrigiu uma falha de segurança no PDF (fpdf2).
- Foram abertos 27 PRs (#66 a #92). 25 estão na `main`, um foi fechado por ter sido substituído (#90) e um foi fechado porque o commit entrou direto (#69).
- O dono autorizou o merge de tudo durante a noite, inclusive dos itens que a regra 2 mandava segurar (migrations, login, fila fiscal, sync offline). Por isso a fila de aprovação ficou vazia. Os riscos desses itens estão na seção 3, para o dono acompanhar o deploy.
- Testes do backend: de 365 para 617. Testes do frontend: de 14 para 99. CI todo verde no último merge, incluindo Postgres real, RLS e E2E.
- Login: LCP em celular fraco com Slow 4G caiu de 8,9 s para 6,1 s (−31%). A meta do Google é 2,5 s, então ainda falta.
- O banco não é o gargalo (0,34 ms por consulta). O ganho veio de cortar idas ao banco: autenticação de 5 para 2 consultas e dashboard de 13 para 5.
- Guias e e-CAC davam erro 500 em produção por colunas faltando no banco. A migration do #76 corrige, e entra no próximo deploy.
- Novo: o FiscWise funciona offline no navegador e no celular (PWA), com sincronização incremental. Emissão offline fica "Pendente de transmissão", nunca "Autorizada".
- O que depende do dono está na seção 4: e-mail (Resend), bucket privado, CNPJ nos termos, Search Console/GA4, conferir o login com Google e aprovar os preços.

## 2. Por frente

### Frente A — Diagnóstico e performance ✅ concluída

Entregue:
- **A0 Diagnóstico** em `docs/audit/DIAGNOSTICO_A0_PERFORMANCE.md` (PR #85). Stack real: Cloud Run e Supabase em São Paulo, front no Cloudflare Pages. Banco de 14 MB, média de 0,34 ms por consulta da aplicação.
- **A1 Banco** (#73 e #76): autenticação em 1 consulta (5 → 2 idas ao banco), dashboard agregado (13 → 5 e 9 → 4 consultas), paginação com teto nas listagens, 8 colunas faltantes criadas, 14 índices nas FKs e 4 índices duplicados removidos.
- **A2 Integrações** (#71 e #77): retry com backoff e erro 503 claro nas integrações externas, cache em memória de planos e regras de obrigações, SERPRO em paralelo (4 por vez) e fila de trabalho em Postgres (`background_jobs`, sem Redis e sem worker fixo).
- **A3 Monitoramento** (#75 e #86): log JSON com duração por requisição, Web Vitals, Playwright com perfis mobile e Slow 4G, e o workflow `perf-probe` no GitHub Actions.

Métricas:

| Medida | Antes | Depois |
|---|---|---|
| Idas ao banco por requisição autenticada | 5 | 2 |
| Consultas do `/dashboard/overview` | 13 | 5 |
| p95 de `/live` medido dos EUA (perf-probe) | — | 159 ms (≈140 ms são a viagem EUA → SP) |
| LCP `/login`, Moto G4, Slow 4G, CPU 4x | 8,9 s | 6,1 s |
| LCP `/register`, mesmo perfil | 9,1 s | 6,9 s |

PRs: #71, #73, #75, #76, #77, #85, #86, todos mesclados.

Ficou pendente:
- Medir o cold start real e uma rota autenticada com banco em produção (rodar o `perf-probe` depois de 15 min sem tráfego).
- Levar o LCP de 6,1 s até 2,5 s: dividir o CSS (72 KB num arquivo só) e tirar `vendor-react` e `vendor-form` do caminho crítico.
- Sentry está no código, mas `SENTRY_DSN` está vazio em produção, então nenhum erro é capturado (seção 4).

### Frente B — Funções quebradas ✅ concluída

Entregue:
- **B1 Inventário** de rotas, botões, telas e endpoints quebrados, em `docs/audit/INVENTARIO_B1_FUNCOES.md`.
- Nove correções, um PR por tarefa, integradas numa linha única revisada (#91):
  - B-01 (#78): rotas que o front chamava e não existiam, Procurações e obrigações.
  - B-02 (#79): notificações ao cliente que agora saem de fato por e-mail.
  - B-03 (#80): portal do cliente com link de acesso por e-mail.
  - B-04 (#88): integrações fiscais simuladas não gravam mais dados falsos em produção.
  - B-05 (#81): calculadora com PDF real; a IA sem chave não consome cota.
  - B-06 (#89): botões sem efeito, dados fixos e preço lido do banco.
  - B-07 (#82): "Esqueci minha senha" e guardas do 2FA por e-mail.
  - B-08 (#83): chaves de API que autenticam e webhooks verificáveis.
  - B-09 (#84): documentos com URL assinada (LGPD), parser de NF-e, CSV e OFX.
- Falha de segurança real corrigida antes do merge: o leitor de XML de NF-e aceitava arquivo malicioso (XXE). Agora usa `defusedxml`.

Métricas: testes do backend de 365 para 558, testes do frontend de 14 para 74.

PRs: #78 a #84, #88, #89 e #91, todos mesclados.

Ficou pendente:
- Integrações pagas (SERPRO, certificado A1 para NFS-e, provedor de WhatsApp). As telas avisam que a integração não está disponível, em vez de mostrar dados falsos.
- Configurações do dono: e-mail, bucket e CNPJ (seção 4).
- O commit `1bcee9d` versionou 67 arquivos `.whl` soltos em `backend/`. Parecem sobra de instalação offline do container. Vale removê-los num PR de limpeza depois de confirmar que nenhum workflow os usa.

### Frente C — Repaginação visual e login ✅ concluída

Entregue:
- **Auditoria visual** em `docs/audit/AUDITORIA_VISUAL.md`.
- **Sistema de design** (#72): laranja `#e05e18` e azul-marinho `#1A2540`; só Geist e JetBrains Mono, hospedadas no próprio site; raios 6/8/12; três sombras sutis; movimento de até 250 ms e respeito a `prefers-reduced-motion`. O chunk de entrada caiu de 45 KB para 8 KB gzip.
- **Login novo** (#74 dentro do #87), já em produção: formulário à esquerda, "Criar conta" no topo, "Como funciona" em três passos à direita, "Esqueci minha senha", reenvio do 2FA e sem as métricas inventadas nem o radar. A primeira versão foi refeita porque mantinha o layout antigo.
- **Varredura das páginas internas** (#92): sem blur, vidro, gradientes, brilhos e caixa alta espaçada. As listagens com erro ganharam "Tentar novamente".

PRs: #72, #74, #87 e #92 mesclados. O #90 (correção de emergência) foi fechado porque o login novo o substituiu.

Ficou pendente:
- O `DESIGN.md` da raiz está no `.gitignore` por regra do dono (briefs locais não são versionados). A cópia versionada, que é a fonte da verdade, fica em `docs/audit/SISTEMA_DE_DESIGN.md`.
- O botão "Entrar com Google" do `/login` não foi conferido em produção, porque o container não abre o site. O dono precisa testar (seção 4).

### Frente D — Concorrentes e preços ✅ concluída

Entregue: `docs/marketing/PESQUISA_CONCORRENTES_PRECOS.md`, com fontes e links de Focus NFe, Simplifique, NFE.io, Conta Azul, Omie, Bling, Tiny e Nibo.

Planos propostos (não publicados):

| Plano | Mensal | Anual | Para quem | Limites |
|---|---|---|---|---|
| Essencial | R$ 79 | R$ 790 | MEI e microempresa | 1 CNPJ, 1 usuário, 100 notas/mês |
| Profissional | R$ 149 | R$ 1.490 | Pequena empresa | 3 CNPJs, 5 usuários, 500 notas/mês |
| Escritório | R$ 349 | R$ 3.490 | Escritório contábil | 30 CNPJs, usuários ilimitados, 3.000 notas/mês |

Posicionamento: "Emita notas fiscais sem complicação, mesmo sem internet". A faixa vazia do mercado fica entre R$ 70 e R$ 150, com notas generosas e acesso para o contador.

PR: #66, mesclado.

Ficou pendente: conferir à mão os preços atuais de Bling, Tiny/Olist, Nibo e eNotas (os sites bloquearam a leitura) e aprovar os planos (seção 4).

### Frente E — SEO e GEO ✅ concluída

Entregue (#68): `robots.txt` bloqueando as rotas do app, `sitemap.xml` só com páginas públicas, `llms.txt`, página `/faq/` com 10 respostas e `FAQPage`, title, description e canonical por página, `noindex` na área logada, 404 personalizada, Open Graph com `og-image.png`, Schema.org e CSP em modo Report-Only. Os crawlers de IA ficam liberados nas páginas públicas, e a decisão está documentada. O plano de palavras-chave, as landing pages por campanha e os eventos de Analytics estão em `docs/marketing/SEO_GEO_FISCWISE.md`.

PR: #68, mesclado.

Ficou pendente: Search Console, ID do GA4, redirecionar `fiscwise.com.br` para `www`, ativar a CSP e pré-renderizar `/precos` quando os preços forem aprovados (seção 4).

### Frente F — Plano de marketing ✅ concluída

Entregue (#67): `docs/marketing/PLANO_MARKETING_FISCWISE.md` com diagnóstico da logo, 3 direções com prompts prontos, 5 roteiros de vídeo (15 a 60 s) com prompts para Higgsfield, ElevenLabs e HyperFrames, textos e formatos de folder e banner, e calendário de 30 dias com métricas. Nada foi gerado com crédito pago nem publicado.

PR: #67, mesclado.

Ficou pendente: duas decisões do dono (seção 7 do plano). A primeira é confirmar se o público principal passa a ser MEI e pequena empresa, porque o README ainda fala em contador. A segunda é aprovar os preços. O calendário só deve começar quando emissão real, modo offline e acesso do contador estiverem em produção.

### Frente G — Offline com sincronização ✅ concluída (fase 1)

Entregue (#70):
- Arquitetura em `docs/arquitetura/OFFLINE_SYNC.md`. O motor é próprio: outbox no cliente e `/api/v1/sync/push`, `/sync/pull` e `/sync/devices` no FastAPI. PowerSync, ElectricSQL, RxDB e Replicache foram rejeitados por custo ou dependência de terceiros.
- PWA com service worker, IndexedDB (Dexie), indicador Online / Offline / Sincronizando / Erro, tela `/sincronizacao` e botão "Sincronizar agora".
- Pull por delta `(updated_at, id)`. Conflitos: última gravação vence por campo nos cadastros, com histórico em `sync_conflicts`; nas NFS-e, o servidor é a autoridade.
- Token de dispositivo separado do login (30 dias). Revogar o dispositivo apaga o banco local.
- Regra fiscal: offline a nota fica "Pendente de transmissão". A emissão offline passa pelo mesmo bloqueio do site, então sem emissor real configurado a nota continua rascunho. A NFS-e nacional não tem contingência; a contingência de NFC-e e NF-e (Ajuste SINIEF 19/2016 e EPEC) está documentada, mas não se aplica hoje.
- Portão de Segurança em `docs/audit/SECURITY-REVIEW-2026-11-12-offline-sync.md`.

Métricas: testes do backend em 617 e do frontend em 99, CI verde com Postgres e E2E. A cabeça do Alembic ficou em `o1i7bc49gk6`, com uma cabeça só.

PR: #70, mesclado.

Ficou pendente:
- **CSP ativa no `_headers`.** É o achado médio da revisão de segurança: o token de dispositivo vale 30 dias e fica no IndexedDB, então um XSS daria acesso longo ao `/sync/pull`.
- **Teto de 180 dias** na renovação do token de dispositivo. Hoje a janela é deslizante e não tem limite.
- **Limpar o cache do service worker na resposta 401**, além do logout e da revogação.
- **Cifrar os campos sensíveis do IndexedDB** (documento, e-mail e telefone) com WebCrypto, aceitando perder a busca local por esses campos.
- **Desktop Tauri (fase 2):** precisa de runner `windows-latest` no GitHub Actions (grátis em repositório público; em privado gasta os 2.000 min/mês do plano Free) e de certificado de assinatura de código (pago, cerca de US$ 200 a 400 por ano). Sem certificado, sai como pré-lançamento com o aviso de "editor desconhecido".
- Endpoint para listar e resolver `sync_conflicts` no servidor, webhook `client.created` para clientes criados pelo sync, RPS para municípios ABRASF e E2E offline com backend de preview.

### Frente extra — Falha de segurança no PDF ✅ arquivada

O `fpdf2` subiu de 2.8.3 para 2.8.8 (CVE-2026-114609 e CVE-2026-114610), com o commit `88b06ca` direto na `main`. O `pip-audit` ficou limpo e 366 testes passaram, incluindo os de PDF. O PR #69 foi fechado porque o commit entrou direto.

## 3. Fila de aprovação

**Vazia.** Às 05:31 UTC o dono autorizou o merge de todos os PRs, inclusive os que a regra 2 mandava segurar. Ficam abaixo os itens sensíveis que já estão na `main`, para acompanhar no próximo deploy:

| PR | O que toca | Risco | O que observar |
|---|---|---|---|
| #76 | migration (colunas e índices) | baixo: só acrescenta | Guias e e-CAC param de dar 500 depois do deploy |
| #77 | migration e fluxo fiscal (fila `background_jobs`) | médio | jobs presos em `GET /jobs`; o tick horário precisa estar rodando |
| #73 | autenticação | médio | logins e permissões por escritório logo depois do deploy |
| #80, #82, #83 | login (portal, senha, 2FA, chaves de API) | médio | só funcionam por completo com o e-mail configurado |
| #89 | preço lido do banco | baixo | a tabela `plans` precisa ter os valores certos |
| #87 | tela de login | baixo | conferir o botão do Google |
| #70 | migration `o1i7bc49gk6` e endpoints de sync | médio | `alembic upgrade head` no deploy e a revogação de dispositivo |

Ainda aberto, de antes da missão: o PR #64 (`docs(audit)`: estado após as levas 5 e 6), que precisa de revisão ou fechamento.

## 4. Pendências que dependem do dono

**Configurações**
1. **E-mail:** definir `RESEND_ENABLED=true` e `RESEND_API_KEY` no Cloud Run. Sem isso, o link do portal do cliente, o "Esqueci minha senha" e as notificações ficam em modo manual ou escondidos. O Resend tem plano grátis.
2. **Documentos privados:** deixar privado o bucket `documents` no Supabase. O código já usa URLs assinadas.
3. **Termos de uso:** informar o CNPJ da empresa em `VITE_COMPANY_CNPJ` no Cloudflare Pages.
4. **Login com Google:** abrir www.fiscwise.com.br/login e testar o botão "Entrar com Google". Ninguém conseguiu conferir esse botão daqui.
5. **Erros em produção:** criar o projeto grátis no Sentry e definir `SENTRY_DSN` e `VITE_SENTRY_DSN`.
6. **Web Analytics:** criar o token do Cloudflare Web Analytics no painel (grátis).
7. **SEO:** verificar a propriedade no Search Console, informar o ID do GA4 e redirecionar `fiscwise.com.br` para `www` no Cloudflare.
8. **CSP:** depois de conferir o console em produção, trocar a CSP de Report-Only para ativa. Isso também fecha o achado médio da Frente G.

**Decisões de negócio**
9. Aprovar ou ajustar os três planos (R$ 79, R$ 149 e R$ 349). Só depois disso `/precos` é publicada e pré-renderizada.
10. Confirmar se o público principal é MEI e pequena empresa ou escritório contábil.
11. Conferir à mão os preços de Bling, Tiny/Olist, Nibo e eNotas.

**Custos (nada foi contratado)**

| Item | Custo estimado | Alternativa até lá |
|---|---|---|
| SERPRO (consultas oficiais) | pago por consulta | tela avisa que a integração não está disponível |
| Certificado A1 para emitir NFS-e | ~R$ 150–250/ano | emissão fica em rascunho e o provedor mock é bloqueado em produção |
| Provedor de WhatsApp | pago por mensagem | envio desligado com aviso |
| Certificado de assinatura do instalador Windows | ~US$ 200–400/ano | pré-lançamento sem assinatura |
| Lojas de apps (Apple US$ 99/ano, Google US$ 25) | taxa | o PWA instalável cobre o celular |

## 5. Modelos usados

As threads não registraram o modelo de cada uma. O que está confirmado:

| Frente | Modelo e esforço |
|---|---|
| Coordenação e este relatório | Opus 5.5, esforço alto |
| C (login refeito e varredura visual) | subagentes Opus 5.5 |
| Demais frentes | modelo padrão da sessão (Opus 5.5); não há registro de troca para Fable 5.2, Sonnet 5.5 ou Haiku 5.5 como a tabela da missão sugeria |

Consumo: não há contagem exata de tokens. O limite de uso do plano foi atingido por volta de 05:41 UTC e liberou cerca de 4 horas depois. As frentes A, B e C retomaram às 10:00 UTC e terminaram os merges até 10:46 UTC. Para a próxima missão, vale distribuir de verdade o Sonnet e o Haiku nas tarefas de volume, como a tabela da missão sugere, para não bater no limite no meio da noite.
