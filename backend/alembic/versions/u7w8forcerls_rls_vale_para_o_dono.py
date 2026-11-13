"""RLS passa a valer também para o dono das tabelas (FORCE ROW LEVEL SECURITY).

Achado em 13/11/2026 (auditoria do catálogo de produção): a API conecta como
`fiscwise_app`, que NÃO é superusuário nem tem BYPASSRLS, mas é DONO das 49
tabelas. Sem FORCE, o PostgreSQL não aplica RLS ao dono — as policies
`tenant_isolation` existiam e não valiam para a aplicação.

O que muda:

1. Toda policy `tenant_isolation` ganha a cláusula `OR current_app_tenant_id()
   IS NULL` (já era assim em users, tenants, tenant_subscriptions,
   portal_magic_tokens, client_portal_invites e retention_offers). Sem escritório
   no contexto = rotina do sistema (agendador, webhooks, migrações, backup,
   login): continua vendo tudo, como hoje. Com escritório no contexto (toda
   requisição autenticada: deps._set_current_tenant_context), o banco só
   mostra e só aceita gravar linhas daquele escritório — mesmo se um filtro no
   código falhar.
2. FORCE ROW LEVEL SECURITY em todas as tabelas com RLS ligada.

O backup (`pg_dump`) passa a usar `--enable-row-security` (db-backup.yml):
com FORCE, o pg_dump padrão (row_security=off) recusaria ler as tabelas.

Volta: o downgrade tira o FORCE (o comportamento volta a ser exatamente o de
antes, porque o dono ignora as policies); as policies ficam com a cláusula
extra, que sem FORCE não muda nada para o dono.

Revision ID: u7w8forcerls
Revises: t6v7oferta
Create Date: 2026-11-13
"""

from alembic import op

revision = "u7w8forcerls"
down_revision = "t6v7oferta"
branch_labels = None
depends_on = None


_UPGRADE = r"""
DO $$
DECLARE
    p record;
    novo_using text;
    novo_check text;
BEGIN
    FOR p IN
        SELECT tablename, policyname, qual, with_check
          FROM pg_policies
         WHERE schemaname = 'public'
           AND policyname = 'tenant_isolation'
    LOOP
        IF position('current_app_tenant_id() IS NULL' in coalesce(p.qual, '')) = 0 THEN
            novo_using := '(' || coalesce(p.qual, 'false') || ') OR (current_app_tenant_id() IS NULL)';
            novo_check := '(' || coalesce(p.with_check, p.qual, 'false') || ') OR (current_app_tenant_id() IS NULL)';
            EXECUTE format('DROP POLICY %I ON public.%I', p.policyname, p.tablename);
            EXECUTE format(
                'CREATE POLICY %I ON public.%I USING (%s) WITH CHECK (%s)',
                p.policyname, p.tablename, novo_using, novo_check
            );
        END IF;
    END LOOP;
END $$;
"""

# Comando separado: o asyncpg não aceita dois blocos num mesmo execute.
_FORCE = r"""
DO $$
DECLARE
    t record;
BEGIN
    FOR t IN
        SELECT c.relname
          FROM pg_class c
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relrowsecurity
    LOOP
        EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', t.relname);
    END LOOP;
END $$;
"""

_DOWNGRADE = r"""
DO $$
DECLARE
    t record;
BEGIN
    FOR t IN
        SELECT c.relname
          FROM pg_class c
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relforcerowsecurity
    LOOP
        EXECUTE format('ALTER TABLE public.%I NO FORCE ROW LEVEL SECURITY', t.relname);
    END LOOP;
END $$;
"""


def upgrade() -> None:
    op.execute(_UPGRADE)
    op.execute(_FORCE)


def downgrade() -> None:
    op.execute(_DOWNGRADE)
