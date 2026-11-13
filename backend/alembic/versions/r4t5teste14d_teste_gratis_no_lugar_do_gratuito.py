"""Teste grátis de 14 dias no lugar do plano Gratuito permanente.

Decisão do dono em 13/11/2026: o plano Gratuito deixa de existir. Todo
escritório novo começa com 14 dias de teste do Premium (sem cartão) e, sem
assinatura, a conta fica só leitura (app/core/plan_access.acesso_expirado).

Esta migração cuida de quem já existe:

1. Escritório no Gratuito sem linha em tenant_subscriptions ganha um teste de
   14 dias do Premium, contado a partir de agora (aviso justo: ninguém fica só
   leitura no dia da mudança).
2. Escritório no Gratuito com assinatura "trialing" sem data de fim (criada ao
   abrir um checkout que não foi pago) ganha a mesma data de fim e o Premium.
3. O plano "free" fica inativo (some da lista e o cadastro não o aceita mais).
   A linha continua no banco: os limites dele seguem valendo para contas
   vencidas.

Escritórios com plano pago gravado pelo admin e sem assinatura não mudam.

Revision ID: r4t5teste14d
Revises: q3t1wt72tour
Create Date: 2026-11-13
"""

from alembic import op

revision = "r4t5teste14d"
down_revision = "q3t1wt72tour"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 2) checkout aberto e não pago: "trialing" sem data de fim.
    op.execute(
        """
        UPDATE tenant_subscriptions s
           SET trial_ends_at = now() + interval '14 days',
               plan_id = p.id,
               amount = p.price_monthly,
               updated_at = now()
          FROM tenants t, plans p
         WHERE t.id = s.tenant_id
           AND p.slug = 'premium'
           AND s.status = 'trialing'
           AND s.trial_ends_at IS NULL
           AND coalesce(t.plan_slug, 'free') = 'free'
        """
    )
    # 1) Gratuito sem assinatura: cria o teste.
    op.execute(
        """
        INSERT INTO tenant_subscriptions
            (id, tenant_id, plan_id, billing_provider, status, trial_ends_at,
             grace_period_days, amount, currency, billing_cycle, created_at, updated_at)
        SELECT gen_random_uuid(), t.id, p.id, 'mercadopago', 'trialing',
               now() + interval '14 days', 3, p.price_monthly, 'BRL', 'mensal', now(), now()
          FROM tenants t
          JOIN plans p ON p.slug = 'premium'
         WHERE coalesce(t.plan_slug, 'free') = 'free'
           AND NOT EXISTS (SELECT 1 FROM tenant_subscriptions s WHERE s.tenant_id = t.id)
        """
    )
    # O plano efetivo do teste vem de tenants.plan_slug (plan_access).
    op.execute(
        """
        UPDATE tenants t
           SET plan_slug = 'premium'
         WHERE coalesce(t.plan_slug, 'free') = 'free'
           AND EXISTS (
               SELECT 1 FROM tenant_subscriptions s
                WHERE s.tenant_id = t.id AND s.status = 'trialing'
                  AND s.trial_ends_at > now()
           )
        """
    )
    # 3) Gratuito fora da lista de planos.
    op.execute("UPDATE plans SET active = false WHERE slug = 'free'")


def downgrade() -> None:
    # Reativa o Gratuito. Os testes criados acima são mantidos de propósito:
    # apagá-los tiraria o acesso de quem já está usando.
    op.execute("UPDATE plans SET active = true WHERE slug = 'free'")
