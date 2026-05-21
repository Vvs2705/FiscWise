# FiscWise

> Production-grade B2B SaaS platform for Brazilian accounting and financial services

**Version:** 1.0.0  
**Status:** Phase 1 - Core Backend & Local Infrastructure

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git

### 1. Clone & Setup

```bash
cd "C:\Users\VINICIUS\Videos\MEUS PROJETOS\ContaFlow"
```

### 2. Start Infrastructure

```bash
# Start PostgreSQL (with pgvector) and Redis
docker-compose up -d

# Verify containers are running
docker-compose ps
```

### 3. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
copy .env.example .env

# Run the API
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Verify Installation

- **API Health Check:** http://localhost:8000/health
- **API Documentation:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

Expected response from `/health`:
```json
{
  "status": "FiscWise API Online"
}
```

---

## 📁 Project Structure

```
FiscWise/
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── main.py      # Application entry point
│   │   └── __init__.py
│   ├── alembic/         # Database migrations
│   ├── requirements.txt # Python dependencies
│   ├── alembic.ini      # Alembic configuration
│   └── .env.example     # Environment template
├── frontend/            # Next.js application (future)
├── infra/               # Infrastructure as Code
│   └── postgres/
│       └── init.sql     # PostgreSQL initialization
├── docs/                # Documentation
│   └── 00-architecture.md
├── docker-compose.yml   # Local development stack
└── README.md           # This file
```

---

## 🛠️ Technology Stack

### Backend
- **FastAPI** 0.115.0 - Modern async web framework
- **SQLAlchemy** 2.0.35 - Async ORM
- **PostgreSQL** 16 with **pgvector** - Vector database for AI/ML
- **Redis** 7 - Cache & rate limiting
- **Alembic** 1.13.3 - Database migrations
- **Pydantic** 2.9.2 - Data validation

### Infrastructure
- **Docker** - Containerization
- **Docker Compose** - Local orchestration

---

## 🗄️ Database

### PostgreSQL Extensions Enabled

- `uuid-ossp` - UUID generation
- `pgcrypto` - Cryptographic functions
- `vector` - pgvector for embeddings

### Connection Details (Development)

- **Host:** localhost
- **Port:** 5432
- **Database:** contaflow_db
- **User:** contaflow
- **Password:** contaflow_dev_2026

### Redis Connection (Development)

- **Host:** localhost
- **Port:** 6379
- **Password:** contaflow_redis_2026

---

## 📝 Available Commands

### Docker

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f

# Rebuild containers
docker-compose up -d --build
```

### Alembic (Database Migrations)

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# View current revision
alembic current

# View migration history
alembic history --verbose
```

### Development

```bash
# Run API with hot-reload
python -m uvicorn app.main:app --reload

# Run tests (when implemented)
pytest

# Check code coverage
pytest --cov=app tests/
```

---

## 🔐 Environment Variables

Copy `.env.example` to `.env` and configure:

```env
# Application
APP_NAME=FiscWise
DEBUG=True
ENVIRONMENT=development

# Database
DATABASE_URL=postgresql+asyncpg://contaflow:contaflow_dev_2026@localhost:5432/contaflow_db

# Redis
REDIS_URL=redis://:contaflow_redis_2026@localhost:6379/0

# JWT (generate with: python -c "import secrets; print(secrets.token_hex(64))")
JWT_SECRET_KEY=your-secret-key-here

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

---

## 📚 Documentation

- [Architecture Blueprint](docs/00-architecture.md) - System design and technical decisions

---

## 🎯 Development Roadmap

### Phase 0: Foundation ✅
- [x] Project structure
- [x] Docker Compose setup
- [x] FastAPI base application
- [x] Alembic configuration
- [x] Documentation

### Phase 1: Core Backend (Current)
- [ ] Database models (User, Tenant, etc.)
- [ ] Authentication system (JWT)
- [ ] Multi-tenancy middleware
- [ ] RBAC implementation
- [ ] User management endpoints
- [ ] Health checks with DB connectivity
- [ ] Unit & integration tests

### Phase 2: Core Frontend
- [ ] Next.js 14 setup
- [ ] Authentication UI
- [ ] Dashboard layout
- [ ] User management UI

### Phase 3: Business Features
- [ ] Domain-specific features (TBD)

### Phase 4: Polish & Launch
- [ ] Performance optimization
- [ ] Security audit
- [ ] Production deployment

---

## 🤝 Contributing

This is a private project. For internal team members:

1. Create a feature branch
2. Make your changes
3. Write/update tests
4. Submit for review

---

## 📄 License

Proprietary - All rights reserved

---

**Built by THE ARCHITECT — Omega v2**  
*Building what endures.*
