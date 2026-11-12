# Security Review — 2026-11-12 — branch `claude/project-thread-o58lnr` (Frente G: offline-first)

Escopo: `git diff origin/main..HEAD` (PR #70): endpoints `/api/v1/sync/*`, token de
dispositivo, migration `o1i7bc49gk6`, PWA (service worker, cache), banco local
IndexedDB, telas local-first. Portão de Segurança obrigatório da missão (toca
banco, endpoint exposto, autenticação e dados de cliente). O relatório fica em
`docs/audit/` porque a regra do repositório proíbe criar pastas novas.

## Resumo

Nenhum achado crítico ou alto. O isolamento por escritório está garantido em três
camadas (tenant só do token, filtro `tenant_id` em toda consulta e RLS nas tabelas
novas), o token de dispositivo é tipado e recusado na API comum, o push é
idempotente e valida todo payload com os mesmos schemas Pydantic do REST, e a
regra fiscal (nota só como rascunho/pedido de transmissão) é aplicada no
servidor. Os achados abaixo são defesa em profundidade: o token de 30 dias no
IndexedDB sem CSP, o cache HTTP do service worker sem chave por escritório e a
renovação do token sem teto absoluto. Dependências com CVE são anteriores a este
PR e sem caminho de exploração no contexto.

## Achados

### [MÉDIO] Token de dispositivo (30 dias) exposto a XSS sem CSP no frontend
- Arquivo: `frontend/src/lib/offline/device.ts:112` (grava em `sync_meta`), `frontend/public/_headers` (sem `Content-Security-Policy`)
- Descrição: o token de dispositivo fica no IndexedDB, legível por qualquer script da origem. Hoje o token de acesso (30 min) já fica no localStorage, mas o novo token vale 30 dias e renova em janela deslizante, então um XSS passa a render acesso longo ao `/sync/pull` (dados de clientes do escritório). Não há `dangerouslySetInnerHTML` com dado de usuário no diff; o risco depende de um XSS futuro ou de dependência comprometida.
- Correção sugerida: publicar a CSP já prevista em `public/_headers` (`default-src 'self'; connect-src 'self' https://fiscwise-api-45ckqevl6a-rj.a.run.app https://accounts.google.com; script-src 'self' https://accounts.google.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data:; frame-src https://accounts.google.com`) e validar no preview do Cloudflare Pages. Independe deste PR, mas o PR aumenta o valor do alvo.

### [BAIXO] Renovação do token de dispositivo sem tempo de vida máximo
- Arquivo: `backend/app/api/v1/endpoints/sync.py:670` (`renew_device_token`)
- Descrição: cada renovação emite um token novo de 30 dias a partir de um token ainda válido; um token roubado e renovado antes de vencer vale indefinidamente até a revogação do dispositivo ou troca de senha (`tokens_valid_after`).
- Correção sugerida: guardar `first_issued_at` no payload (ou em `sync_devices.created_at`) e recusar renovação depois de 180 dias, exigindo novo login online.

### [BAIXO] Cache HTTP do service worker chaveado só pela URL
- Arquivo: `frontend/vite.config.ts:46-65` (cache `fiscwise-api`, 7 dias)
- Descrição: respostas GET de `/api/v1/*` (dados pessoais de clientes) ficam no Cache Storage até 7 dias. O cache é apagado no logout explícito e na revogação, mas não quando a sessão cai por 401 automático; num navegador compartilhado por dois escritórios o segundo usuário, offline, poderia ver a resposta em cache do primeiro para a mesma URL.
- Correção sugerida: apagar `fiscwise-api` também no 401 que desloga (`api.ts`) e, no login, se o `tenant_id` mudou em relação ao último gravado (`localStorage`), limpar o cache antes de abrir a sessão.

### [BAIXO] Campos sensíveis em claro no IndexedDB (LGPD, já registrado como pendência)
- Arquivo: `frontend/src/lib/offline/db.ts` (stores `clients`, `receivables`)
- Descrição: CPF/CNPJ, e-mail e telefone dos clientes do escritório ficam no banco local sem criptografia; a proteção é o perfil do navegador e a criptografia de disco do sistema. Já documentado em `docs/arquitetura/OFFLINE_SYNC.md` seção 9 como decisão em aberto.
- Correção sugerida: desktop com SQLCipher (fase 2); no PWA avaliar cifrar `document`, `email`, `phone`, `responsible_cpf` com WebCrypto e chave derivada por sessão.

## Scanners

- **bandit** (arquivos do diff, `-ll`): nenhum problema médio ou alto; 1 Low `B110 try/except/pass` em `sync.py:791` (rollback defensivo após falha; intencional).
- **pip-audit** (`requirements.txt`, com os 3 ignores documentados no CI): 2 CVEs em `fpdf2 2.8.3` (CVE-2026-114609/114610, corrigidos em 2.8.8). Pré-existentes, fora do diff; o fpdf2 gera PDF a partir de dados do próprio escritório. Recomendação: subir para 2.8.8 em PR próprio.
- **npm audit --omit=dev**: 4 avisos, todos pré-existentes (nenhuma dependência nova deste PR tem CVE): `zod <4.6.6` (DoS de memória ao validar coleções enormes; a validação é client-side sobre formulários do próprio usuário, sem exploração remota), `react-router`/`react-router-dom` ≤7.17.0 (open redirect com barra invertida em `<Link>`/`useNavigate`; o app não navega para destino vindo de parâmetro externo), `follow-redirects` (transitivo do axios; a API não redireciona). Recomendação: atualizar em PR de dependências.
- **gitleaks** (5 commits da branch): nenhum segredo.

## Não é problema (falsos positivos descartados)

- `register_device` busca `SyncDevice` pelo id sem filtro de tenant: com RLS o registro de outro escritório é invisível e a colisão vira `IntegrityError` → 409; sem RLS o código confere `tenant_id`/`user_id` e devolve 409. Nenhum dado é exposto.
- `payload.tenant_id` nunca é lido no push: tenant, usuário e papel vêm só do token; `device_id` do evento precisa bater com o do token.
- Pull sem filtro de papel nos campos do cliente: paridade com o REST atual (`GET /clients` já devolve `AccountingClientResponse` completo a qualquer usuário do escritório). Se o REST ganhar RBAC por campo, o pull usa o mesmo serializador.
- Mensagens de erro no push: texto de Pydantic e de domínio em português; exceções de banco e bugs viram mensagem genérica e vão só para o log.
- `sync_events.payload` guarda dados pessoais por 90 dias: finalidade definida (idempotência e diagnóstico), retenção automática no tick diário, RLS por escritório.
- Mensagem `fiscwise-sync` do service worker: só o SW da própria origem fala com as abas; a aba apenas dispara um ciclo de sync, sem dados no evento.
- `version` nas respostas REST: contador inteiro, sem informação sensível.
- Token de dispositivo com `type=device` recusado em `get_current_user`; token de usuário recusado em `get_current_device`; `tokens_valid_after` vale para os dois.
