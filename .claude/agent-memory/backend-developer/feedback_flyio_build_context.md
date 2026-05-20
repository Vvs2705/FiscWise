---
name: feedback-flyio-build-context
description: Fly.io build context is project root when fly.toml is at root — Dockerfile COPY paths must use backend/ prefix
metadata:
  type: feedback
---

When fly.toml is at the project root and `dockerfile = "./backend/Dockerfile"`, the Docker build context is the **project root**, not the `backend/` directory. All COPY instructions in the Dockerfile must use paths relative to the project root.

**Why:** Docker build context = directory where flyctl runs (where fly.toml lives). The Dockerfile is just instructions; paths in COPY are resolved against the context, not the Dockerfile's own directory.

**How to apply:** In ContaFlow's backend/Dockerfile, use `COPY backend/requirements.txt .` and `COPY backend/ .` rather than `COPY requirements.txt .` and `COPY . .`.
