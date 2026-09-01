# 💰 FISCWISE — SETUP DE SESSÃO (SaaS fiscal/contábil — EM PRODUÇÃO)

> **Instrução para o agente:** Este projeto está EM PRODUÇÃO. Toda mudança exige cautela: nada de migrations destrutivas, nada de deploy sem testes passando. Execute as fases em ordem, com verificação em loop fechado. Pré-requisito: `00_VSTACK_BASE_SETUP.md` já aplicado (Context7, Ponytail, Superpowers ativos).

## Contexto
- Produto: FiscWise (ex-ContaFlow) — SaaS de contabilidade/fiscal, live em produção
- Stack: FastAPI + PostgreSQL / Next.js + TypeScript + Tailwind
- Sensibilidade: dados fiscais e financeiros de terceiros → LGPD se aplica

## FASE 1 — Diagnóstico
1. Leia o repositório: estrutura, `CLAUDE.md` (crie se não existir), requirements, migrations pendentes.
2. Rode a suíte de testes e registre o baseline (quantos passam/falham).
3. `/ponytail-audit` para mapear over-engineering — apenas RELATÓRIO nesta fase, sem alterar código.

✅ Verificar: baseline de testes documentado no CLAUDE.md.

## FASE 2 — Stack fiscal brasileira (núcleo do produto)
Instale e integre as bibliotecas do ecossistema fiscal open-source:

```bash
pip install nfelib          # bindings XML: NF-e, NFS-e nacional, CT-e, MDF-e (gerados dos XSDs da Fazenda)
pip install erpbrasil.edoc  # transmissão para SEFAZ
pip install brazilfiscalreport  # geração de DANFE em PDF
```

Notas de integração:
- `nfelib` cobre parsing E geração com validação dos XSDs — priorize-a sobre parsing manual de XML.
- Para NFS-e municipal (padrão Abrasf/Ginfes/Betha), avalie `PyNFe` como complemento.
- Certificados A1 (.pfx): NUNCA no repositório. Carregar via variável de ambiente/secret manager.
- Crie um módulo `app/fiscal/` isolando essas dependências atrás de uma interface própria (facilita trocar de lib).

✅ Verificar: escrever teste que gera uma NF-e de exemplo com nfelib, serializa para XML e re-parseia sem erro.

## FASE 3 — MCP de banco (somente leitura)
Conecte um MCP Postgres para o agente inspecionar schema e dados SEM risco:

1. Crie no Postgres uma role dedicada `mcp_readonly` com apenas CONNECT + USAGE + SELECT (nunca superuser).
2. Adicione o servidor (escopo project, vai para `.mcp.json`):
```bash
claude mcp add --scope project postgres -- npx @henkey/postgres-mcp-server --connection-string "postgresql://mcp_readonly:SENHA@host:5432/fiscwise"
```
   (No Windows, se falhar, use `claude mcp add-json` com `"command": "cmd", "args": ["/c", "npx", ...]`.)
3. Adicione `.mcp.json` ao `.gitignore` SE contiver credenciais; prefira connection string via env.

✅ Verificar: pedir ao agente para listar as tabelas do schema e descrever a tabela principal.

## FASE 4 — Segurança e CI
1. Adicione o workflow `anthropics/claude-code-security-review` em `.github/workflows/security-review.yml` (siga o README oficial do repo).
2. Confirme que o CI roda testes + lint em cada PR.

✅ Verificar: abrir um PR de teste e confirmar que a action executa.

## FASE 5 — Registrar no CLAUDE.md
Acrescente ao `CLAUDE.md` do projeto:
- Seção "Tooling": MCPs ativos, libs fiscais e o módulo `app/fiscal/`
- Seção "Regras de produção": sem migration destrutiva, testes obrigatórios antes de deploy, certificados fora do repo
- Convenção: consultar Context7 antes de usar APIs de libs fiscais (mudam com frequência)

## Checklist final
- [ ] Baseline de testes documentado
- [ ] nfelib + erpbrasil.edoc + brazilfiscalreport instalados e testados
- [ ] MCP Postgres read-only funcionando
- [ ] Security review action ativa
- [ ] CLAUDE.md atualizado
