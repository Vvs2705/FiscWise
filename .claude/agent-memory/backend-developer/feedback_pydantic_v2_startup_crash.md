---
name: feedback_pydantic_v2_startup_crash
description: Never raise ValueError in Pydantic Settings validators at import time — it crashes uvicorn before the health endpoint can respond, causing 502 Bad Gateway on Fly.io
metadata:
  type: feedback
---

Never raise `ValueError` (or any exception) inside a `@field_validator` on `BaseSettings` for missing/invalid secrets that should surface at runtime rather than boot.

**Why:** On Fly.io, `settings = Settings()` executes at module import time.  If a validator raises, the Python process exits before uvicorn binds to the port.  Fly.io's health-check then gets no response and marks the machine as failed → 502 Bad Gateway on all requests.  The correct pattern is to return a safe default (empty string, False, etc.) and emit a `CRITICAL` log; the startup_event in `main.py` surfaces the missing secret with a human-readable message.

**How to apply:**
- For `DATABASE_URL`, `JWT_SECRET_KEY`, `DEBUG` and similar env vars that are required only at runtime (not at import): use log + return-safe-value, never raise.
- Exception: it is acceptable to raise if the value is present but provably insecure (e.g. JWT_SECRET_KEY contains "dev_secret" in production) — this is a deliberate fail-fast for security.
- Field declaration order in `BaseSettings` matters in Pydantic v2: `ENVIRONMENT` must appear as the first field because `info.data` is populated in declaration order, and later validators read it via `info.data.get("ENVIRONMENT")`.
- Default for `DEBUG` must be `False` (not `True`) so that a missing `DEBUG` env var in production never triggers the validator's production-guard path.
