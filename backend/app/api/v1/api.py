"""
API v1 Router for FiscWise

Aggregates all v1 endpoint routers into a single API router.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, onboarding, health, operations, diagnostic, admin, portal, partners, company_documents, calculator, das, obligations, subscription, notifications, billing, account, whatsapp, fiscal_monitor, rag_fiscal, developer, invoices, ecac, guias, fiscal_mailbox, monthly_closing, focus, reports


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

# Include Invoices endpoints
api_router.include_router(
    invoices.router,
    tags=["Invoices"]
)

# Include e-CAC endpoints
api_router.include_router(
    ecac.router,
    tags=["e-CAC"]
)

# Include Guias endpoints
api_router.include_router(
    guias.router,
    tags=["Guias de Impostos"]
)

# Include Fiscal Mailbox (e-CAC / DTE) endpoints
api_router.include_router(
    fiscal_mailbox.router,
    tags=["Fiscal Mailbox"]
)

# Include Monthly Closing endpoints
api_router.include_router(
    monthly_closing.router,
    tags=["Monthly Closing"]
)

# Include Daily Focus aggregator endpoint
api_router.include_router(
    focus.router,
    tags=["Daily Focus"]
)

# Include Reports (aggregations) endpoints
api_router.include_router(
    reports.router,
    tags=["Reports"]
)



