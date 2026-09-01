# CLAUDE.md — FiscWise

## Regra permanente — centralizar, nunca espalhar

- **JAMAIS criar pastas novas.** Tudo vai na estrutura que ja existe.
  So criar pasta nova em necessidade REAL e clara.
- **Trabalhar sempre na pasta central do projeto** — a raiz do repositorio, na
  branch `main`. Nada de copias, clones paralelos ou worktrees aninhados
  (`.claude/worktrees/...`, `.gemini/.../worktrees/...`).
- Terminou uma tarefa? O resultado volta para `main`, na pasta central.

### Git
- Trabalho so entra em `main` por **fast-forward** (`git merge --ff-only`).
  Se `main` divergiu, parar e perguntar — nao forcar.
- Branch ou worktree so e apagado depois de confirmado que esta 100% contido
  em `main` (`git merge-base --is-ancestor`).
- **Nunca** reescrever historico: proibido `git push --force`, `git filter-branch`,
  `git reflog expire`, `git gc --prune`, apagar `.git`.

### Higiene
- Regeneraveis podem ser apagados a vontade: `.next`, `dist`, `build`, `out`,
  `target`, `coverage`, `__pycache__`, `.pytest_cache`, `.turbo`,
  `*.tsbuildinfo`, `*.log`, `*.tmp`.
- Arquivo de trabalho — mesmo nao rastreado — nunca e apagado sem commit antes.
