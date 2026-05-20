"""Factory builders for test fixtures."""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from app.models.operations import (
    AccountReceivable,
    AccountingClient,
    ClientDocument,
    DeadlineItem,
    DigitalCertificate,
)
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.schemas.operations import (
    AccountingClientCreate,
    CertificateCreate,
    DeadlineCreate,
    DocumentCreate,
    ReceivableCreate,
)


class TenantFactory:
    @staticmethod
    def build(
        id: Optional[uuid.UUID] = None,
        name: str = "Test Tenant",
        is_active: bool = True,
    ) -> Tenant:
        return Tenant(
            id=id or uuid.uuid4(),
            name=name,
            is_active=is_active,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )


class UserFactory:
    @staticmethod
    def build(
        id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        email: str = "user@example.com",
        role: UserRole = UserRole.OWNER,
        is_active: bool = True,
    ) -> User:
        return User(
            id=id or uuid.uuid4(),
            tenant_id=tenant_id or uuid.uuid4(),
            email=email,
            hashed_password="$2b$12$test",
            role=role,
            is_active=is_active,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )


class AccountingClientFactory:
    @staticmethod
    def build(
        id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        name: str = "Test Client",
        document: Optional[str] = None,
        status: str = "active",
    ) -> AccountingClient:
        return AccountingClient(
            id=id or uuid.uuid4(),
            tenant_id=tenant_id or uuid.uuid4(),
            name=name,
            document=document or f"{uuid.uuid4().hex[:8]}",
            entity_type="pj",
            status=status,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def create_schema(**kwargs) -> AccountingClientCreate:
        return AccountingClientCreate(
            name=kwargs.get("name", "Test Client"),
            document=kwargs.get("document", f"{uuid.uuid4().hex[:8]}"),
            entity_type=kwargs.get("entity_type", "pj"),
            status=kwargs.get("status", "active"),
            tax_regime=kwargs.get("tax_regime"),
            email=kwargs.get("email"),
            phone=kwargs.get("phone"),
            notes=kwargs.get("notes"),
        )


class DeadlineFactory:
    @staticmethod
    def build(
        id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        client_id: Optional[uuid.UUID] = None,
        title: str = "Test Deadline",
        status: str = "pending",
    ) -> DeadlineItem:
        return DeadlineItem(
            id=id or uuid.uuid4(),
            tenant_id=tenant_id or uuid.uuid4(),
            client_id=client_id or uuid.uuid4(),
            title=title,
            category="fiscal",
            due_date=date.today() + timedelta(days=7),
            status=status,
            priority="medium",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def create_schema(client_id: Optional[uuid.UUID] = None, **kwargs) -> DeadlineCreate:
        return DeadlineCreate(
            client_id=client_id or uuid.uuid4(),
            title=kwargs.get("title", "Test Deadline"),
            category=kwargs.get("category", "fiscal"),
            due_date=kwargs.get("due_date", date.today() + timedelta(days=7)),
            status=kwargs.get("status", "pending"),
            priority=kwargs.get("priority", "medium"),
            description=kwargs.get("description"),
        )


class DocumentFactory:
    @staticmethod
    def build(
        id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        client_id: Optional[uuid.UUID] = None,
        name: str = "Test Document",
        status: str = "available",
    ) -> ClientDocument:
        return ClientDocument(
            id=id or uuid.uuid4(),
            tenant_id=tenant_id or uuid.uuid4(),
            client_id=client_id or uuid.uuid4(),
            name=name,
            document_type="other",
            status=status,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def create_schema(client_id: Optional[uuid.UUID] = None, **kwargs) -> DocumentCreate:
        return DocumentCreate(
            client_id=client_id or uuid.uuid4(),
            name=kwargs.get("name", "Test Document"),
            document_type=kwargs.get("document_type", "other"),
            status=kwargs.get("status", "available"),
            file_url=kwargs.get("file_url"),
            issued_at=kwargs.get("issued_at"),
            expires_at=kwargs.get("expires_at"),
            notes=kwargs.get("notes"),
        )


class CertificateFactory:
    @staticmethod
    def build(
        id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        client_id: Optional[uuid.UUID] = None,
        status: str = "valid",
    ) -> DigitalCertificate:
        return DigitalCertificate(
            id=id or uuid.uuid4(),
            tenant_id=tenant_id or uuid.uuid4(),
            client_id=client_id or uuid.uuid4(),
            certificate_type="e-cnpj",
            holder_name="Test Holder",
            status=status,
            issued_at=datetime.now(timezone.utc).date(),
            valid_until=(datetime.now(timezone.utc) + timedelta(days=365)).date(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def create_schema(client_id: Optional[uuid.UUID] = None, **kwargs) -> CertificateCreate:
        return CertificateCreate(
            client_id=client_id or uuid.uuid4(),
            certificate_type=kwargs.get("certificate_type", "e-cnpj"),
            holder_name=kwargs.get("holder_name", "Test Holder"),
            status=kwargs.get("status", "valid"),
            issued_at=kwargs.get("issued_at", datetime.now(timezone.utc).date()),
            valid_until=kwargs.get(
                "valid_until",
                (datetime.now(timezone.utc) + timedelta(days=365)).date(),
            ),
        )


class ReceivableFactory:
    @staticmethod
    def build(
        id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        client_id: Optional[uuid.UUID] = None,
        status: str = "pending",
    ) -> AccountReceivable:
        return AccountReceivable(
            id=id or uuid.uuid4(),
            tenant_id=tenant_id or uuid.uuid4(),
            client_id=client_id or uuid.uuid4(),
            description="Test Invoice",
            amount=Decimal("1000.00"),
            due_date=date.today() + timedelta(days=30),
            status=status,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def create_schema(client_id: Optional[uuid.UUID] = None, **kwargs) -> ReceivableCreate:
        return ReceivableCreate(
            client_id=client_id or uuid.uuid4(),
            description=kwargs.get("description", "Test Invoice"),
            amount=kwargs.get("amount", Decimal("1000.00")),
            due_date=kwargs.get("due_date", date.today() + timedelta(days=30)),
            status=kwargs.get("status", "pending"),
        )
