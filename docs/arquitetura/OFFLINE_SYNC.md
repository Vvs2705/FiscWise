# FiscWise offline-first: arquitetura de dados locais e sincronização

Documento de arquitetura da Frente G (2026-11-12). Define como o FiscWise continua
funcionando sem internet no navegador (PWA), no celular (PWA instalado) e, depois,
no PC (Tauri), e como as alterações feitas offline voltam para a nuvem sem perder
nem duplicar nada. O código segue este documento; divergência é bug ou exige
atualizar o documento junto.

Referência interna: o **Moto-OS** (`Vvs2705/moto-os`) já roda offline-first em
produção com Tauri 2 + SQLite e endpoints `sync/push`, `sync/pull` e
`sync/snapshot`. Os padrões abaixo marcados com *(Moto-OS)* foram reaproveitados
de lá, com as lições aprendidas registradas nos comentários do código daquele repo.

---

## 1. Princípios

1. **Local-first.** A interface lê e grava sempre no banco local. A rede só
   sincroniza em segundo plano. Nenhuma tela de cadastro espera a API.
2. **Nunca perder dado em silêncio.** Toda alteração offline vira um evento na
   outbox com ID próprio; o servidor confirma um a um (ACK) e o que ele rejeita
   fica visível para o usuário com o motivo.
3. **Reenviar nunca duplica.** Chave de idempotência `device_id:event_id` em
   todo evento *(Moto-OS)*.
4. **Delta, nunca a base inteira.** Pull incremental por entidade com cursor
   `(updated_at, id)`; a carga inicial é só o primeiro pull a partir do zero,
   paginado. Protege o egress do banco.
5. **Servidor é a autoridade fiscal.** Offline, o sistema **não** autoriza nem
   emite documento fiscal (seção 6).
6. **Só os dados do escritório logado.** O banco local recebe apenas as linhas
   do `tenant_id` do token, filtradas pelo mesmo RBAC da API.
7. **Custo zero.** Nenhum serviço novo: a sincronização roda no FastAPI que já
   existe (Cloud Run), no Postgres do Supabase e no navegador.

---

## 2. Decisão do motor de sincronização (G1.6)

Opções avaliadas em 2026-11-12:

| Opção | Custo | O que exige | Veredito |
|---|---|---|---|
| **PowerSync** (open edition, auto-hospedado) | serviço extra (Node) + MongoDB/Postgres interno | mais um container no Cloud Run, replicação lógica no Supabase, regras de sync em YAML | Rejeitado: infraestrutura nova e segundo ponto de falha; o plano Free do Supabase e a cota do Cloud Run são compartilhados com outros produtos. |
| **ElectricSQL** | serviço extra (Rust) | replicação lógica, apenas leitura (escrita continua por API própria) | Rejeitado: resolve só o pull e ainda precisa de serviço próprio. |
| **RxDB** | lib cliente (core Apache-2.0; vários plugins pagos) | esquema próprio no cliente, endpoints push/pull próprios de qualquer forma | Rejeitado: a parte útil (replicação HTTP) ainda exige escrever os endpoints; adiciona peso e um segundo modelo de dados. |
| **Replicache / Zero** | lib cliente | endpoints push/pull próprios; produto em transição para o Zero | Rejeitado: dependência de roadmap de terceiro para um diferencial central do produto. |
| **Implementação própria** (outbox + `/sync/push` + `/sync/pull` no FastAPI, Dexie no navegador, SQLite no desktop) | zero | código nosso, já validado no Moto-OS | **Escolhido.** |

Motivos: robustez já comprovada no Moto-OS (idempotência, retomada, conflitos),
custo zero, nenhum serviço novo, controle total sobre a regra fiscal e sobre o
RBAC. O custo é manter o código de aplicação dos eventos nos dois lados, que
fica pequeno porque o número de entidades offline é limitado (seção 3).

Bibliotecas no cliente: **Dexie.js** (Apache-2.0) para IndexedDB no PWA;
**vite-plugin-pwa + Workbox** para o service worker; `@tauri-apps/plugin-sql`
com SQLite/SQLCipher no desktop (fase 2). Nenhuma delas tem plano pago.

---

## 3. Escopo offline (entidades e operações)

### 3.1 Entidades offline na versão 1

| Entidade | Tabela servidor | Operações offline | Regra de conflito |
|---|---|---|---|
| Cliente | `accounting_clients` | criar, editar, desativar (`status=inactive`) | LWW por campo com histórico (4.5) |
| Prazo/obrigação | `deadline_items` | criar, editar, concluir, cancelar | LWW por campo com histórico |
| Certificado digital (metadados) | `digital_certificates` | criar, editar, bloquear | LWW por campo com histórico |
| Honorário (conta a receber) | `account_receivables` | criar, editar, marcar pago, cancelar | LWW por campo com histórico |
| Nota fiscal (NFS-e) | `invoices` | **só** criar rascunho e **pedir transmissão** | Servidor é autoridade; sem mesclagem (seção 6) |

"Excluir" no FiscWise já é mudança de status (`inactive`, `cancelled`,
`revoked`); a sincronização usa a mesma semântica: **não há exclusão física**, e
a linha com status terminal é o *soft delete* exigido pela arquitetura. Assim o
pull entrega a "exclusão" como qualquer outra atualização.

### 3.2 O que fica só para consulta offline

Documentos (metadados e lista), fechamentos, guias, obrigações calculadas,
dashboard: o PWA mostra a **última resposta em cache** (React Query persistido +
cache do service worker), com selo "dados de HH:MM". Não há outbox para essas
entidades na versão 1; os botões de ação ficam desabilitados com aviso.

### 3.3 O que exige rede (desabilitado offline, com aviso claro)

Emissão e cancelamento de NFS-e, consulta à SEFAZ/Receita/e-CAC, consulta de
CNPJ, upload e download de arquivos, geração de dossiê PDF, IA fiscal, pagamento
e assinatura, convites do portal, WhatsApp.

---

## 4. Modelo de dados

### 4.1 Esquema lógico (igual no servidor, no IndexedDB e no SQLite)

Cada entidade offline tem, nos três lugares, as mesmas colunas da tabela do
servidor mais:

- `version INTEGER NOT NULL DEFAULT 1` – incrementa a cada atualização no
  servidor (listener `before_update` no SQLAlchemy, vale para a API REST e para o
  sync). Usado para detectar conflito.
- `updated_at` – já existe; é a base do cursor do pull.

Colunas **só locais** (nunca sobem): `_sync_status` (`synced` | `pending` |
`error`), `_local_updated_at`.

### 4.2 Tabelas novas no servidor (migration reversível)

```
sync_devices
  id uuid pk            -- gerado no cliente (UUID v4), persistido localmente
  tenant_id uuid fk     -- RLS tenant_isolation
  user_id uuid fk
  name text             -- "Chrome no Windows", "PWA Android"
  platform text         -- web | android | ios | windows | macos | linux
  app_version text
  last_seen_at timestamptz
  revoked_at timestamptz null
  created_at timestamptz

sync_events                -- log de tudo que o servidor aplicou (push)
  id uuid pk
  sequence bigserial unique
  tenant_id uuid fk
  device_id uuid fk -> sync_devices
  event_id uuid             -- id do evento gerado no cliente
  idempotency_key text unique   -- "<device_id>:<event_id>"
  entity_type text          -- client | deadline | certificate | receivable | invoice
  entity_id uuid
  operation text            -- create | update | delete | emit_requested
  payload jsonb
  status text               -- applied | rejected
  error text null
  client_created_at timestamptz
  received_at timestamptz

sync_conflicts             -- histórico de LWW por campo (nada se perde)
  id uuid pk
  tenant_id uuid fk
  entity_type text, entity_id uuid
  event_id uuid             -- evento que causou a sobrescrita
  device_id uuid
  base_version int          -- versão que o cliente achava que tinha
  server_version int        -- versão que o servidor tinha
  fields_overwritten jsonb  -- {campo: {server: v1, client: v2}}
  resolved_at timestamptz null, resolved_by uuid null
  created_at timestamptz
```

Índices: `sync_events (tenant_id, sequence)`, `sync_events (tenant_id,
entity_type, entity_id)`, `sync_conflicts (tenant_id, resolved_at)`, e
`(tenant_id, updated_at, id)` em cada tabela offline (cursor do pull). Todas as
tabelas novas entram com RLS `tenant_isolation` igual às demais
(`current_app_tenant_id()`).

### 4.3 Banco local (Dexie / IndexedDB)

Um banco por escritório: `fiscwise-<tenant_id>`. Stores:

```
clients, deadlines, certificates, receivables, invoices   -- mesmas colunas do servidor + _sync_status
sync_outbox      -- id, entity_type, entity_id, operation, payload, base_version,
                    created_at, attempts, status (pending|syncing|synced|error),
                    last_error, next_retry_at
sync_meta        -- device_id, device_token, cursors por entidade, last_sync_at, last_error
sync_conflicts   -- cópia local do que o servidor devolveu para a tela de revisão
```

No desktop as mesmas stores viram tabelas SQLite (SQLCipher), com o mesmo
contrato; o módulo `src/lib/offline/` define a interface `LocalDb` e cada
plataforma implementa.

---

## 5. Protocolo de sincronização

### 5.1 Dispositivo e autenticação

1. No primeiro login online, o cliente gera `device_id` (UUID v4), guarda em
   `sync_meta` e chama `POST /api/v1/sync/devices` (token de usuário normal).
   Resposta: registro do dispositivo + **token de dispositivo** (JWT `typ=device`,
   30 dias, com `device_id`, `sub`, `tenant_id`, `role`, `iat`).
2. Os endpoints `/sync/*` aceitam **só** o token de dispositivo. A cada chamada o
   servidor confere: assinatura, `typ`, dispositivo existe, `revoked_at IS NULL`,
   usuário ativo, `iat >= users.tokens_valid_after` (troca de senha derruba todos
   os dispositivos, igual ao token web).
3. **Renovação:** `POST /api/v1/sync/devices/token` com o token de dispositivo
   ainda válido devolve um token de dispositivo novo **e** um token de acesso
   (30 min) para a API comum. O cliente renova quando faltam menos de 7 dias e
   sempre que uma chamada comum devolver 401 (antes de deslogar). Assim o
   usuário não é expulso ao voltar de um período offline.
4. **Revogação:** `GET /api/v1/sync/devices` lista; `POST /api/v1/sync/devices/{id}/revoke`
   (dono/admin) marca `revoked_at`. No próximo contato o dispositivo recebe
   `401 {"code":"device_revoked"}` e **apaga o banco local inteiro** antes de ir
   para a tela de login (limpeza remota, G5). Eventos pendentes daquele
   dispositivo são descartados, e o painel mostra quantos eram.

### 5.2 Outbox *(Moto-OS)*

Toda escrita local grava a linha da entidade **e** o evento da outbox na mesma
transação do Dexie. Evento:

```
id (uuid v4), entity_type, entity_id, operation, payload (campos alterados),
base_version (versão local no momento da edição), created_at (ISO),
status pending → syncing → synced | error, attempts, last_error, next_retry_at
```

- Edições sucessivas do mesmo registro **antes** do envio são **coalescidas**
  em um único evento `update` (payload mesclado, `base_version` do primeiro).
- Backoff exponencial 5 s → 10 min em erro de transporte. Erro `rejected` do
  servidor não entra em retry: fica `error` com o motivo até o usuário agir.
- Na abertura do app, eventos presos em `syncing` voltam para `pending`
  (`recoverStuckOutbox`, Moto-OS): fechar a aba no meio do envio não perde nada,
  porque o servidor deduplica.

### 5.3 Push

`POST /api/v1/sync/push` (token de dispositivo), corpo `{events: [até 200]}`,
resposta `{acks: [{id, status: "ack"|"rejected", error?, entity?}]}`.

Para cada evento, em uma transação própria:

1. `device_id`/`tenant_id` do evento precisam bater com o token; senão
   `rejected`.
2. Se `idempotency_key` já existe em `sync_events`: devolve o resultado
   anterior sem reaplicar (ACK ou a mesma rejeição).
3. Valida o payload com o schema Pydantic já usado na API REST
   (`AccountingClientCreate/Update` etc.) e o RBAC do papel do token.
4. Aplica (seção 4.5 para conflitos), grava `sync_events` com `applied`, grava
   `audit_events` (`sync.<entity>.<operation>`), e inclui no ACK a linha final
   do servidor (`entity`), para o cliente gravar `version`/`updated_at` reais.
5. Erro transitório de banco (conexão, timeout, deadlock): **nada é gravado** e a
   resposta é `503` com os ACKs já obtidos; o cliente devolve o resto a
   `pending`. Gravar `rejected` num erro passageiro congelaria o erro para
   sempre *(achado do Moto-OS)*.
6. Erro de validação/domínio: `sync_events.status=rejected` com a mensagem; o
   cliente marca o evento `error` e mostra na tela de sincronização.

`sync_events` guarda o payload por 90 dias (job de retenção no `tick` horário).

### 5.4 Pull (delta por entidade)

`GET /api/v1/sync/pull?entity=clients&since=<updated_at ISO>&after_id=<uuid>&limit=500`

- Devolve linhas do tenant com `(updated_at, id) > (since, after_id)` ordenadas
  por `(updated_at, id)`, limitadas a `updated_at <= now() - 5 s` (marca d'água:
  evita o buraco de uma transação que ainda não commitou com `updated_at` menor
  *(Moto-OS)*).
- Resposta: `{rows: [...], next: {since, after_id}, has_more}`. O cliente só
  persiste o cursor depois de gravar todas as linhas do lote.
- A linha vinda do servidor **sempre vence** no banco local, exceto quando existe
  evento `pending` para o mesmo registro: aí o cliente guarda a linha do servidor
  como base (`version`) e mantém a edição local até o push resolver.
- Carga inicial = pull com cursor vazio, entidade por entidade, em lotes de 500.
  O cliente mostra "Baixando dados do escritório (3/5)".
- Toda escrita que passa pela API REST, por rotinas agendadas ou por outro
  dispositivo chega pelo pull, porque o cursor é por `updated_at` da linha e não
  por log de eventos. Isso cobre honorários gerados pelo scheduler, parsing de
  documentos e edições feitas na web.

### 5.5 Conflitos

Regra por entidade (seção 3.1):

**Cadastros (cliente, prazo, certificado, honorário): last-write-wins por campo,
com histórico.**

- O evento `update` leva só os campos alterados e o `base_version`.
- `base_version == version` no servidor → aplica, `version + 1`.
- `base_version < version` → o servidor aplica **apenas os campos do evento**
  (o cliente é o último a escrever nesses campos), preserva os demais campos que
  mudaram no servidor, incrementa `version` e grava em `sync_conflicts` o par
  `{campo: {server, client}}` de cada campo sobrescrito. O ACK volta com
  `conflict: true` e os campos; o cliente grava em `sync_conflicts` local.
- Tela "Sincronização" lista os conflitos com "manter como está" (resolve) ou
  "restaurar valor do servidor" (gera um novo `update`). Nada é perdido em
  silêncio: o valor anterior fica no histórico.
- Transições de status terminal nunca são revertidas por LWW. Terminais por
  entidade: cliente `inactive`; prazo `completed` e `cancelled`; certificado
  `revoked`; honorário `paid` e `cancelled`. O servidor rejeita `update` que
  tente sair deles, com mensagem; reativar continua possível pela API REST
  (ação explícita, online), e só então o pull propaga o novo status.
- O conflito só é registrado quando o valor enviado difere do valor atual do
  servidor; evento repetido devolve o mesmo ACK e o conflito original.
- A auditoria `sync.<entidade>.<operação>` guarda só os nomes dos campos
  alterados, `event_id`, `device_id` e o flag de conflito, sem valores (LGPD).
- Paridade com a API REST no push: criar cliente respeita o limite do plano e o
  CNPJ/CPF único e gera `client_code`; concluir prazo recorrente gera a próxima
  ocorrência; marcar honorário pago preenche `paid_at`. O webhook
  `client.created` não é disparado pelo sync (pendência).

**Documentos fiscais (NFS-e): servidor é autoridade, sem mesclagem.**

- Offline o cliente só cria `invoices` com `status=draft` e eventos
  `emit_requested`. Qualquer outro campo de status vindo do cliente é rejeitado.
- Dois dispositivos pedindo a transmissão do mesmo rascunho: o segundo recebe
  ACK idempotente (a nota já está `queued`/`processing`), nunca duas emissões.
- `emit_requested` chama `queue_emission` (status `queued`) e agenda o mesmo
  processamento em segundo plano que `POST /invoices/{id}/emit` usa hoje. Esse
  processamento morre quando o Cloud Run desliga; a fila em Postgres da Frente
  A2 (`background_jobs`, kind `invoice.emit`, varredura das notas `queued` sem
  job no tick horário) é quem garante a emissão. Quando ela entrar, o push
  passa a só gravar `queued`.
- A criação de nota pelo sync replica as validações de `InvoiceService`
  (tomador, competência, cliente e emissor do escritório) porque o serviço não
  aceita o id gerado no cliente; `invoices` não tem `version` (sai `null`).

### 5.6 Ciclo (`syncNow`)

1. Recuperar eventos presos em `syncing`.
2. Push (drena a outbox em lotes de 200).
3. Pull de cada entidade até `has_more=false`.
4. Atualizar `last_sync_at` e invalidar as queries do React Query.

Dispara: ao abrir o app, ao voltar a conexão (`online`), a cada 60 s com rede,
ao criar evento (debounce 2 s), pelo botão "Sincronizar agora" e, quando o
navegador suportar, por Background Sync (`sync` tag `fiscwise-outbox`) com a aba
fechada.

---

## 6. Regra fiscal obrigatória (G2)

**Offline, o FiscWise não autoriza, não emite e não cancela documento fiscal.**
A autorização é ato da administração tributária (SEFAZ estadual para NF-e/NFC-e;
ambiente nacional ou prefeitura para NFS-e). O sistema só prepara e enfileira.

### 6.1 Estados locais da nota

| Situação | Status mostrado | Status interno |
|---|---|---|
| Rascunho salvo offline | "Rascunho (não enviado)" | `draft` + `_sync_status=pending` |
| Usuário mandou transmitir sem rede | **"Pendente de transmissão"** | `pending_transmission` (só local; no servidor vira `queued`) |
| Servidor recebeu o pedido | "Na fila de emissão" | `queued` / `processing` |
| Provedor/SEFAZ autorizou | "Emitida" | `issued` |
| Rejeitada | "Rejeitada" com o código e a descrição | `rejected` |

Nunca aparece "Emitida" ou "Autorizada" sem o `issued_at` e o protocolo vindos do
servidor. Ao reconectar, os `emit_requested` saem **na ordem de criação**, com
retry e backoff; rejeição gera alerta visível na lista de notas e na tela de
sincronização.

### 6.2 Contingência oficial: o que a legislação permite e o que o FiscWise faz

Pesquisa feita em 2026-11-12. O FiscWise hoje emite **NFS-e** (serviços, padrão
nacional via provedor); NF-e/NFC-e (mercadorias, modelos 55/65) não são emitidas
pelo produto. A tabela cobre os três para a decisão ficar documentada.

| Documento | Modo oficial | Base legal | Prazo de transmissão | FiscWise |
|---|---|---|---|---|
| NFS-e padrão nacional | **Não existe contingência offline nem RPS** no padrão nacional: a DPS é enviada ao ambiente nacional e a NFS-e só existe depois da autorização. O app oficial guarda "NFS-e não transmitidas" para envio posterior, que é exatamente a fila "Pendente de transmissão". | Resoluções CGNFS-e (gov.br/nfse); obrigatoriedade MEI desde 1º/9/2023 (CGSN 169/2022 e 172/2023) e ME/EPP do Simples a partir de 1º/11/2026 (CGSN 189/2026 e 191/2026) | Não há prazo legal de "regularização" porque não há documento provisório; a nota só vale quando autorizada. Vale a data de competência/fato gerador para o ISS. | Fila "Pendente de transmissão" (6.1). Nada mais é permitido. |
| NFS-e municipal (padrão ABRASF, prefeituras que ainda não migraram) | **RPS (Recibo Provisório de Serviços)** pode ser emitido offline e convertido em NFS-e depois | Legislação de cada município (ex.: São Paulo exige conversão até o 10º dia seguinte à emissão do RPS; outros municípios usam 5 a 10 dias) | Varia por município | **Não implementado.** O provedor atual é o padrão nacional. Se um município ABRASF for homologado, o RPS entra como fase 2 com o prazo do município configurado no emissor. |
| NFC-e (modelo 65) | Contingência **off-line** (`tpEmis=9`): emite com a mesma chave, imprime DANFE com "EMITIDA EM CONTINGÊNCIA" e transmite depois | Ajuste SINIEF 19/2016, cláusula 11ª, inciso I e § 1º; MOC 7.0 Anexo IV | **Até o primeiro dia útil subsequente à emissão** (o texto legal não fala em 24 h; "24 horas" é a orientação de algumas SEFAZ, ex.: PE). Cancelamento: até 24 h da autorização (cláusula 15ª), prazo que a UF pode reduzir. | Não aplicável hoje (produto não emite NFC-e). Se vier a emitir, é o único modo offline permitido e o prazo entra como alerta automático. |
| NF-e (modelo 55) | EPEC (`tpEmis=4`), SVC-AN (`tpEmis=6`), SVC-RS (`tpEmis=7`), FS-DA (formulário de segurança). Todos exigem **rede** com o ambiente de contingência, exceto FS-DA. | Ajuste SINIEF 07/2005 e NT 2014.001; EPEC: 168 h para transmitir a NF-e correspondente; PR e PB deixaram de aceitar EPEC em 5/10/2026 (Ajuste SINIEF 25/2026, NT 2014.001 v1.40/1.41) | 168 h (EPEC) | Não aplicável hoje. Registrado para a fase em que o produto emitir NF-e: SVC/EPEC não são "offline" (precisam de rede), e FS-DA exige formulário de segurança físico. |

Conclusão: para o documento que o FiscWise emite (NFS-e nacional) **não há
modalidade legal de emissão offline**; o comportamento correto é guardar o
pedido e transmitir quando houver rede, mostrando sempre "Pendente de
transmissão". Fontes:
[Ajuste SINIEF 19/2016](https://www.normaslegais.com.br/legislacao/ajuste-sinief-19-2016.htm),
[SEFAZ-PE: contingência NFC-e](https://www.sefaz.pe.gov.br/Servicos/Nota-Fiscal-de-Consumidor-Eletronica/Paginas/contingencia.aspx),
[NFE.io: contingência offline NFC-e (MOC 7.0 Anexo IV)](https://nfe.io/docs/documentacao/nota-fiscal-consumidor/integracao-api/contingencia-offline-nfce/),
[NFE.io: modos de contingência NF-e/NFC-e](https://nfe.io/docs/emissao-nfe-nfce-processamento-resiliencia-e-contingencia/),
[TecnoSpeed: fim do EPEC em PR e PB](https://blog.tecnospeed.com.br/fim-do-epec/),
[TecnoSpeed: NFS-e Nacional](https://blog.tecnospeed.com.br/nfse-nacional/),
[Resoluções CGNFS-e (gov.br/nfse)](https://www.gov.br/nfse/pt-br/biblioteca/portarias-e-resolucoes-cgnfs-e/resolucaocgnfsen930122025.pdf),
[RPS em São Paulo: orientação da prefeitura](https://www.prefeitura.sp.gov.br/cidade/upload/orientacao_rps_v3_1637351637.pdf).

---

## 7. Plataformas (G3)

### 7.1 PWA (web e celular) – fase 1, nesta entrega

- `vite-plugin-pwa` com Workbox: precache do app shell (HTML, JS, CSS, fontes,
  ícones); `NetworkFirst` para `/api/v1/*` de leitura das telas de consulta
  (3.2), nunca para `/sync/*` nem para escrita; `CacheFirst` para fontes do
  Google.
- `manifest.webmanifest` com nome, ícones 192/512 (maskable), `display:
  standalone`, `theme_color #e05e18`, `start_url /painel`.
- Prompt de instalação próprio (`beforeinstallprompt`) na tela inicial e em
  Configurações; no iOS, instrução "Compartilhar → Adicionar à Tela de Início".
- Background Sync quando disponível (Chrome/Edge/Android); nos demais, o sync
  roda com a aba aberta.
- Persistência: `navigator.storage.persist()` pedido no primeiro login para o
  navegador não descartar o IndexedDB sob pressão de disco.

### 7.2 Desktop Windows (Tauri 2) – fase 2

Mesmo front (build do Vite) empacotado pelo Tauri; `LocalDb` implementado sobre
`@tauri-apps/plugin-sql` com **SQLCipher** (chave guardada no Windows Credential
Manager via crate `keyring`, como no Moto-OS). Instalador NSIS por usuário,
atualização automática pelo `tauri-plugin-updater` apontando para GitHub
Releases (**pré-lançamento** até o dono aprovar). O build do `.exe` só roda no
Windows (no PC do dono ou em runner `windows-latest` do GitHub Actions). Entra
depois que o PWA e o motor de sync estiverem estáveis.

### 7.3 Mobile nativo – só avaliação

O PWA cobre o celular na versão 1. Para lojas: **Capacitor** (reaproveita o
mesmo build web, plugins maduros para SQLite com criptografia, push nativo) é
preferível a Tauri mobile (ainda jovem para iOS). Publicação em loja é
pendência de decisão/custo (Apple Developer US$ 99/ano, Google Play US$ 25).

---

## 8. Experiência do usuário (G4)

- **Indicador permanente** no cabeçalho, sempre visível, com quatro estados:
  `Online` · `Offline (N pendentes)` · `Sincronizando (x de y)` · `Erro (N
  itens)`. "Online" significa que o último push/pull respondeu, não só que há
  rede *(Moto-OS)*.
- Clique no indicador abre `/sincronizacao`: pendências por entidade, erros com
  motivo, conflitos para revisão, última sincronização, dispositivo atual,
  botão **Sincronizar agora**, botão "Instalar aplicativo".
- Linhas com `_sync_status=pending` mostram um ponto discreto "não enviado";
  `error` mostra o ícone de alerta com o motivo no hover.
- Recursos que exigem rede ficam desabilitados offline com o aviso "Precisa de
  internet: a emissão depende da SEFAZ/prefeitura" (texto específico por ação).
- Atualização otimista só nos cadastros (3.1); jamais em emissão ou
  cancelamento fiscal.

---

## 9. Segurança e LGPD (G5)

- **Dados locais:** apenas do `tenant_id` e do usuário logados; o pull aplica o
  mesmo RBAC da API (campos sensíveis do cliente só para quem pode vê-los).
- **Criptografia em repouso:** desktop com SQLCipher (7.2). No navegador o
  IndexedDB não oferece criptografia transparente; a proteção é o perfil do
  navegador e a criptografia de disco do sistema (BitLocker/FileVault/Android).
  Decisão registrada como pendência: avaliar cifrar os campos sensíveis
  (documento, e-mail, telefone) com WebCrypto e chave derivada por sessão, com o
  custo de perder busca local por esses campos.
- **Token:** token de dispositivo com 30 dias, renovado em janela deslizante;
  invalidado por troca de senha (`tokens_valid_after`) e por revogação.
- **Revogação com limpeza remota:** painel em Configurações → Dispositivos
  (lista, último acesso, botão Revogar). O dispositivo revogado apaga o banco
  local no próximo contato (5.1.4). **Logout explícito** também apaga o banco
  local (computador compartilhado).
- **Portão de segurança:** `security-review` obrigatório no PR por tocar banco,
  endpoint exposto, autenticação e dados de cliente.
- Rate limit nos endpoints `/sync/*` (mesmo middleware), tamanho máximo de lote
  (200 eventos / 1 MB) e validação Pydantic de todo payload.

---

## 10. Testes (G6, critério de aceite)

Backend (`pytest`, SQLite em memória + CI com Postgres):

1. Push idempotente: o mesmo evento duas vezes aplica uma vez e devolve o mesmo ACK.
2. Conflito LWW por campo: dois dispositivos editam o mesmo cliente; os dois
   campos sobrevivem e `sync_conflicts` registra a sobrescrita.
3. Pull paginado com cursor `(updated_at, id)` e marca d'água; nenhuma linha
   pulada ou repetida entre páginas.
4. Dispositivo revogado recebe 401 `device_revoked`; token de outro tenant é
   rejeitado; evento de outro `device_id` é rejeitado.
5. Regra fiscal: evento que tente gravar `status=issued` em nota é rejeitado;
   `emit_requested` duplicado é idempotente.
6. Erro transitório no meio do lote devolve 503 sem gravar `rejected`.

Frontend (`vitest` + `fake-indexeddb`, transporte falso):

1. Offline → cria/edita → online → sincroniza; outbox vazia e `version` do
   servidor gravada.
2. Dois clientes (dois `device_id`) editam o mesmo registro; o segundo recebe
   conflito e a tela de revisão mostra os campos.
3. Queda no meio do push (transporte falha após o lote 1): retomada não duplica
   (ACKs idempotentes do servidor falso).
4. Fila com 500 operações: push em lotes de 200, ordem preservada.
5. App "fechado" no meio do envio (eventos em `syncing`) e reaberto offline:
   `recoverStuckOutbox` devolve para `pending`; dados continuam visíveis.

E2E (Playwright, perfil mobile + `context.setOffline(true)`): abrir o app
instalado sem rede, criar cliente, voltar a rede, ver o cliente na API.

---

## 11. Pendências e decisões em aberto (G7)

| Item | Tipo | Alternativa |
|---|---|---|
| Certificado de assinatura de código para o instalador Windows (EV ou OV, ~US$ 200–400/ano) | custo | Publicar sem assinatura como pré-lançamento; o Windows mostra "Editor desconhecido". |
| Publicação em lojas (Apple/Google) | custo/decisão | PWA instalável cobre o celular. |
| Criptografia de campos sensíveis no IndexedDB | decisão | Seção 9. |
| RPS para municípios ABRASF | decisão de produto | Só quando houver emissor homologado em município não migrado. |
| Build do `.exe` do Tauri | infraestrutura | Runner `windows-latest` do GitHub Actions (grátis em repositório público; em privado consome os 2.000 min/mês do plano Free). |
| Endpoint para resolver/listar `sync_conflicts` no servidor | contrato | Hoje a revisão é local (tela Sincronização); o servidor só grava o histórico. Entra com a tela de revisão compartilhada entre dispositivos. |
| Webhook `client.created` para clientes criados pelo sync | paridade | Disparar no handler `create` do push, como no REST. |
| Isolamento por escritório do cache HTTP do service worker | segurança | Cache chaveado por URL; limpo no logout e na revogação. Chavear por tenant se um navegador for compartilhado entre escritórios. |
| E2E Playwright offline (perfil mobile, `setOffline`) | teste | Depende de backend de preview; cenários unitários já cobrem a engine. |

---

## 12. Dependências com as outras frentes

- **A1 (paginação e índices):** o pull já nasce paginado e com índice
  `(tenant_id, updated_at, id)`; a listagem REST de clientes/prazos/certificados/
  honorários pode continuar sem paginação até A1 porque o PWA passa a ler do
  banco local.
- **B e C:** toda função nova ou tela redesenhada que escreva em uma entidade da
  seção 3.1 deve escrever pela camada `src/lib/offline/` (repositório local +
  outbox), nunca direto no `api.post`. As telas de consulta (3.2) devem tolerar
  dado em cache com selo de hora.
