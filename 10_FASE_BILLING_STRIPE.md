# FASE 10 — Billing: Stripe + Quotas + Emails Transacionais

## PRÉ-REQUISITO
Fases 06-09 concluídas. Backend completo com RAG, Chat, Analytics, Widget.

## CONTEXTO DO PROJETO
Stack: FastAPI + SQLAlchemy 2.0 async + PostgreSQL + Stripe + Resend
Deploy: Railway

## REGRAS ABSOLUTAS
1. SEMPRE usar `from app.core.deps import get_current_user, get_db`
2. Rotas de webhook Stripe são PÚBLICAS e ASSINADAS — verificar `stripe.Webhook.construct_event`
3. Adicionar `/api/v1/billing` e `/api/v1/webhooks` em `_EXCLUDED_PREFIXES` apenas para webhook; demais rotas são autenticadas

---

## TAREFA

### 1. requirements.txt — Adicionar:
```
stripe==11.1.0
resend==2.3.0
```

---

### 2. app/core/config.py — Adicionar:
```python
# Stripe
STRIPE_SECRET_KEY: str = ""
STRIPE_PUBLISHABLE_KEY: str = ""
STRIPE_WEBHOOK_SECRET: str = ""

# Stripe Price IDs (configurar no Stripe Dashboard)
STRIPE_PRICE_FREE: str = ""
STRIPE_PRICE_STARTER: str = ""
STRIPE_PRICE_PRO: str = ""

# Resend (email)
RESEND_API_KEY: str = ""
EMAIL_FROM: str = "noreply@seudominio.com.br"

# Plan Limits
FREE_MONTHLY_MESSAGES: int = 100
STARTER_MONTHLY_MESSAGES: int = 1000
PRO_MONTHLY_MESSAGES: int = 10000
```

---

### 3. Criar `app/models/billing.py`
Modelos:
- `Plan(Base)` — campos: `id UUID PK`, `name str(100)`, `slug str(50) UNIQUE`, `price_brl Numeric(10,2)`, `stripe_price_id str(100)`, `monthly_message_limit int`, `is_active bool default True`
- `Subscription(Base, TenantBase)` — campos: `plan_id UUID FK(plans.id)`, `stripe_subscription_id str(200) nullable`, `stripe_customer_id str(200) nullable`, `status str(50) default 'trial'` (trial/active/past_due/canceled), `trial_ends_at DateTime nullable`, `current_period_end DateTime nullable`

Exportar em `app/models/__init__.py`.

Criar migration: `alembic revision --autogenerate -m "add_billing_tables"`

---

### 4. Criar script `backend/scripts/seed_plans.py`
Inserir 3 planos se não existirem:
- `free`: R$0, 100 mensagens/mês
- `starter`: R$97, 1000 mensagens/mês
- `pro`: R$297, 10000 mensagens/mês

Script usa `asyncio.run()` com sessão AsyncSession direta.
Adicionar chamada no startup: `app/main.py` no evento `startup_event`.

---

### 5. Criar `app/services/billing_service.py`
```python
"""
BillingService — Stripe Checkout + Subscription Management + Quota

Métodos:
  create_checkout_session(tenant_id, plan_slug, success_url, cancel_url) → str (checkout URL)
  create_customer_portal(tenant_id) → str (portal URL)
  get_current_subscription(tenant_id) → Subscription
  check_quota(tenant_id) → bool (True = dentro do limite)
  handle_webhook(payload, sig_header) → None
"""
import stripe
import resend
from app.core.config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY
resend.api_key = settings.RESEND_API_KEY
```

Implementar todos os métodos:

**create_checkout_session**: `stripe.checkout.Session.create()` com `mode="subscription"`, `line_items=[{"price": price_id, "quantity": 1}]`, `metadata={"tenant_id": str(tenant_id)}`.

**handle_webhook**: verificar assinatura com `stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)`. Tratar eventos:
- `checkout.session.completed` → atualizar Subscription para `active`, salvar `stripe_subscription_id` e `stripe_customer_id`
- `invoice.payment_succeeded` → atualizar `current_period_end`
- `invoice.payment_failed` → atualizar status para `past_due`
- `customer.subscription.deleted` → atualizar status para `canceled`

**check_quota**: contar `ChatMessage` do mês corrente para o tenant, comparar com limite do plano.

**send_email**: usar `resend.Emails.send()` para emails:
- Boas-vindas ao registrar
- Trial expirando (7 dias antes)
- Pagamento confirmado
- Conta bloqueada por quota

---

### 6. Criar `app/schemas/billing.py`
```python
from pydantic import BaseModel
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

class PlanResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    price_brl: Decimal
    monthly_message_limit: int
    class Config:
        from_attributes = True

class SubscriptionResponse(BaseModel):
    id: uuid.UUID
    plan: PlanResponse
    status: str
    trial_ends_at: Optional[datetime]
    current_period_end: Optional[datetime]
    class Config:
        from_attributes = True

class CheckoutRequest(BaseModel):
    plan_slug: str
    success_url: str
    cancel_url: str

class CheckoutResponse(BaseModel):
    checkout_url: str
```

---

### 7. Criar `app/api/v1/endpoints/billing.py`
```
GET  /api/v1/billing/plans                    → list[PlanResponse]      (PÚBLICO)
GET  /api/v1/billing/subscription             → SubscriptionResponse    (autenticado)
POST /api/v1/billing/checkout                 → CheckoutResponse         (autenticado)
POST /api/v1/billing/portal                   → {"portal_url": str}      (autenticado)
POST /api/v1/webhooks/stripe                  → {"status": "ok"}         (PÚBLICO)
```

Webhook endpoint recebe `Request` raw body (não JSON parsing):
```python
@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    service = BillingService(db)
    await service.handle_webhook(payload, sig_header)
    return {"status": "ok"}
```

---

### 8. Atualizar `app/core/middleware.py`
Adicionar em `_EXCLUDED_PREFIXES`:
```python
"/api/v1/billing/plans",
"/api/v1/webhooks",
```

---

### 9. Registrar em `app/api/v1/api.py`
```python
from app.api.v1.endpoints import auth, onboarding, knowledge, chat, analytics, widget, billing

api_router.include_router(billing.router, prefix="", tags=["Billing"])
```
(sem prefix pois os endpoints têm paths distintos: `/billing/*` e `/webhooks/*`)

---

### 10. Integrar verificação de quota no ChatService
Em `app/services/chat_service.py`, no início do `stream_response()`:
```python
# Import no topo:
from app.services.billing_service import BillingService

# No stream_response, antes de tudo:
billing_service = BillingService(self.db)
if not await billing_service.check_quota(tenant_id):
    yield "data: [QUOTA_EXCEEDED]\n\n"
    return
```

---

## VALIDAÇÃO FINAL
```bash
alembic upgrade head
python backend/scripts/seed_plans.py
python -c "from app.api.v1.endpoints.billing import router; print('✅ billing router OK')"
```
Testar `GET /api/v1/billing/plans` sem autenticação — deve retornar 3 planos.
