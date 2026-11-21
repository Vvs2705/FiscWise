"""Segredo TOTP cifrado: users.two_factor_secret passa de VARCHAR(64) para VARCHAR(255).

O valor cifrado (enc:v1: + base64 de nonce, texto e tag do AES-256-GCM) tem
cerca de 90 caracteres. Alargar VARCHAR não perde dados nem reescreve a
tabela no PostgreSQL.

Os segredos já gravados continuam em texto puro e são cifrados no próximo
login com 2FA (app/api/v1/endpoints/auth.py). Não há migração de dados aqui.

Volta: no-op de propósito. Estreitar de novo para 64 truncaria (ou recusaria)
os segredos já cifrados, e o usuário perderia o 2FA.

Revision ID: y1b2totpcifrado
Revises: x0a1certificados
Create Date: 2026-11-21
"""

import sqlalchemy as sa
from alembic import op

revision = "y1b2totpcifrado"
down_revision = "x0a1certificados"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "two_factor_secret",
        existing_type=sa.String(length=64),
        type_=sa.String(length=255),
        existing_nullable=True,
    )


def downgrade() -> None:
    pass
