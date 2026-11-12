# Inventário B1 — funções quebradas, simuladas, sem efeito ou "em breve" (12/11/2026)

Frente B da missão noturna. Varredura estática de **todas** as rotas do frontend (`frontend/src/App.tsx`), das 185 rotas do backend (`backend/app/api/v1`) e de cada botão/ação das telas, cruzando chamada do frontend × rota do backend. Baseline em `main` `485093f`: backend `pytest` 365 passed / 1 skipped; frontend `type-check`, `lint` (1 warning) e `vitest` (14) verdes.

Legenda: **QUEBRADO** (erro 404/405/500 ou dado inválido) · **MOCK** (dado simulado apresentado como real) · **NO-OP** (botão sem efeito ou "em breve") · **GATED** (depende de credencial/env) · **SEM-UI** (rota existe, nenhuma tela usa) · **OK**.

> Já tratado pela Frente A (não duplicar): telas **Guias** e **Central e-CAC** dão 500 em produção por colunas `updated_at`/`created_at` ausentes em `tax_guides`, `ecac_proxies` e `ecac_fiscal_situations` (migration corretiva na branch `claude/project-thread-353yrz`).

## 1. Resumo executivo

| # | Achado | Impacto | Correção mais barata |
|---|---|---|---|
| 1 | **Monitor Fiscal inventa** débitos, CND, NF-e e **cria prazos reais** para dívidas fictícias (`services/fiscal_monitor_service.py:76-238`), sem flag; roda em produção | Alto: contador recebe tarefas falsas e links quebrados (`fiscwise.storage`) | Situação cadastral via BrasilAPI (grátis); débitos/CND/NF-e viram "não consultado"; flag de provider |
| 2 | **Caixa Postal** e **situação e-CAC** gravam dados falsos por padrão (`FISCAL_MAILBOX_PROVIDER=mock`, `ecac.py:27`), sem aviso na Caixa Postal; intimações falsas aparecem no Foco do dia | Alto | Em `production` com provider mock: responder "não configurado" (503) em vez de gravar |
| 3 | **NFS-e**: emissão/cancelamento 100 % mock (`invoices.py:33,117`); PDF/XML dão 500/404 porque nada é enviado ao storage (`domain/invoices/service.py:170`) | Alto | Servir `xml_content` direto; bloquear emissão em produção enquanto provider for mock; integração real = NFS-e Nacional (mTLS + A1) |
| 4 | **Nenhuma notificação sai**: `notification_engine` usa env `EMAIL_PROVIDER` inexistente e SDK `resend` não instalado; lembretes de cobrança só gravam auditoria; aviso de certificado grava "pending" sem worker; "Enviar por E-mail" no cockpit é `setTimeout` com toast "enviado" | Alto | Trocar por `email_service.send_email` (já funciona com Resend); endpoint real para o lembrete do cockpit |
| 5 | **`POST /notifications/cert-expiry-warning` dá 500** no Postgres (`body` NOT NULL não preenchido, `notifications.py:248`) — tela Certificados chama | Alto | 1 linha + envio real |
| 6 | **Portal do cliente inalcançável**: convite e magic-link não enviam e-mail nem têm UI; `/portal/invites/*` dá 500 no Postgres (`datetime.utcnow()` × coluna com fuso, `portal.py:125-259`); `/portal/login` sem token só mostra erro | Alto | Fuso + `send_email` + botão "Convidar para o portal" + formulário de pedir link (**auth → fila de aprovação**) |
| 7 | **Frontend chama rotas inexistentes**: `/powers-of-attorney*` (página Procurações inteira, link do Sidebar), `DELETE obligations/instances`, `DELETE deadlines`, `DELETE certificates`, `DELETE receivables`, `PATCH das` (backend é PUT) | Alto: 6 botões de excluir/página quebrados | Procurações → `/ecac/proxies`; criar DELETEs como *soft delete* (compatível com sync offline) |
| 8 | "Gerar automáticas" de obrigações roda para **todos os tenants** e o campo `custom_name` da obrigação avulsa é descartado (`obligations.py:78,475`) | Médio | Escopar por tenant; aceitar `custom_name` |
| 9 | **Export PDF da calculadora (Premium)** sai só com o título (`calculator.py:765`, `Td` relativo) | Médio | Reescrever com `fpdf2` (já instalado, padrão de `dossier_pdf.py`) |
| 10 | **API keys são fachada** (`verify_api_key` nunca usado) e **webhooks** assinam com `sha256(secret)` (cliente não consegue verificar), 2 eventos nunca disparam, sessão de banco compartilhada | Médio | Dependência `user_or_api_key`; assinar com segredo cru; sessão própria (**auth → fila**) |
| 11 | **Documentos em URL pública** do bucket (`operations.py:1157,1664`) — LGPD; parser ignora XML de NF-e; mídia do WhatsApp nunca é baixada | Médio | URL assinada (como Guias já fazem); parser XML stdlib |
| 12 | **Painel**: datas −1 dia em BRT (`DashboardPage.tsx:21-25`), nomes dos dias fixos, itens clicáveis sem handler, "Ver todos os documentos" sem handler; Ctrl+K "Novo cliente/Subir documento" não abre modal | Médio | Correções locais no frontend |
| 13 | **Configurações**: preço Premium R$ 299 fixo (banco = 349), aba Pagamento cita Asaas (gateway é Mercado Pago), histórico de faturas sempre vazio, link `/docs` quebrado, e-mail de contato divergente | Médio | Ler `/subscription/plans`; limpar textos |
| 14 | **Fechamento Mensal** só oferece Mar–Mai/2026 no select (`MonthlyClosingsPage.tsx:17-21`) | Médio | Gerar competências dinamicamente |
| 15 | **Sem "Esqueci minha senha"** (template de e-mail existe, endpoint não) | Médio | Endpoints request/reset + tela (**auth → fila**) |
| 16 | NO-OPs: Exportar XLSX (Relatórios), "Emitir Guia" (cockpit), "Renovar" (Procurações), "Ver planos" (FeatureGate), "Notificar/adiar" no Modo Foco, ESC no Ctrl+K | Baixo | Implementar ou remover |
| 17 | `/api/v1/db-test` público expõe contagem de usuários e erro do banco; `/ready` devolve `str(e)` | Baixo/seg. | Gate por `DIAGNOSTICS_ENABLED`; sem `str(e)` |
| 18 | Chat IA consome cota mesmo sem `OPENAI_API_KEY`; `resend-2fa` responde `sent=true` sem enviar; 2FA por e-mail pode ser ativado sem Resend (tranca o usuário) | Baixo/médio | Guardas simples (**auth → fila**) |

### Pendências que dependem de serviço pago ou credencial (não dá para "consertar" à noite)
- **e-CAC / Caixa Postal / Situação fiscal real**: SERPRO Integra Contador (contrato pago + e-CNPJ + mTLS). O cliente SERPRO já existe (`domain/fiscal_mailbox/integrations/serpro.py`).
- **NFS-e real**: API NFS-e Nacional (gratuita) exige certificado A1 do emissor + mTLS; libs sugeridas `nfelib` (DPS), `erpbrasil.assinatura` (XML-DSig), `brazilfiscalreport` (DANFSe). Nenhuma está no `requirements.txt`.
- **WhatsApp real**: Evolution API self-hosted (grátis) ou Meta Cloud API; precisa número e adaptador de webhook.
- **Débitos/CND na Receita**: não existe API pública gratuita; manter como "indisponível".
- **E-mail transacional**: `RESEND_ENABLED=true` + `RESEND_API_KEY` em produção (Resend tem plano grátis de 3 000/mês). Sem isso, nada do item 4/6 chega ao cliente.
- **Pagamentos**: `PAGAMENTOS_GO_LIVE` + credenciais Mercado Pago.
- CNPJ da empresa nos Termos (`TermsPage.tsx:41`) está como `XX.XXX.XXX/0001-XX`.

## 2. Plano de correção (um PR por tarefa)

| PR | Escopo | Merge |
|---|---|---|
| B-01 | Rotas faltantes: `DELETE` soft de deadlines/certificates/receivables/obligations; `useUpdateDas`→PUT; Procurações usando `/ecac/proxies`; `custom_name`; generate por tenant | mesclável |
| B-02 | Notificações reais: `cert-expiry-warning` (500), `notification_engine` via `email_service`, lembrete de cobrança, endpoint de lembrete do cockpit | mesclável |
| B-03 | Portal do cliente: fuso, envio do magic-link/convite, botão "Convidar", formulário em `/portal/login` | **fila (auth)** |
| B-04 | Honestidade dos mocks fiscais: Monitor Fiscal com BrasilAPI e sem dados inventados; mailbox/e-CAC/NFS-e bloqueados em produção com provider mock; XML da nota servido do banco | **fila (fluxo fiscal)** |
| B-05 | Calculadora: export PDF com fpdf2; cota sem chave; UI (campos ignorados, `ai_recommendation`, Fator R no histórico, botão PDF só Premium) | mesclável |
| B-06 | Frontend: painel (datas, handlers), Ctrl+K, Fechamento (competências), Configurações (preços/Pagamento/docs), Relatórios XLSX real (openpyxl), Caixa Postal "lida", Documentos (conferir / IA), reativar cliente, gerar mensalidades, LGPD export/delete na UI | mesclável |
| B-07 | Esqueci minha senha + guardas de 2FA por e-mail + `resend-2fa` honesto | **fila (auth)** |
| B-08 | Developer: API key autenticando de verdade, HMAC correto, eventos, sessão | **fila (auth)** |
| B-09 | Documentos: URL assinada, parser XML NF-e, `POST /documents` dispara parsing, mídia WhatsApp baixada; `/db-test` e `/ready` | mesclável (portão de segurança) |

## 3. Inventário por tela (frontend)

### 3.1 Configurações (`pages/SettingsPage.tsx`)
| Ação | Local | Status | Detalhe |
|---|---|---|---|
| Perfil "Salvar alterações" | :268-278, :338 | OK | `PATCH /auth/me` |
| Escritório "Salvar" | :389-398, :459 | OK | `PATCH /auth/tenant` |
| Card "Plano atual" (nome e preço) | :130-153, :599 | MOCK | `PLANS` fixo: Premium "R$ 299/mês"; banco tem 349 (migração `j4d267c94bf1`) |
| Lista de recursos dos planos | :521-535, :709 | MOCK | `planMeta` fixo substitui limites do banco |
| "Continuar para o Mercado Pago" | `UpgradePlanoModal.tsx:233-247` | GATED | `PAGAMENTOS_GO_LIVE=false` → 503; não-owner 403 sem aviso |
| 2FA TOTP | :828-886 | OK | |
| 2FA por e-mail | :839-873 | GATED | `RESEND_ENABLED`; backend responde "Código enviado" sem enviar (`auth.py:596-603`) |
| Alterar senha | :1124, :1183 | OK | |
| Pagamento: "Assinatura Ativa" | :1278 | MOCK | Texto fixo mesmo em trial/atraso |
| Pagamento: "Gerenciar no Asaas" | :1308-1315 | NO-OP | Home do asaas.com; gateway é Mercado Pago |
| Pagamento: "Cobrança Direta (Asaas)…" | :1333 | MOCK | Contradiz o gateway |
| Pagamento: "Histórico de faturas" | :1363-1376 | MOCK | Sempre vazio, sem API |
| Pagamento: e-mail de contato | :1380 | QUEBRADO | Link `contato@`, texto `faturamento@` |
| Notificações "Disparar agora" | :1476-1483 | NO-OP | Backend "skipped" sem `EMAIL_PROVIDER` (env inexistente em Settings) |
| Base de Conhecimento CRUD | :1617-1876 | OK | Bloqueio Free só no frontend; depende de `OPENAI_API_KEY` |
| Desenvolvedor: chaves de API | :1939-2099 | MOCK | `verify_api_key` nunca é chamado |
| Desenvolvedor: webhooks | :1966-2226 | OK/parcial | HMAC inverificável; ver §4 |
| Aba Desenvolvedor visível | :165, :243 | MOCK | `feature_public_api:false` mas sem gate |
| Link "documentação da API" `/docs` | :2298 | QUEBRADO | Rota do frontend inexistente; `/docs` do backend desligado em produção |
| LGPD exportar/excluir conta | — | SEM-UI | `GET /account/export`, `POST /account/delete` existem |

### 3.2 Clientes (`pages/ClientsPage.tsx`) e detalhe (`features/clients/components/ClientDetailCockpit.tsx`)
| Ação | Local | Status | Detalhe |
|---|---|---|---|
| Novo cliente, CNPJ auto (BrasilAPI no browser) | :710, :99-103 | OK | |
| Importar XLSX | :222, :296 | MOCK | Só a 1ª linha preenche o formulário; não é lote |
| Reativar cliente desativado | — | NO-OP | Sem botão |
| Prazos: excluir | Cockpit :420-428, :1199 | QUEBRADO | `DELETE /deadlines/{id}` não existe (405) |
| Upload documento oficial | :370-392, :1095 | GATED | Supabase; URL pública do bucket |
| "Enviar por E-mail" | :666-677, :1425 | MOCK | `setTimeout` 1,2 s + toast "enviado"; nenhuma API |
| Monitor Fiscal "Sincronizar Agora" | :1477-1501 | MOCK | Backend inventa tudo e cria prazos reais |
| Monitor Fiscal "Baixar CND PDF" / XML NF-e | :1592-1609, :1765 | QUEBRADO | URLs `fiscwise.storage` inventadas / `'#'` |
| Monitor Fiscal "Emitir Guia" | :1646-1655 | NO-OP | Só toast |
| "Validade estimada: 180 dias" | :1588 | MOCK | Texto fixo |
| Sócios, honorários, DAS, notas internas | vários | OK | |
| `components/ClientManageDrawer.tsx` | :253 | morto | Não é renderizado |
| `SecureNotesDrawer` | :104-123 | LOCAL | Credenciais em `localStorage` em texto puro (aviso honesto na tela) |

### 3.3 Painel (`pages/DashboardPage.tsx`, `features/dashboard/components/*`)
| Ação | Local | Status | Detalhe |
|---|---|---|---|
| Cálculo de datas | :21-25 | QUEBRADO | `new Date('YYYY-MM-DD')` = UTC → −1 dia em BRT |
| Nomes dos dias | :161 | MOCK | 'Hoje','Amanhã','Quarta','Quinta','Sexta' fixos |
| Score de risco | :220-267 | MOCK | Heurística local (aceitável, mas rotulado como estimativa) |
| "Clientes em atenção" itens | `ClientAttentionList.tsx:83` | NO-OP | `cursor-pointer` sem `onClick` |
| Linha do tempo da semana | `FiscalWeekTimeline.tsx:115` | NO-OP | idem |
| "Ver todos os N documentos" | `PendingDocumentsCard.tsx:147` | NO-OP | `<button>` sem handler |
| Modo Foco: "Notificar Cliente", adiar certificado, "Aguardando cliente" | `ModoFocoModal.tsx:159-212` | NO-OP/MOCK | Só toasts; nada persiste nem envia |
| Modo Foco: índice após resolver | :134-140 | QUEBRADO (provável) | refetch remove item e o índice pula o próximo |
| Hero, Foco do dia, recomendações | | OK | |

### 3.4 Documentos, Certificados, Financeiro
| Ação | Local | Status | Detalhe |
|---|---|---|---|
| Documentos: coluna "IA" | `DocumentsPage.tsx:383-418` | MOCK | `POST /documents` não agenda parsing → "Aguardando processamento" para sempre |
| Documentos: conferir/aprovar | — | SEM-UI | `PATCH /documents` existe |
| Certificados: excluir | `CertificatesPage.tsx:359,432` | QUEBRADO | `DELETE /certificates/{id}` não existe |
| Certificados: "Avisar cliente" | :133-153 | QUEBRADO+MOCK | Backend 500 (body NOT NULL); toast "enviado" |
| Financeiro: excluir cobrança | `FinancePage.tsx:389,457` | QUEBRADO | `DELETE /receivables/{id}` não existe |
| Financeiro: gerar mensalidades | — | SEM-UI | `POST /receivables/generate-monthly` |

### 3.5 Login, Cadastro, Layout
| Ação | Local | Status | Detalhe |
|---|---|---|---|
| "Esqueci minha senha" | — | NO-OP | Não existe (nem backend) |
| Texto "Login por Google… permanecem ativos" | `LoginPage.tsx:336` | MOCK | Aparece com Google desligado |
| Google (`onError={() => {}}`) | `RegisterPage.tsx:301-310` | GATED | Erro engolido |
| Preços no cadastro ×  Configurações | `RegisterPage.tsx:30-54` | divergente | 349 × 299 |
| Sidebar "Procurações" | `components/Sidebar.tsx:66` | QUEBRADO | Leva à página que chama `/powers-of-attorney` |
| Ctrl+K "Cadastrar Novo Cliente"/"Subir Documento" | `CommandMenu.tsx:68,75` | NO-OP | Navega sem `state.openCreate` |
| Ctrl+K "ESC para fechar" | :132 | NO-OP | Sem handler |
| `FeatureGate` "Ver planos" | `FeatureGate.tsx:30` | NO-OP | Sem `onClick` |

### 3.6 Obrigações, Fechamento, Portal, WhatsApp, Relatórios, Aprender
| Ação | Local | Status | Detalhe |
|---|---|---|---|
| Obrigações: excluir | `ObrigacoesPage.tsx:187,913,989` | QUEBRADO | `DELETE /obligations/instances/{id}` não existe |
| Obrigações: "Gerar automáticas" | :627-636 | QUEBRADO | Engine roda para **todos** os tenants; toast soma global |
| Obrigações: avulsa `custom_name` | :337 | QUEBRADO | Campo descartado pelo schema → "Sem descrição" |
| Fechamento: select de competência | `MonthlyClosingsPage.tsx:17-21` | MOCK | Só Mar–Mai/2026 |
| Fechamento: "Gerar rotina" só com lista vazia | :144 | limitado | Clientes novos não entram |
| Portal (escritório): convidar / link mágico | — | SEM-UI | Backend não envia e-mail |
| Portal (cliente): login sem token | `PortalLoginPage.tsx:52-105` | QUEBRADO | Sem formulário; "Tentar novamente" reenvia token de uso único |
| WhatsApp: enviar | `WhatsAppInboxPage.tsx:444`, widget :206 | MOCK | `mock-msg-*`; widget mostra badge "Live" sem aviso |
| Relatórios: "Exportar XLSX" | `ReportsPage.tsx:173` | NO-OP | "em breve" |
| Aprender: "Configurar Perfil" | `LearningPage.tsx:38` | MOCK | `isProfileComplete = true` fixo |
| Caixa Postal: abrir detalhe | `FiscalMailboxPage.tsx:178` | parcial | Nunca chama `/read`; "Não lidas" nunca muda |
| Caixa Postal: sincronizar | :85 | MOCK | Grava intimações falsas sem aviso |
| Termos: CNPJ | `TermsPage.tsx:41` | MOCK | `XX.XXX.XXX/0001-XX` |

### 3.7 Calculadora, Procurações, Notas, e-CAC, Guias
| Ação | Local | Status | Detalhe |
|---|---|---|---|
| Simulador: Estado e crédito PIS/COFINS | `CalculatorSimulator.tsx:156,174` | MOCK | Não entram no payload; `activity_code` fixo |
| Simulador: recomendação IA | `fiscwise-calculator-api.ts:64-70` | QUEBRADO | Backend devolve, mapper descarta |
| Histórico: Fator R | api :96-113 | QUEBRADO | Aparece "N/A" / receita 0 |
| Histórico: "Exportar PDF" | `SimulationHistory.tsx:163` | GATED+QUEBRADO | Botão em todos os planos (403 → `alert`); PDF do backend só com título |
| Chat fiscal | `FiscalChat.tsx` | GATED | Plano + `OPENAI_API_KEY`; bloqueio Free sem botão de upgrade |
| Plano na calculadora | `Calculator.tsx:35-43` | risco | Usa `plan_slug` cru em vez do plano efetivo |
| Procurações: tudo | `PowersOfAttorneyPage.tsx`, `features/powers-of-attorney/api.ts` | QUEBRADO | 3 rotas inexistentes; "Renovar" em breve; aba equivalente em `/ecac` funciona |
| Notas: lista/emitir/cancelar | `features/invoices/**` | MOCK | Aviso presente; provider mock fixo |
| Notas: "Corrigir e Transmitir" | `InvoiceDetailPage.tsx:124` | NO-OP | Não há edição (sem PATCH) |
| Notas: PDF/XML | :132-136 | QUEBRADO | Arquivo nunca enviado ao storage |
| e-CAC: situação fiscal | `FiscalSituationPage`, card | MOCK | Aviso presente |
| e-CAC: procurações CRUD | `ProxiesListPage.tsx` | OK | `/ecac/proxies` |
| Guias: CRUD, pagar, uploads/downloads | `features/guias/**` | OK/GATED | Supabase; (500 em produção até a migration da Frente A) |

## 4. Inventário do backend

### 4.1 Endpoints com problema
| Rota | Arquivo:linha | Status | Detalhe |
|---|---|---|---|
| POST /notifications/cert-expiry-warning | notifications.py:229 | QUEBRADO | `body` NOT NULL ausente → 500; "pending" sem worker |
| GET/POST /portal/invites/{id}, /accept | portal.py:135,173 | QUEBRADO (PG) | `utcnow()` naive × `DateTime(timezone=True)` |
| POST /portal/invites, /magic-link/request | portal.py:65,529 | STUB+SEM-UI | Não envia e-mail (TODO :608) |
| POST /calculator/export-pdf | calculator.py:618-765 | QUEBRADO | PDF manual com `Td` relativo; só o título aparece |
| POST /fiscal-monitor/sync/{id} | fiscal_monitor_service.py:32-238 | MOCK perigoso | Dados inventados + prazos reais + URLs falsas, sem flag |
| POST /fiscal-monitor/nfes/import | fiscal_monitor.py:168 | STUB+SEM-UI | `access_key` checado sem filtro de tenant (:279) |
| POST /fiscal-mailbox/sync | factory.py:28 | MOCK por padrão | Intimações falsas em produção |
| POST /ecac/fiscal-situation/{id}/refresh | ecac.py:27,112 | MOCK fixo | `IntegraContadorProvider` = `NotImplementedError`; erro em `print` |
| POST /invoices/{id}/emit, /cancel | invoices.py:33,117 | MOCK fixo | `except Exception: pass` engole erro |
| GET /invoices/{id}/pdf, /xml | service.py:170,272 | QUEBRADO | Nada enviado ao storage; `xml_content` existe no banco |
| POST /whatsapp/inboxes/{id}/send | whatsapp_service.py:99 | MOCK | Loga corpo (PII); `status="sent"` |
| POST /whatsapp/webhooks/{tenant} | whatsapp.py:270 | GATED/parcial | Mídia nunca baixada (parser lê `/tmp/...` inexistente) |
| POST /notifications/trigger-pending-docs | notification_engine.py:52-79 | NO-OP | `EMAIL_PROVIDER` fora de Settings; SDK `resend` ausente |
| POST /auth/login/resend-2fa | auth.py:315 | engana | `sent=True` mesmo com falha |
| /auth 2FA por e-mail | auth.py:229,596 | GATED | Sem Resend tranca o usuário |
| POST /account/delete, GET /account/export | account.py | GATED/parcial | Só marca; export sem dados |
| POST /documents/upload, /clients/{id}/documents | operations.py:1157,1664 | risco LGPD | URL pública do bucket |
| /developer/webhooks | webhook_service.py:64,178,246 | QUEBRADO parcial | HMAC com `sha256(secret)`; eventos nunca emitidos; sessão compartilhada |
| /developer/api-keys | api_key_service.py:102 | FAKE | Nunca autentica |
| GET /db-test | health.py:85, middleware.py:20 | exposto | Público |
| GET /ready | health.py:43 | vaza | `str(e)` |
| POST /obligations/generate | obligations.py:475 | QUEBRADO | Sem `tenant_id` → todos os tenants |

### 4.2 Rotas sem UI
`POST /auth/logout`, `GET/POST /account/*`, `simulate-icms`, `simulate-pis-cofins`, `obligations/profiles`, `obligations/checklist*` (sem ela o motor de "documentos pendentes" nunca tem dados), `certificates/expiring`, `/block`, `/usage-trail`, `receivables/generate-monthly`, `subscription/limits-check`, `portal/my-data`, convites, `magic-link/request`, `PUT/DELETE /das/{id}`, `fiscal-monitor/nfes/import`, `billing/subscription`.

### 4.3 Serviços
| Serviço | Status | O que falta |
|---|---|---|
| email_service | OK/GATED | Resend real; template de reset existe sem endpoint |
| notification_engine | NO-OP | Usar `email_service.send_email` |
| scheduler | parcial | Lembretes de cobrança só auditam (:323) |
| whatsapp_service | MOCK | Sem provider; sem download de mídia |
| fiscal_monitor_service | MOCK | Tudo inventado |
| ecac integrations | MOCK/STUB | Factory + 503 em produção |
| fiscal_mailbox | GATED | SERPRO real, padrão mock |
| invoices providers | MOCK/STUB | NFS-e Nacional TODO; sem DANFSe |
| storage | OK/GATED | Placeholder em dev |
| document_parser | parcial | Sem XML/CSV/OFX/imagem |
| ai_fiscal | GATED | Cota consumida sem chave |
| rag_service | ingênuo | "Confiança" inventada |
| webhook_service | QUEBRADO parcial | HMAC, eventos, sessão, sem retry |
| api_key_service | FAKE | Não ligado a dependência |
| mercadopago | OK/GATED | |
| obligation_engine, fiscal_calculator, business_days, monthly_closing, guias | OK | |

### 4.4 Flags de configuração (efeito em produção quando ausentes)
`RESEND_ENABLED`/`RESEND_API_KEY` (nenhum e-mail; 2FA e-mail tranca) · `EMAIL_PROVIDER` (fora de Settings) · `PORTAL_URL` (fora de Settings; difere de `APP_URL`) · `FISCAL_MAILBOX_PROVIDER=mock` (dados falsos) · `SERPRO_*` · nenhuma flag para Monitor Fiscal / e-CAC / NFS-e (mock fixo) · `OPENAI_API_KEY` · `SUPABASE_URL`/`SUPABASE_SECRET_KEY` (upload 503/500) · `REDIS_URL` (rate limit global desligado) · `SCHEDULER_MODE`/`RUN_SCHEDULER`/`CRON_SECRET` · `PAGAMENTOS_GO_LIVE` + `MERCADO_PAGO_*` · `WHATSAPP_WEBHOOK_SECRET` · `GOOGLE_CLIENT_ID` · `DIAGNOSTICS_ENABLED` · `ADMIN_*` · `TEST_SUPERUSER_EMAILS` (vira Premium sem pagar se definida).

## 5. Compatibilidade com o modo offline (Frente G)
Toda função nova ou corrigida desta frente segue: exclusões como *soft delete* (`status`/`deleted_at`), nunca `DELETE` físico; escritas idempotentes (repetir a chamada não duplica); `updated_at` tocado em toda alteração; ações que exigem rede (emissão, consulta à SEFAZ/Receita, CNPJ online, envio de e-mail/WhatsApp) devolvem erro claro em vez de fingir sucesso.
