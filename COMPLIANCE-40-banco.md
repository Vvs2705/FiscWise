# COMPLIANCE-40 — Frente de banco de dados (itens 2, 3, 18, 31 e migrações)

Auditoria de 21/11/2026, feita contra o checklist "40 requisitos" com leitura
crítica: onde o documento estava errado ou incompleto para o FiscWise, isso
está dito na seção 5. Os demais itens estão em
[COMPLIANCE-40-seguranca.md](COMPLIANCE-40-seguranca.md) (bloco A) e no
relatório do jurídico.

## 1. Perfil

**P2+.** SaaS B2B para escritórios contábeis, em produção, com cobrança
(Mercado Pago). Multi-tenant no mesmo Postgres (Supabase), com RLS forçada
por escritório. O FiscWise é **operador** dos dados fiscais dos clientes dos
escritórios e guarda segredos críticos (certificado A1 e senha). Backend
FastAPI + SQLAlchemy async + Alembic no Cloud Run, com segredos no Secret
Manager.

## 2. Vereditos

| Nº | Item | Veredito | Evidência ou o que foi feito | Arquivo / commit |
|----|------|----------|------------------------------|------------------|
| 2 | Controle de acesso, IDOR, filtro por tenant | 🔧 APLICADO | A base já era boa: RLS com FORCE em todas as tabelas com `tenant_id`, `tenant_id` do token conferido com o usuário, portal do cliente preso a uma lista de rotas. A varredura nova (40 rotas, B cria e A tenta ler, alterar, apagar e acionar) achou **2 falhas reais**, as duas do mesmo tipo: um id vindo do corpo ou da rota gravado sem checar o escritório. (a) `PUT /certificados/emissao/{id}` aceitava o `certificado_id` de outro escritório se o contexto RLS faltasse, e o emissor de A passaria a assinar NFS-e com o A1 de B. (b) `PUT /obligations/profiles/{client_id}` criava, no escritório A, um perfil apontando para o cliente de B. Neste caso a RLS **não** protege, porque a checagem de FK do Postgres não passa pelas policies. Também entrou uma trava no CI: toda tabela com `tenant_id` precisa ter RLS, FORCE e a policy `tenant_isolation`. | `app/domain/certificados/servico.py`, `cofre.py`, `endpoints/obligations.py`, `tests/test_idor_cross_tenant.py`, `tests/test_rls_postgres.py` · `167325e` |
| 3 | Criptografia de campo (A1, senha, tokens) | 🔧 APLICADO (parcial: o A1 já atendia) | **Certificado A1 e senha: ✅ já atendiam.** O cofre usa AES-256-GCM com nonce por campo e AAD `tenant:cert:campo`, e o blob copiado para outro escritório não abre (`cofre.py`). **Tokens de integração: ✅** (Mercado Pago, SERPRO, OpenAI, Resend, WhatsApp). Ficam no Secret Manager, não no banco. O segredo de assinatura de webhook já ia cifrado (Fernet). **Lacuna achada: o segredo TOTP do 2FA ficava em texto puro** em `users.two_factor_secret`, e um dump do banco entregava o segundo fator. Agora ele é cifrado com a mesma chave do cofre. O valor legado continua valendo e é cifrado no próximo login, sem ninguém perder o 2FA. A migração alarga a coluna, sem perda de dados. | `app/core/campo_cifrado.py`, `endpoints/auth.py`, `y1b2totpcifrado` · `77b35cf` |
| 18 | Exclusão e anonimização com retenção legal | 🔧 APLICADO | Já existia a exclusão automática 60 dias depois de a conta vencer, com aviso 72 h antes (`services/exclusao_dados.py`). Três lacunas: (a) o **pedido LGPD do dono** (`POST /account/delete`) só era gravado, e nada o executava. A rotina automática pula de propósito quem pediu. Agora existe `POST /admin/lgpd/exclusao`, com token de admin, nome do escritório redigitado e prévia por padrão. (b) A exclusão apagava `audit_events`, onde ficam IP e data de acesso que o **Marco Civil (art. 15) manda guardar por 6 meses**. Agora o conteúdo sai na hora e o registro expira em 6 meses. (c) A **exportação LGPD não trazia NFS-e (XML), guias, fechamentos, procurações nem caixa postal**, que o escritório precisa guardar por 5 anos antes de os dados sumirem. A resposta de `/account/delete` também dizia que o FiscWise retinha documentos fiscais por 5 anos, o que a exclusão não faz. O texto foi corrigido. | `services/exclusao_dados.py`, `endpoints/admin.py`, `endpoints/account.py`, `tests/test_exclusao_lgpd.py` · `96adf50` |
| 31 | Backups e restauração documentada | 🔧 APLICADO + 🔒 | Já existia o `pg_dump` diário cifrado com `age`, enviado ao R2 com retenção de 30 dias. Lacunas: (a) o **Storage do Supabase (documentos dos clientes, guias, comprovantes) não tinha backup**. O passo novo está no workflow e fica desligado até você criar as chaves (🔒, abaixo). (b) Nada conferia se o dump abria. Agora o `pg_restore --list` confere antes de cifrar. (c) A restauração era descrita em 2 linhas. Agora há teste mensal com conferência e um roteiro de produção com RPO de 24 h. Testado aqui: o dump do head foi restaurado num banco vazio e as 47 tabelas voltaram com FORCE RLS. | `.github/workflows/db-backup.yml`, `DEPLOY.md` §11 · `5844c1a` |
| — | Migrações | ✅ (com observações) | Banco vazio até o head: ok. Rollback das 8 últimas e volta ao head: ok. Uma só head. Comparação modelo × banco migrado: nenhuma tabela ou coluna faltando. Restam diferenças de nulidade: 13 colunas `NOT NULL` no modelo e `NULL` no banco (ex. `invoices.created_at`) e 1 ao contrário (`sync_events.sequence`). Também há `json` × `jsonb` e `timestamp` com e sem fuso em 4 colunas da API pública. Nenhuma é de segurança. Não mexi: virar `NOT NULL` exige conferir os dados de produção antes (🔒). O `downgrade base` não remove os tipos ENUM e o `upgrade` seguinte falha. Fica registrado, sem correção: ninguém desce até a base em produção. | — |

## 3. Aplicado (commits na branch, um por item)

1. `167325e` — #2: filtro por escritório no certificado A1 e no perfil fiscal, varredura IDOR, trava de RLS por tabela.
2. `77b35cf` — #3: segredo TOTP cifrado (AES-256-GCM), migração `y1b2totpcifrado`.
3. `96adf50` — #18: execução do pedido LGPD, retenção de 6 meses dos registros de acesso, exportação dos documentos fiscais.
4. `5844c1a` — #31: dump conferido antes de cifrar, backup do Storage (desligado), restauração documentada.

Testes: suíte completa verde (ver PR). Os testes de RLS em PostgreSQL também
passaram localmente (`RUN_PG_RLS=1`), num Postgres 16 migrado até o head.

## 4. 🔒 Bloqueados (precisam de você)

| O quê | Por quê | Passo exato |
|-------|---------|-------------|
| Ligar o backup do Storage | Exige criar credenciais e segredos | Supabase → Storage → S3 Connection: ligar o protocolo e gerar as chaves. GitHub → Variables: `SUPABASE_S3_ENDPOINT` (`https://<ref>.supabase.co/storage/v1/s3`) e `SUPABASE_S3_REGION`. GitHub → Secrets: `SUPABASE_S3_ACCESS_KEY_ID` e `SUPABASE_S3_SECRET_ACCESS_KEY`. Depois, Actions → Database backup → Run workflow. |
| Pedidos LGPD pendentes | A execução apaga dados reais | Ver quem pediu: `SELECT id, name, deletion_requested_at FROM tenants WHERE deletion_requested_at IS NOT NULL AND dados_excluidos_em IS NULL;`. Para cada um, depois de conferir com o dono que ele exportou: `POST /api/v1/admin/lgpd/exclusao` com `{"tenant_id": "...", "confirmar_nome": "<nome exato>"}` (prévia) e depois com `"executar": true`. Exige `ADMIN_OPERATIONS_ALLOWED=true` e `ADMIN_EMERGENCY_TOKEN` no ambiente. |
| `CERT_ENCRYPTION_KEY` | Segredo de produção | Nada a fazer se ela já está no Secret Manager, porque o cofre A1 depende dela. **Atenção:** trocar essa chave agora invalida os certificados A1 **e** os 2FA TOTP já cifrados. Uma rotação precisa de recifragem (o campo `chave_versao` existe para isso), e isso não foi feito. |
| Retenção dos logs do Cloud Logging | Config de produção | O Marco Civil pede 6 meses de registro de acesso. O `audit_events` guarda login, IP e data, mas o log por requisição fica no bucket `_Default`, que guarda 30 dias. Se quiser cobrir tudo: `gcloud logging buckets update _Default --location=global --retention-days=180` (tem custo de armazenamento). |
| Cópia da chave `age` | Custódia de segredo | A chave privada é o único jeito de abrir os backups. Guardar uma segunda cópia offline (pendrive em local seguro ou papel). |
| Plano do Supabase / PITR | Custo | Hoje o único backup é o do R2 (RPO de 24 h). O Supabase Pro dá backup gerenciado diário e restaura também o Storage. Decisão de custo: `{{PREENCHER}}` (plano atual do Supabase). |
| `NOT NULL` nas 13 colunas divergentes | Migração que pode falhar ou exigir backfill | Só depois de `SELECT count(*) ... WHERE <coluna> IS NULL` em produção dar zero. Baixa prioridade. |

## 5. Lacunas do documento (onde ele não serve como está)

1. **Item 2 só fala em "toda query filtra por tenant".** As falhas reais
   achadas foram de outro tipo: **id de outro escritório gravado como
   referência** (FK). Com RLS, a leitura está protegida, mas a checagem de FK
   do Postgres ignora as policies. O teste certo é "A grava apontando para o
   registro de B", não só "A lê o registro de B". A varredura nova cobre os
   dois casos.
2. **RLS "aberta sem contexto".** As policies liberam tudo quando não há
   escritório no contexto. É assim que o agendador, os webhooks e o backup
   funcionam. Isso também quer dizer que qualquer rota que esqueça de fixar
   o contexto fica sem a segunda camada. Hoje toda autenticação fixa o
   contexto (`deps.py`), e o documento não pede para conferir isso.
3. **Item 3 lista A1, senha e tokens de integração, mas esquece os segredos
   de autenticação guardados no banco.** Era exatamente onde estava a lacuna
   (TOTP em texto puro).
4. **Item 18 fala em "respeitar a retenção legal de dados fiscais" como se
   ela fosse do FiscWise.** Para os dados dos clientes, o FiscWise é
   operador. A guarda por 5 anos (CTN arts. 173 e 195) é obrigação do
   escritório e do contribuinte. O dever do operador é **devolver**
   (exportação completa) e **excluir** ao fim do contrato (LGPD art. 16). O
   FiscWise só retém o que é dele como controlador: o histórico de cobrança e
   os registros de acesso do Marco Civil, que o documento não menciona.
5. **Item 31 fala só do Postgres.** Os arquivos dos clientes ficam no Storage
   e não tinham cópia. Faltam também a conferência do backup, a custódia da
   chave e um RPO declarado.
6. **O documento não tem item para migrações**, embora a distribuição de
   agentes cite "Banco de Dados (… migrações)". Foram cobertos: subida do
   zero, rollback, head única, divergência entre modelo e banco e a trava de
   RLS por tabela nova.

## 6. Status

PR aberto a partir da branch `claude/project-thread-773u4h` (rebaseada sobre a
`main`). Merge por fast-forward na `main` só com a suíte verde. Os itens 🔒
acima continuam com você e não fazem parte do merge.
