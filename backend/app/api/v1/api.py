"""
API v1 Router for FiscWise

Aggregates all v1 endpoint routers into a single API router.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, onboarding, health, operations, diagnostic, admin, portal, partners, company_documents, calculator, das, obligations, subscription, notifications, billing, account, whatsapp, fiscal_monitor, rag_fiscal, developer
from app.domain.invoices.api import router as invoices_router, issuers_router, profiles_router
from app.domain.ecac.api import router as ecac_router
from app.domain.certificates.api import router as certificates_router
from app.domain.powers_of_attorney.api import router as powers_of_attorney_router
from app.domain.fiscal_guides.api import router as fiscal_guides_router
from app.domain.fiscal_mailbox.api import router as fiscal_mailbox_router
from app.domain.monthly_closing.api import router as monthly_closing_router


# Create main API router for v1
api_router = APIRouter()

# Include authentication endpoints
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

# Include onboarding endpoints
api_router.include_router(
    onboarding.router,
    prefix="/onboarding",
    tags=["Onboarding"]
)

# Include health check endpoints
api_router.include_router(
    health.router,
    tags=["Health"]
)

# Include FiscWise operational MVP endpoints
api_router.include_router(
    operations.router,
    tags=["Operations"]
)

# Include diagnostic endpoints (for debugging)
api_router.include_router(
    diagnostic.router,
    prefix="/diagnostic",
    tags=["Diagnostic"]
)

# Include admin endpoints (emergency fixes)
api_router.include_router(
    admin.router,
    prefix="/admin",
    tags=["Admin"]
)

# Include client portal endpoints
api_router.include_router(
    portal.router,
    tags=["Client Portal"]
)

# Include company partners endpoints
api_router.include_router(
    partners.router,
    tags=["Company Partners"]
)

# Include company documents endpoints
api_router.include_router(
    company_documents.router,
    tags=["Company Documents"]
)

# Include calculator endpoints (Feature #7 — Calculadora Fiscal com IA)
api_router.include_router(
    calculator.router,
    prefix="/calculator",
    tags=["Calculator"]
)

# Include DAS endpoints
api_router.include_router(
    das.router,
    tags=["DAS Monthly Payments"]
)

# Include Obligation Engine endpoints
api_router.include_router(
    obligations.router,
    prefix="/obligations",
    tags=["Fiscal Obligations"]
)

# Include Subscription / Plan endpoints
api_router.include_router(
    subscription.router,
    prefix="/subscription",
    tags=["Subscription"]
)

# Include Notification endpoints
api_router.include_router(
    notifications.router,
    tags=["Notifications"]
)

# Include WhatsApp Inbox endpoints
api_router.include_router(
    whatsapp.router,
    tags=["WhatsApp Inbox"]
)

# Include Billing / Payment Gateway endpoints
api_router.include_router(
    billing.router,
    tags=["Billing"]
)

# Include Account / LGPD endpoints
api_router.include_router(
    account.router,
    tags=["Account / LGPD"]
)

# Include Fiscal Monitor endpoints
api_router.include_router(
    fiscal_monitor.router,
    tags=["Fiscal Monitor"]
)

# Include RAG Fiscal endpoints
api_router.include_router(
    rag_fiscal.router,
    tags=["RAG Fiscal"]
)

# Include Developer (API Keys + Webhooks) endpoints
api_router.include_router(
    developer.router,
    tags=["Developer"]
)

# ─── Fiscal Core Domains ──────────────────────────────────────────────────────

# Include Invoices (NFS-e) endpoints
api_router.include_router(invoices_router)
api_router.include_router(issuers_router)
api_router.include_router(profiles_router)

# Include e-CAC integration endpoints
api_router.include_router(ecac_router)

# Include Digital Certificates endpoints
api_router.include_router(certificates_router)

# Include Powers of Attorney (Procurações) endpoints
api_router.include_router(powers_of_attorney_router)

# Include Fiscal Guides (DAS, DARF, DAE, GPS, DCTFWeb) endpoints
api_router.include_router(fiscal_guides_router)

# Include Fiscal Mailbox (Caixa Postal Fiscal) endpoints
api_router.include_router(fiscal_mailbox_router)

# Include Monthly Closing (Fechamento Mensal) endpoints
api_router.include_router(monthly_closing_router)
