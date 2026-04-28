# ContaFlow — Architecture Blueprint

> **Version:** 1.0.0 (Greenfield)  
> **Status:** Foundation Phase (Phase 0)  
> **Last Updated:** 27/04/2026

---

## Executive Summary

**ContaFlow** is a production-grade B2B SaaS platform designed for the Brazilian accounting and financial services market. Built from the ground up with enterprise-grade architecture, security-first principles, and commercial polish.

This is a **complete rebuild** — zero legacy debt, zero technical compromises.

---

## Technology Stack

### Backend
- **Framework:** FastAPI 0.115+ (async-native, OpenAPI auto-generation)
- **ORM:** SQLAlchemy 2.0 (Async Core + ORM, type-safe queries)
- **Database:** PostgreSQL 16+ with pgvector extension
- **Authentication:** JWT (RS256) with refresh token rotation
- **Validation:** Pydantic v2 (strict mode, custom validators)
- **Migrations:** Alembic (async-compatible)
- **Task Queue:** Celery + Redis (background jobs, email, webhooks)
- **Cache:** Redis 7+ (distributed rate limiting, session store)
- **ASGI Server:** Uvicorn with Gunicorn process manager

### Frontend
- **Framework:** Next.js 14 (App Router, React Server Components)
- **Language:** TypeScript 5+ (strict mode)
- **Styling:** Tailwind CSS 3+ (utility-first, responsive design)
- **UI Components:** Shadcn/ui + Radix UI (accessible, composable)
- **State Management:** Zustand (lightweight, TypeScript-native)
- **Data Fetching:** TanStack Query (React Query v5, optimistic updates)
- **Forms:** React Hook Form + Zod (type-safe validation)
- **Charts:** Recharts (declarative, responsive)
- **Icons:** Lucide React (tree-shakeable)

### Infrastructure
- **Containerization:** Docker + Docker Compose (multi-stage builds)
- **Orchestration:** Kubernetes (Helm charts for production)
- **IaC:** Terraform (AWS/GCP/Azure agnostic)
- **CI/CD:** GitHub Actions (automated testing, security scanning, deployment)
- **Monitoring:** Prometheus + Grafana + OpenTelemetry
- **Logging:** Loki + Grafana (structured JSON logs)
- **Secrets:** HashiCorp Vault / AWS Secrets Manager

### AI/ML (Future Phase)
- **Embeddings:** Voyage AI / OpenAI Ada-002
- **LLM:** Anthropic Claude 3.5 / OpenAI GPT-4
- **Vector Store:** pgvector (PostgreSQL extension)
- **RAG Framework:** LangChain / LlamaIndex

---

## Core Architectural Principles

### 1. Clean Architecture (Hexagonal)
```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                       │
│  FastAPI Routers · Pydantic Schemas · Middleware Stack     │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              APPLICATION LAYER                        │  │
│  │  Services · Use Cases · Business Logic                │  │
│  │                                                       │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │           DOMAIN LAYER                          │  │  │
│  │  │  Entities · Value Objects · Domain Events       │  │  │
│  │  │  Business Rules · Invariants                    │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  │                                                       │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │        INFRASTRUCTURE LAYER                     │  │  │
│  │  │  SQLAlchemy Models · Redis Client · SMTP        │  │  │
│  │  │  External APIs · File Storage                   │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Key Benefits:**
- **Testability:** Domain logic isolated from infrastructure
- **Flexibility:** Swap databases, frameworks, or external services without touching business logic
- **Maintainability:** Clear boundaries, single responsibility per layer

### 2. Multi-Tenancy Strategy

**Approach:** Hybrid (Shared Database + Row-Level Security)

```
┌─────────────────────────────────────────────────────────────┐
│                    Tenant Isolation                         │
│                                                             │
│  Layer 1: Application (TenantMiddleware)                    │
│  → Extracts X-Tenant-ID header                              │
│  → Validates UUID format                                    │
│  → Injects into request.state.tenant_id                     │
│                                                             │
│  Layer 2: Service Layer                                     │
│  → All queries filter by tenant_id                          │
│  → tenant_id sourced from request.state (not user input)    │
│                                                             │
│  Layer 3: Database (PostgreSQL RLS)                         │
│  → Row-Level Security policies enforce tenant_id match      │
│  → Even with application bugs, DB blocks cross-tenant access│
│                                                             │
│  Layer 4: Audit Trail                                       │
│  → All tenant-scoped operations logged to audit_logs        │
│  → Immutable append-only log for compliance                 │
└─────────────────────────────────────────────────────────────┘
```

### 3. Security-First Design

**OWASP Top 10 Mitigations:**
- **A01 (Broken Access Control):** RBAC + RLS + JWT scopes
- **A02 (Cryptographic Failures):** TLS 1.3, bcrypt (cost 12), RS256 JWT
- **A03 (Injection):** Parameterized queries, Pydantic validation, CSP headers
- **A04 (Insecure Design):** Threat modeling, security reviews, principle of least privilege
- **A05 (Security Misconfiguration):** Hardened Docker images, no default credentials
- **A06 (Vulnerable Components):** Automated dependency scanning (Dependabot, Trivy)
- **A07 (Auth Failures):** MFA support, rate limiting, account lockout
- **A08 (Data Integrity):** HMAC signatures, audit logs, immutable events
- **A09 (Logging Failures):** Structured logging, centralized aggregation, alerting
- **A10 (SSRF):** Allowlist external domains, network segmentation

**Compliance Readiness:**
- **LGPD (Brazil):** Data minimization, consent management, right to erasure
- **GDPR (EU):** Data portability, privacy by design, DPO contact
- **SOC 2 Type II:** Access controls, encryption, change management
- **PCI-DSS (if handling payments):** Tokenization, no card storage, network segmentation

### 4. Observability-First

**Three Pillars:**

```
┌─────────────────────────────────────────────────────────────┐
│  METRICS (Prometheus)                                       │
│  • Request rate, latency (p50/p95/p99), error rate          │
│  • Database connection pool stats                           │
│  • Cache hit/miss ratio                                     │
│  • Business metrics (signups, active tenants, MRR)          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  LOGS (Loki + Loguru)                                       │
│  • Structured JSON format                                   │
│  • trace_id, span_id, tenant_id, user_id in every log       │
│  • Centralized aggregation with retention policies          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  TRACES (OpenTelemetry + Jaeger)                            │
│  • Distributed tracing across services                      │
│  • Database query spans                                     │
│  • External API call spans                                  │
└─────────────────────────────────────────────────────────────┘
```

**Health Checks:**
- `/health` — Liveness probe (app is running)
- `/health/ready` — Readiness probe (DB + Redis connectivity)
- `/health/metrics` — Prometheus metrics endpoint

### 5. API Design Standards

**RESTful Conventions:**
- `GET /api/v1/resources` — List (paginated)
- `GET /api/v1/resources/{id}` — Retrieve single
- `POST /api/v1/resources` — Create
- `PATCH /api/v1/resources/{id}` — Partial update
- `DELETE /api/v1/resources/{id}` — Soft delete (set `is_active=false`)

**Response Format:**
```json
{
  "data": { ... },
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 150
  },
  "links": {
    "self": "/api/v1/resources?page=1",
    "next": "/api/v1/resources?page=2",
    "prev": null
  }
}
```

**Error Format:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ],
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

---

## Project Structure

```
ContaFlow/
├── backend/                      # FastAPI application
│   ├── app/
│   │   ├── main.py               # FastAPI app initialization
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── router.py     # API router aggregator
│   │   │       └── endpoints/    # Endpoint modules
│   │   ├── core/
│   │   │   ├── config.py         # Settings (Pydantic BaseSettings)
│   │   │   ├── security.py       # JWT, password hashing
│   │   │   ├── middleware.py     # Custom middleware
│   │   │   └── dependencies.py   # Reusable dependencies
│   │   ├── domain/               # Domain layer (business logic)
│   │   │   ├── entities/         # Domain entities
│   │   │   ├── value_objects/    # Value objects
│   │   │   └── events/           # Domain events
│   │   ├── services/             # Application services (use cases)
│   │   ├── infrastructure/       # Infrastructure layer
│   │   │   ├── database/         # SQLAlchemy models, session
│   │   │   ├── cache/            # Redis client
│   │   │   ├── email/            # SMTP client
│   │   │   └── storage/          # File storage (S3, local)
│   │   ├── schemas/              # Pydantic schemas (API contracts)
│   │   └── utils/                # Shared utilities
│   ├── alembic/                  # Database migrations
│   ├── tests/                    # Test suite
│   │   ├── unit/                 # Unit tests
│   │   ├── integration/          # Integration tests
│   │   └── e2e/                  # End-to-end tests
│   ├── scripts/                  # Utility scripts
│   ├── requirements/             # Dependency files
│   │   ├── base.txt              # Core dependencies
│   │   ├── dev.txt               # Development tools
│   │   └── prod.txt              # Production-only deps
│   ├── Dockerfile                # Multi-stage Docker build
│   ├── docker-compose.yml        # Local development stack
│   ├── pyproject.toml            # Python project config
│   └── .env.example              # Environment template
│
├── frontend/                     # Next.js application
│   ├── src/
│   │   ├── app/                  # App Router (Next.js 14)
│   │   │   ├── (auth)/           # Auth route group
│   │   │   ├── (dashboard)/      # Dashboard route group
│   │   │   ├── layout.tsx        # Root layout
│   │   │   └── page.tsx          # Home page
│   │   ├── components/           # React components
│   │   │   ├── ui/               # Shadcn/ui components
│   │   │   ├── forms/            # Form components
│   │   │   └── layouts/          # Layout components
│   │   ├── lib/                  # Utilities
│   │   │   ├── api.ts            # API client (axios/fetch)
│   │   │   ├── auth.ts           # Auth utilities
│   │   │   └── utils.ts          # Shared utilities
│   │   ├── hooks/                # Custom React hooks
│   │   ├── stores/               # Zustand stores
│   │   ├── types/                # TypeScript types
│   │   └── styles/               # Global styles
│   ├── public/                   # Static assets
│   ├── tests/                    # Frontend tests
│   ├── .env.local.example        # Environment template
│   ├── next.config.js            # Next.js configuration
│   ├── tailwind.config.ts        # Tailwind configuration
│   ├── tsconfig.json             # TypeScript configuration
│   └── package.json              # Node dependencies
│
├── infra/                        # Infrastructure as Code
│   ├── terraform/                # Terraform modules
│   │   ├── modules/              # Reusable modules
│   │   ├── environments/         # Environment configs
│   │   │   ├── dev/
│   │   │   ├── staging/
│   │   │   └── production/
│   │   └── main.tf               # Root module
│   ├── kubernetes/               # K8s manifests
│   │   ├── base/                 # Base configs
│   │   └── overlays/             # Kustomize overlays
│   ├── helm/                     # Helm charts
│   └── docker-compose/           # Compose files
│       ├── dev.yml
│       ├── staging.yml
│       └── production.yml
│
└── docs/                         # Documentation
    ├── 00-architecture.md        # This file
    ├── 01-setup.md               # Development setup guide
    ├── 02-api-reference.md       # API documentation
    ├── 03-deployment.md          # Deployment guide
    ├── 04-security.md            # Security guidelines
    └── 05-contributing.md        # Contribution guidelines
```

---

## Development Workflow

### Phase 0: Foundation (Current)
- [x] Create project structure
- [x] Initialize architecture documentation
- [ ] Set up Git repository + GitHub
- [ ] Configure pre-commit hooks (black, ruff, mypy, prettier)
- [ ] Initialize backend (FastAPI + SQLAlchemy)
- [ ] Initialize frontend (Next.js + TypeScript)
- [ ] Set up Docker Compose for local development
- [ ] Configure CI/CD pipeline (GitHub Actions)

### Phase 1: Core Backend (Weeks 1-2)
- [ ] Database schema design
- [ ] Authentication system (JWT + refresh tokens)
- [ ] Multi-tenancy middleware
- [ ] RBAC implementation
- [ ] User management endpoints
- [ ] Health checks + metrics
- [ ] Unit + integration tests (80%+ coverage)

### Phase 2: Core Frontend (Weeks 3-4)
- [ ] Authentication UI (login, register, password reset)
- [ ] Dashboard layout
- [ ] User management UI
- [ ] Settings pages
- [ ] Responsive design (mobile-first)
- [ ] E2E tests (Playwright)

### Phase 3: Business Features (Weeks 5-8)
- [ ] Define domain-specific features (TBD with Executive Director)
- [ ] Implement business logic
- [ ] Build corresponding UI
- [ ] Integration with external APIs (if needed)

### Phase 4: Polish & Launch (Weeks 9-10)
- [ ] Performance optimization
- [ ] Security audit
- [ ] Load testing
- [ ] Documentation finalization
- [ ] Production deployment
- [ ] Monitoring setup

---

## Design Decisions & Trade-offs

### Why FastAPI over Django?
- **Performance:** Async-native, handles high concurrency with fewer resources
- **Modern:** Type hints, automatic OpenAPI docs, Pydantic validation
- **Flexibility:** Microservices-ready, no monolithic ORM lock-in

### Why Next.js over Create React App?
- **SSR/SSG:** Better SEO, faster initial load
- **App Router:** React Server Components, streaming, suspense
- **DX:** Built-in routing, API routes, image optimization, TypeScript support

### Why PostgreSQL over MongoDB?
- **ACID guarantees:** Critical for financial/accounting data
- **Relational integrity:** Foreign keys, constraints, transactions
- **pgvector:** Native vector search for future AI features
- **Mature ecosystem:** Battle-tested, excellent tooling

### Why Monorepo vs Separate Repos?
- **Monorepo (Current Choice):** Easier to maintain consistency, shared types, atomic commits
- **Trade-off:** Larger repo size, requires good tooling (Nx, Turborepo in future)
- **Alternative:** Split into `contaflow-api` + `contaflow-web` if teams scale independently

---

## Non-Functional Requirements

### Performance
- **API Response Time:** p95 < 200ms, p99 < 500ms
- **Frontend FCP:** < 1.5s (First Contentful Paint)
- **Database Queries:** < 50ms for 95% of queries
- **Concurrent Users:** Support 1000+ concurrent users per instance

### Scalability
- **Horizontal Scaling:** Stateless API servers (scale via load balancer)
- **Database:** Read replicas for analytics, connection pooling
- **Cache:** Redis for session store, rate limiting, hot data

### Reliability
- **Uptime SLA:** 99.9% (43 minutes downtime/month)
- **RTO (Recovery Time Objective):** < 1 hour
- **RPO (Recovery Point Objective):** < 5 minutes (DB backups every 5 min)

### Security
- **Authentication:** MFA support, OAuth 2.0 / OIDC
- **Authorization:** RBAC with fine-grained permissions
- **Data Encryption:** TLS 1.3 in transit, AES-256 at rest
- **Secrets Management:** Never commit secrets, use Vault/Secrets Manager

---

## Next Steps

Awaiting Executive Director confirmation to proceed with:

1. **Git Repository Initialization**
   - Initialize Git repo
   - Create `.gitignore` for Python + Node.js
   - Set up GitHub repository
   - Configure branch protection rules

2. **Backend Scaffolding**
   - Initialize FastAPI project structure
   - Set up SQLAlchemy + Alembic
   - Configure Pydantic settings
   - Create Docker Compose for local dev (PostgreSQL + Redis)

3. **Frontend Scaffolding**
   - Initialize Next.js 14 with TypeScript
   - Configure Tailwind CSS + Shadcn/ui
   - Set up ESLint + Prettier
   - Create base layout components

4. **CI/CD Pipeline**
   - GitHub Actions workflow for backend (lint, test, build)
   - GitHub Actions workflow for frontend (lint, test, build)
   - Docker image build + push to registry
   - Automated deployment to staging environment

---

**Status:** ✅ Foundation structure created. Awaiting Executive approval to proceed.

**THE ARCHITECT — Omega v2**  
*Building what endures.*
