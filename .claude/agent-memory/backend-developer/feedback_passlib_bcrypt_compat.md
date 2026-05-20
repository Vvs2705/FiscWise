---
name: feedback-passlib-bcrypt-compat
description: passlib 1.7.x quebra com bcrypt >= 4.0 — usar bcrypt diretamente em security.py
metadata:
  type: feedback
---

Nunca usar `passlib` com `bcrypt >= 4.0`. A passlib 1.7.x lê `bcrypt.__about__.__version__`
que foi removido no bcrypt 4.0. Isso causa um `ValueError` enganoso ("password cannot be
longer than 72 bytes") que mascara o erro real de compatibilidade.

**Why:** O Fly.io instala a versão mais recente do bcrypt (5.x) — a passlib falha silenciosamente
com uma exceção que parece ser de validação de senha mas é na verdade incompatibilidade de versão.
O 500 no endpoint `/api/v1/onboarding/register` era causado por isso.

**How to apply:** Em `app/core/security.py`, chamar `bcrypt.hashpw()` e `bcrypt.checkpw()`
diretamente em vez de usar `CryptContext` da passlib. Ver implementação atual do arquivo.
Remover `passlib[bcrypt]` de requirements.txt e usar apenas `bcrypt>=4.0.0`.

Relacionado: [[feedback_pydantic_v2_startup_crash]]
