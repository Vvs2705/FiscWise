# Ata do Conselho — PR #131: redesign do frontend (login, menu agrupado, painel)

- **Data:** 2026-11-22
- **Modo:** B
- **Projeto / repositório:** Vvs2705/FiscWise · **PR:** #131
- **Pedido literal:** deixar o sistema bonito, porém funcional e útil; revisar ordem dos textos, login e organização da informação.
- **Estado:** APROVADA

## 1. Triagem
SEGUIR: só apresentação no `frontend/src`; nenhuma rota removida; dados de exemplo no login rotulados (decisão do dono de
2026-11-22, registrada em `docs/audit/SISTEMA_DE_DESIGN.md`).

## 2–4. Pareceres (independentes)
- Técnico: Sidebar com as mesmas 23 rotas e os mesmos controles de acesso (`role !== 'client'`, `planLacksFeature`); login com as
  mesmas funções (senha, Google, 2FA); painel sem chamada de API nova; CI toda verde no head.
- Produto: painel abre com "Hoje" e resumo dos dados reais; menu em 6 grupos sem perder rota; dado fictício do login rotulado.
  Não bloqueantes: com `isError` o topo diz "Nada urgente agora" (falsa tranquilidade); nomes "Hoje"/"Painel"/"Foco de hoje" a alinhar.
- Produtor: escopo bate com o pedido; Definição de Pronto cumprida (lint, tsc, vitest 162/162, build, axe); descrição conservadora.

## 6. Votos (Modo B — revisão do PR)
Commit revisado: 6c921787c31bf21ba8f7d8cc9fe90bcac3cd5a44

| Diretor | Voto | Motivo / evidência |
|---|---|---|
| diretor-tecnico | APROVA | rotas e permissões iguais; mesmas chamadas de auth; CI verde (lint, tsc, vitest, build, axe, e2e, Semgrep, backend) |
| diretor-produto | APROVA | hierarquia "o que fazer agora"; 6 grupos sem perder rota; exemplo rotulado |
| produtor | APROVA | escopo do pedido entregue; validação rodada e pendências declaradas |

**Veredito final:** APROVADO
