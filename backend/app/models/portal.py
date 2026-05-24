"""Models for the client portal — magic link authentication tokens."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UUID as SQLUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class PortalMagicToken(Base):
    """
    One-time magic link token for client portal authentication.

    Flow:
      1. Office staff calls POST /portal/magic-link/request for a client user.
      2. Backend creates a PortalMagicToken, sends link to client email.
      3. Client clicks link → POST /portal/magic-link/verify with raw token.
      4. Backend verifies, marks as used, returns JWT.

    Tokens are:
      - Single-use (used=True after first verification)
      - Valid for 24 hours
      - Stored as SHA-256 hash (token_hash) for security
    """

    __tablename__ = "portal_magic_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True,
        comment="SHA-256 hash of the raw token. Never store raw token.",
    )
    email: Mapped[str] = mapped_column(
        String(255), nullable=False,
        comment="Email address this token was sent to",
    )
    used: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True,
        comment="Token expiry — 24 hours from creation",
    )
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<PortalMagicToken(user_id={self.user_id}, used={self.used})>"
