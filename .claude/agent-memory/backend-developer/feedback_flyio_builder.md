---
name: feedback-flyio-builder-config
description: Fly.io fly.toml builder config — never use builder = "docker", only specify dockerfile path
metadata:
  type: feedback
---

Never use `builder = "docker"` in fly.toml [build] section alongside `dockerfile`. The string "docker" activates the Heroku Cloud Native Buildpack builder, causing the "more than one build configuration found" conflict.

**Why:** Fly.io treats `builder = "docker"` as a buildpack selector (Heroku CNB), not as "use Docker". This conflicts with an explicit `dockerfile` path in the same block, producing the warning and the `unauthorized` build failure.

**How to apply:** In fly.toml, to use a Dockerfile, only specify `dockerfile = "./path/to/Dockerfile"` in `[build]` — no `builder` field needed. If no builder field is present, Fly.io defaults to Dockerfile if one is specified.
