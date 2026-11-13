"""Sincronização offline-first (Frente G): dispositivos, push e pull.

Contrato: docs/arquitetura/OFFLINE_SYNC.md (seções 4, 5, 6 e 9). Padrões
reaproveitados do Moto-OS (`app/api/v1/sync/push|pull`, `lib/sync/errors.ts`):

- cada evento do push em transação própria, idempotente por `<device_id>:<event_id>`;
- erro transitório de banco → 503 com os ACKs já obtidos, sem gravar `rejected`
  (gravar congelaria um erro passageiro para sempre);
- validação/domínio → `rejected` definitivo, mensagem em português e sem SQL;
- pull por cursor `(updated_at, id)` com marca d'água de 5 s.

Rate limit: `RateLimitMiddleware` (prefixo /api/v1/sync, por token + IP; resto da API por usuário).
"""

import json
import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import func, inspect as sa_inspect, literal, select, tuple_
from sqlalchemy import exc as sa_exc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_device, get_current_user, get_db
from app.core.security import create_access_token, create_device_token
from app.domain.invoices.models import Invoice, InvoiceEvent, InvoiceIssuer
from app.domain.invoices.schemas import InvoiceCreate, InvoiceResponse
from app.models.operations import (
    AccountReceivable,
    AccountingClient,
    DeadlineItem,
    DigitalCertificate,
)
from app.models.sync import SyncConflict, SyncDevice, SyncEvent
from app.models.user import User, UserRole
from app.schemas.operations import (
    AccountingClientCreate,
    AccountingClientResponse,
    AccountingClientUpdate,
    CertificateCreate,
    CertificateResponse,
    CertificateUpdate,
    DeadlineCreate,
    DeadlineResponse,
    DeadlineUpdate,
    ReceivableCreate,
    ReceivableResponse,
    ReceivableUpdate,
)
from app.services.audit import log_audit_event

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_EVENTS_PER_PUSH = 200
MAX_PUSH_BYTES = 1_000_000
PULL_MAX_LIMIT = 500
PULL_WATERMARK_SECONDS = 5
TRANSIENT_MESSAGE = "Erro temporário do servidor. Tente novamente."

_NIL_UUID = uuid.UUID(int=0)
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

Platform = Literal["web", "android", "ios", "windows", "macos", "linux"]
EntityName = Literal["client", "deadline", "certificate", "receivable", "invoice"]
Operation = Literal["create", "update", "delete", "emit_requested"]


class DeviceRegisterRequest(BaseModel):
    id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=120)
    platform: Platform
    app_version: Optional[str] = Field(None, max_length=40)


class DeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    name: str
    platform: str
    app_version: Optional[str] = None
    last_seen_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    created_at: datetime


class ConflictResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    event_id: uuid.UUID
    device_id: uuid.UUID
    base_version: Optional[int] = None
    server_version: int
    fields_overwritten: dict
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[uuid.UUID] = None
    created_at: datetime


class DeviceRegisterResponse(BaseModel):
    device: DeviceResponse
    device_token: str


class DeviceTokenResponse(BaseModel):
    device_token: str
    access_token: str
    token_type: str = "bearer"
    tenant_id: uuid.UUID


class SyncEventIn(BaseModel):
    id: uuid.UUID
    device_id: uuid.UUID
    entity_type: EntityName
    entity_id: uuid.UUID
    operation: Operation
    payload: dict[str, Any] = Field(default_factory=dict)
    base_version: Optional[int] = Field(None, ge=0)
    created_at: datetime


class PushRequest(BaseModel):
    events: list[SyncEventIn] = Field(..., min_length=1, max_length=MAX_EVENTS_PER_PUSH)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class SyncRejection(Exception):
    """Erro de validação/domínio: vira `rejected` definitivo com esta mensagem."""


def _utc(value: Optional[datetime]) -> Optional[datetime]:
    """SQLite dos testes devolve datetime sem fuso; tudo aqui é UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


def _transient_sqlstate(exc: BaseException) -> Optional[str]:
    for candidate in (getattr(exc, "orig", None), getattr(getattr(exc, "orig", None), "__cause__", None)):
        if candidate is None:
            continue
        code = getattr(candidate, "sqlstate", None) or getattr(candidate, "pgcode", None)
        if code:
            return str(code)
    return None


# Concorrência/conexão, não o dado: deadlock, serialização, lock/statement timeout,
# admin shutdown e a classe 08 (conexão).
_TRANSIENT_SQLSTATES = {"40P01", "40001", "55P03", "57014", "57P01", "57P03"}


def is_transient_db_error(exc: BaseException) -> bool:
    if isinstance(exc, (TimeoutError, ConnectionError, sa_exc.TimeoutError)):
        return True
    if isinstance(exc, (sa_exc.OperationalError, sa_exc.InterfaceError, sa_exc.DisconnectionError)):
        return True
    if isinstance(exc, sa_exc.DBAPIError):
        if exc.connection_invalidated:
            return True
        code = _transient_sqlstate(exc)
        if code and (code in _TRANSIENT_SQLSTATES or code.startswith("08")):
            return True
    return False


def _validation_message(exc: ValidationError) -> str:
    parts = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err.get("loc", ())) or "payload"
        parts.append(f"{loc}: {err.get('msg')}")
    return "Dados inválidos: " + "; ".join(parts)


_HTTP_DETAIL_PT = {
    "Client not found": "Cliente não encontrado neste escritório.",
    "Invalid CPF or CNPJ for tomador.": "CPF/CNPJ do tomador inválido.",
    "Valor do serviço must be greater than zero.": "O valor do serviço deve ser maior que zero.",
    "Competência cannot be a future month.": "A competência não pode ser um mês futuro.",
    "Invoice issuer not found.": "Emissor da nota não encontrado neste escritório.",
    "Invoice not found.": "Nota fiscal não encontrada.",
}


def _http_message(exc: HTTPException) -> str:
    detail = exc.detail if isinstance(exc.detail, str) else ""
    return _HTTP_DETAIL_PT.get(detail, detail or "Operação recusada pelo servidor.")


def _validate(schema: type[BaseModel], payload: dict) -> BaseModel:
    try:
        return schema.model_validate(payload)
    except ValidationError as exc:
        raise SyncRejection(_validation_message(exc)) from None


# ---------------------------------------------------------------------------
# Entidades
# ---------------------------------------------------------------------------

_LABEL = {
    "client": "cliente",
    "deadline": "prazo",
    "certificate": "certificado",
    "receivable": "honorário",
    "invoice": "nota fiscal",
}

_ENTITY = {
    "client": (AccountingClient, AccountingClientCreate, AccountingClientUpdate, AccountingClientResponse),
    "deadline": (DeadlineItem, DeadlineCreate, DeadlineUpdate, DeadlineResponse),
    "certificate": (DigitalCertificate, CertificateCreate, CertificateUpdate, CertificateResponse),
    "receivable": (AccountReceivable, ReceivableCreate, ReceivableUpdate, ReceivableResponse),
}

# "Exclusão" = status terminal (não há exclusão física; OFFLINE_SYNC.md 3.1).
_DELETE_STATUS = {
    "client": "inactive",
    "deadline": "cancelled",
    "certificate": "revoked",
    "receivable": "cancelled",
}

# Status terminais nunca regridem por LWW (OFFLINE_SYNC.md 5.5).
_TERMINAL = {
    "client": {"inactive"},
    "deadline": {"completed", "cancelled"},
    "certificate": {"revoked"},
    "receivable": {"paid", "cancelled"},
}

_INVOICE_EXCLUDE = {"xml_content", "provider_response"}
# Campos que só o servidor/provedor grava numa nota.
_INVOICE_SERVER_FIELDS = {
    "numero", "serie", "provider_protocol", "provider_response", "xml_content",
    "pdf_storage_path", "xml_storage_path", "issued_at", "cancelled_at",
}
# Já passou (ou está passando) pela emissão: novo pedido é ACK idempotente.
_INVOICE_ALREADY_EMITTING = {
    "validating", "queued", "processing", "issued", "cancel_requested", "cancelled", "replaced",
}


def serialize_entity(entity_type: str, obj: Any) -> dict:
    """Linha final do servidor: *Response schema + version (nota: sem XML/resposta do provedor)."""
    schema = InvoiceResponse if entity_type == "invoice" else _ENTITY[entity_type][3]
    try:
        data = schema.model_validate(obj).model_dump(mode="json")
    except ValidationError:
        # Dado legado que não passa no schema de resposta: entrega as colunas cruas.
        data = _json_safe({attr.key: getattr(obj, attr.key) for attr in sa_inspect(obj).mapper.column_attrs})
    for key in _INVOICE_EXCLUDE if entity_type == "invoice" else ():
        data.pop(key, None)
    data["version"] = getattr(obj, "version", None) if entity_type != "invoice" else None
    return data


class _Ctx:
    """Valores simples do token: sobrevivem ao rollback (que expira os objetos ORM)."""

    def __init__(self, user: User, device: SyncDevice):
        self.tenant_id: uuid.UUID = user.tenant_id
        self.user_id: uuid.UUID = user.id
        self.user_email: str = user.email
        self.role: str = user.role.value
        self.device_id: uuid.UUID = device.id


class _Applied:
    def __init__(self, obj: Any, before: Optional[dict] = None, after: Optional[dict] = None,
                 conflict: Optional[dict] = None, emit_queued: bool = False):
        self.obj = obj
        self.before = before
        self.after = after
        self.conflict = conflict
        self.emit_queued = emit_queued


async def _load(db: AsyncSession, model: Any, tenant_id: uuid.UUID, entity_id: uuid.UUID, lock: bool = True):
    stmt = select(model).where(model.tenant_id == tenant_id, model.id == entity_id)
    if lock:
        # OF <tabela>: a nota tem eager joins (LEFT JOIN) e o Postgres não trava o lado nulo.
        stmt = stmt.with_for_update(of=model)
    return await db.scalar(stmt)


async def _ensure_new_id(db: AsyncSession, model: Any, entity_id: uuid.UUID) -> None:
    if await db.scalar(select(model.id).where(model.id == entity_id)) is not None:
        raise SyncRejection("Já existe um registro com este identificador.")


async def _ensure_client(db: AsyncSession, tenant_id: uuid.UUID, client_id: Optional[uuid.UUID]) -> None:
    from app.core.tenant_guard import ensure_client_in_tenant

    try:
        await ensure_client_in_tenant(db, tenant_id, client_id)
    except HTTPException as exc:
        raise SyncRejection(_http_message(exc)) from None


async def _check_client_plan_limit(db: AsyncSession, ctx: _Ctx) -> None:
    """Mesmo limite de clientes ativos do POST /clients (falha da checagem não bloqueia)."""
    try:
        from app.core.plan_access import resolve_tenant_plan
        from app.models.plan import Plan
        from app.models.tenant import Tenant

        tenant_obj = await db.scalar(select(Tenant).where(Tenant.id == ctx.tenant_id))
        slug = resolve_tenant_plan(tenant_obj, ctx.user_email) or "free"
        plan_obj = await db.scalar(select(Plan).where(Plan.slug == slug))
        if plan_obj is None or plan_obj.max_clients is None:
            return
        count = await db.scalar(
            select(func.count()).select_from(AccountingClient).where(
                AccountingClient.tenant_id == ctx.tenant_id, AccountingClient.status == "active"
            )
        )
        if int(count or 0) >= plan_obj.max_clients:
            raise SyncRejection(
                f"Limite de clientes atingido para o plano {plan_obj.name} "
                f"({plan_obj.max_clients} clientes ativos). Faça upgrade em fiscwise.com.br/planos."
            )
    except SyncRejection:
        raise
    except Exception as exc:  # igual ao REST: checagem de plano não derruba o cadastro
        if is_transient_db_error(exc):
            raise
        logger.warning("Plan limit check failed (non-fatal): %s", exc)


async def _create(db: AsyncSession, ctx: _Ctx, ev: SyncEventIn) -> _Applied:
    model, create_schema, _upd, _resp = _ENTITY[ev.entity_type]
    data = _validate(create_schema, ev.payload)
    await _ensure_new_id(db, model, ev.entity_id)
    values = data.model_dump()
    if ev.entity_type == "client":
        if data.status == "active":
            await _check_client_plan_limit(db, ctx)
        if data.document:
            dup = await db.scalar(
                select(AccountingClient.id).where(
                    AccountingClient.tenant_id == ctx.tenant_id,
                    AccountingClient.document == data.document,
                )
            )
            if dup is not None:
                raise SyncRejection("Já existe um cliente com este CPF/CNPJ no escritório.")
        from app.api.v1.endpoints.operations import _generate_client_code

        try:
            values["client_code"] = await _generate_client_code(db, ctx.tenant_id)
        except HTTPException:
            raise SyncRejection("Não foi possível gerar o código do cliente. Tente novamente.") from None
    else:
        await _ensure_client(db, ctx.tenant_id, values.get("client_id"))
    obj = model(id=ev.entity_id, tenant_id=ctx.tenant_id, **values)
    db.add(obj)
    return _Applied(obj, after={"fields": sorted(values)})


def _check_terminal(entity_type: str, current: str, new: str) -> None:
    if current in _TERMINAL[entity_type] and new != current:
        raise SyncRejection(
            f"O {_LABEL[entity_type]} está com status '{current}' e não pode voltar para '{new}'."
        )


def _after_status_change(db: AsyncSession, entity_type: str, obj: Any, old_status: str) -> None:
    """Efeitos colaterais iguais aos do PATCH REST."""
    now = datetime.now(timezone.utc)
    if entity_type == "deadline" and obj.status == "completed":
        if obj.completed_at is None:
            obj.completed_at = now
        if old_status != "completed" and obj.is_recurring and obj.recurrence_interval:
            from app.api.v1.endpoints.operations import get_next_due_date

            db.add(DeadlineItem(
                tenant_id=obj.tenant_id,
                client_id=obj.client_id,
                title=obj.title,
                category=obj.category,
                due_date=get_next_due_date(obj.due_date, obj.recurrence_interval),
                status="pending",
                priority=obj.priority,
                description=obj.description,
                is_recurring=True,
                recurrence_interval=obj.recurrence_interval,
                recurrence_parent_id=obj.id,
            ))
    if entity_type == "receivable" and obj.status == "paid" and obj.paid_at is None:
        obj.paid_at = now


async def _update(db: AsyncSession, ctx: _Ctx, ev: SyncEventIn) -> _Applied:
    model, _create_schema, update_schema, _resp = _ENTITY[ev.entity_type]
    data = _validate(update_schema, ev.payload)
    obj = await _load(db, model, ctx.tenant_id, ev.entity_id)
    if obj is None:
        raise SyncRejection(f"{_LABEL[ev.entity_type].capitalize()} não encontrado neste escritório.")
    changes = data.model_dump(exclude_unset=True)
    for key, value in changes.items():
        if value is None and not model.__table__.c[key].nullable:
            raise SyncRejection(f"O campo '{key}' não pode ficar vazio.")
    old_status = obj.status
    if "status" in changes and changes["status"] is not None:
        _check_terminal(ev.entity_type, old_status, changes["status"])
    if ev.entity_type == "client" and changes.get("document") and changes["document"] != obj.document:
        dup = await db.scalar(
            select(AccountingClient.id).where(
                AccountingClient.tenant_id == ctx.tenant_id,
                AccountingClient.document == changes["document"],
                AccountingClient.id != obj.id,
            )
        )
        if dup is not None:
            raise SyncRejection("Já existe um cliente com este CPF/CNPJ no escritório.")

    server_version = obj.version
    differing = {k: v for k, v in changes.items() if getattr(obj, k) != v}
    before = _json_safe({k: getattr(obj, k) for k in differing})
    conflict = None
    if ev.base_version is not None and ev.base_version < server_version and differing:
        # LWW por campo: o evento vence nos campos que trouxe; o histórico guarda o valor do servidor.
        conflict = _json_safe({k: {"server": getattr(obj, k), "client": v} for k, v in differing.items()})
    for key, value in changes.items():
        setattr(obj, key, value)
    if "status" in differing:
        _after_status_change(db, ev.entity_type, obj, old_status)
    if conflict:
        db.add(SyncConflict(
            tenant_id=ctx.tenant_id,
            entity_type=ev.entity_type,
            entity_id=ev.entity_id,
            event_id=ev.id,
            device_id=ctx.device_id,
            base_version=ev.base_version,
            server_version=server_version,
            fields_overwritten=conflict,
        ))
    return _Applied(obj, before=before, after={"fields": sorted(differing)}, conflict=conflict)


async def _delete(db: AsyncSession, ctx: _Ctx, ev: SyncEventIn) -> _Applied:
    model = _ENTITY[ev.entity_type][0]
    obj = await _load(db, model, ctx.tenant_id, ev.entity_id)
    if obj is None:
        raise SyncRejection(f"{_LABEL[ev.entity_type].capitalize()} não encontrado neste escritório.")
    target = _DELETE_STATUS[ev.entity_type]
    old_status = obj.status
    _check_terminal(ev.entity_type, old_status, target)
    obj.status = target
    return _Applied(obj, before={"status": old_status}, after={"status": target})


async def _create_invoice(db: AsyncSession, ctx: _Ctx, ev: SyncEventIn) -> _Applied:
    """Só rascunho: offline o FiscWise não autoriza nem emite (OFFLINE_SYNC.md 6)."""
    from app.domain.invoices.validators import validate_cpf_cnpj

    sent_status = ev.payload.get("status")
    if sent_status is not None and sent_status != "draft":
        raise SyncRejection(
            "Nota criada fora do servidor só pode ser rascunho; a autorização é feita pela "
            "prefeitura/ambiente nacional depois da transmissão."
        )
    server_fields = sorted(_INVOICE_SERVER_FIELDS & set(ev.payload))
    if server_fields:
        raise SyncRejection(
            "Campos da nota controlados pelo servidor não podem ser enviados: " + ", ".join(server_fields) + "."
        )
    data: InvoiceCreate = _validate(InvoiceCreate, ev.payload)  # type: ignore[assignment]
    # Mesmas regras de InvoiceService.create_invoice (que não aceita id vindo do cliente).
    if data.tomador_cpf_cnpj and not validate_cpf_cnpj(data.tomador_cpf_cnpj):
        raise SyncRejection("CPF/CNPJ do tomador inválido.")
    today = date.today()
    if (data.competencia.year, data.competencia.month) > (today.year, today.month):
        raise SyncRejection("A competência não pode ser um mês futuro.")
    await _ensure_new_id(db, Invoice, ev.entity_id)
    await _ensure_client(db, ctx.tenant_id, data.client_id)
    issuer = await db.scalar(
        select(InvoiceIssuer.id).where(InvoiceIssuer.id == data.issuer_id, InvoiceIssuer.tenant_id == ctx.tenant_id)
    )
    if issuer is None:
        raise SyncRejection("Emissor da nota não encontrado neste escritório.")
    invoice = Invoice(
        id=ev.entity_id,
        tenant_id=ctx.tenant_id,
        issuer_id=data.issuer_id,
        client_id=data.client_id,
        status="draft",
        competencia=data.competencia,
        valor_servico=data.valor_servico,
        valor_deducoes=data.valor_deducoes,
        valor_iss=data.valor_iss,
        descricao_servico=data.descricao_servico,
        tomador_nome=data.tomador_nome,
        tomador_cpf_cnpj=data.tomador_cpf_cnpj,
        tomador_email=data.tomador_email,
        tomador_municipio_ibge=data.tomador_municipio_ibge,
        billing_charge_id=data.billing_charge_id,
    )
    db.add(invoice)
    db.add(InvoiceEvent(invoice_id=ev.entity_id, tenant_id=ctx.tenant_id, event_type="created",
                        payload={"status": "draft", "source": "sync"}))
    return _Applied(invoice, after={"status": "draft"})


async def _emit_invoice(db: AsyncSession, ctx: _Ctx, ev: SyncEventIn) -> _Applied:
    from app.domain.invoices.providers.factory import (
        NfseProviderNotConfiguredError,
        build_nfse_provider,
    )
    from app.domain.invoices.repository import InvoiceRepository
    from app.domain.invoices.service import InvoiceService

    invoice = await _load(db, Invoice, ctx.tenant_id, ev.entity_id)
    if invoice is None:
        raise SyncRejection("Nota fiscal não encontrada neste escritório.")
    if invoice.status in _INVOICE_ALREADY_EMITTING:
        # Segundo pedido (outro dispositivo, reenvio): nunca duas emissões.
        return _Applied(invoice, after={"status": invoice.status, "already": True})
    if invoice.status not in ("draft", "rejected"):
        raise SyncRejection(f"A nota está com status '{invoice.status}' e não pode ser transmitida.")
    # Mesmo portão do POST /invoices/{id}/emit: em produção com provider mock a
    # nota não sai do rascunho (regra G2; providers/factory.py).
    try:
        build_nfse_provider()
    except NfseProviderNotConfiguredError as exc:
        raise SyncRejection(str(exc)) from None
    old_status = invoice.status
    try:
        invoice = await InvoiceService(InvoiceRepository(db)).queue_emission(ev.entity_id, ctx.tenant_id)
    except ValueError:
        raise SyncRejection("A nota não pode ser transmitida no status atual.") from None
    except HTTPException as exc:
        raise SyncRejection(_http_message(exc)) from None
    return _Applied(invoice, before={"status": old_status}, after={"status": invoice.status}, emit_queued=True)


async def _apply(db: AsyncSession, ctx: _Ctx, ev: SyncEventIn) -> _Applied:
    if ev.entity_type == "invoice":
        if ev.operation == "create":
            return await _create_invoice(db, ctx, ev)
        if ev.operation == "emit_requested":
            return await _emit_invoice(db, ctx, ev)
        raise SyncRejection(
            "Nota fiscal só aceita criação de rascunho e pedido de transmissão pela sincronização."
        )
    if ev.operation == "emit_requested":
        raise SyncRejection("Pedido de transmissão só vale para nota fiscal.")
    if ev.operation == "create":
        return await _create(db, ctx, ev)
    if ev.operation == "update":
        return await _update(db, ctx, ev)
    return await _delete(db, ctx, ev)


def _event_row(ctx: _Ctx, ev: SyncEventIn, status_: str, error: Optional[str] = None) -> SyncEvent:
    return SyncEvent(
        tenant_id=ctx.tenant_id,
        device_id=ctx.device_id,
        event_id=ev.id,
        idempotency_key=f"{ev.device_id}:{ev.id}",
        entity_type=ev.entity_type,
        entity_id=ev.entity_id,
        operation=ev.operation,
        payload=_json_safe(ev.payload),
        status=status_,
        error=error,
        client_created_at=_utc(ev.created_at),
    )


async def _ack_from_seen(db: AsyncSession, ctx: _Ctx, ev: SyncEventIn, seen: SyncEvent) -> dict:
    if seen.status != "applied":
        return {"id": str(ev.id), "status": "rejected", "error": seen.error or "Evento rejeitado anteriormente."}
    ack: dict[str, Any] = {"id": str(ev.id), "status": "ack"}
    model = Invoice if ev.entity_type == "invoice" else _ENTITY[ev.entity_type][0]
    obj = await _load(db, model, ctx.tenant_id, ev.entity_id, lock=False)
    if obj is not None:
        ack["entity"] = serialize_entity(ev.entity_type, obj)
    conflict = await db.scalar(
        select(SyncConflict).where(SyncConflict.tenant_id == ctx.tenant_id, SyncConflict.event_id == ev.id)
    )
    if conflict is not None:
        ack["conflict"] = True
        ack["fields_overwritten"] = conflict.fields_overwritten
    return ack


async def _find_seen(db: AsyncSession, key: str) -> Optional[SyncEvent]:
    return await db.scalar(select(SyncEvent).where(SyncEvent.idempotency_key == key))


async def _record_rejection(db: AsyncSession, ctx: _Ctx, ev: SyncEventIn, message: str) -> None:
    db.add(_event_row(ctx, ev, "rejected", message[:1000]))
    await db.commit()


# ---------------------------------------------------------------------------
# Dispositivos
# ---------------------------------------------------------------------------


@router.post("/devices", response_model=DeviceRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_device(
    payload: DeviceRegisterRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Registra (ou atualiza) o dispositivo e devolve o token de dispositivo (30 dias)."""
    tenant_id, user_id, role = current_user.tenant_id, current_user.id, current_user.role.value
    now = datetime.now(timezone.utc)
    device = await db.scalar(select(SyncDevice).where(SyncDevice.id == payload.id))
    if device is not None:
        if device.tenant_id != tenant_id or device.user_id != user_id:
            raise HTTPException(status.HTTP_409_CONFLICT, "Identificador de dispositivo já está em uso.")
        if device.revoked_at is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Dispositivo revogado. Apague os dados locais e registre um novo dispositivo.",
            )
        device.name, device.platform, device.app_version = payload.name, payload.platform, payload.app_version
        device.last_seen_at = now
        action = "sync.device.update"
    else:
        device = SyncDevice(
            id=payload.id,
            tenant_id=tenant_id,
            user_id=user_id,
            name=payload.name,
            platform=payload.platform,
            app_version=payload.app_version,
            last_seen_at=now,
        )
        db.add(device)
        action = "sync.device.register"
    try:
        await db.commit()
    except sa_exc.IntegrityError:
        # id já usado em outro escritório (invisível pela RLS).
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Identificador de dispositivo já está em uso.")
    await db.refresh(device)
    response = DeviceRegisterResponse(
        device=DeviceResponse.model_validate(device),
        device_token=create_device_token(str(user_id), str(tenant_id), role, str(payload.id)),
    )
    await log_audit_event(
        db=db, tenant_id=tenant_id, action=action, entity_type="sync_device",
        actor_user_id=user_id, actor_role=role, entity_id=payload.id,
        after_data={"name": payload.name, "platform": payload.platform, "app_version": payload.app_version},
    )
    return response


@router.get("/devices", response_model=list[DeviceResponse])
async def list_devices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dono/admin veem todos os dispositivos do escritório; membro só os próprios."""
    stmt = select(SyncDevice).where(SyncDevice.tenant_id == current_user.tenant_id)
    if current_user.role not in (UserRole.OWNER, UserRole.ADMIN):
        stmt = stmt.where(SyncDevice.user_id == current_user.id)
    result = await db.execute(stmt.order_by(SyncDevice.created_at.desc()))
    return list(result.scalars().all())


@router.post("/devices/token", response_model=DeviceTokenResponse)
async def renew_device_token(request: Request, auth=Depends(get_current_device)):
    """Renova o token de dispositivo e entrega um token de acesso comum (30 min).

    O token novo herda o início da cadeia (``fia``): a soma das renovações
    nunca passa de 180 dias sem um login online (get_current_device recusa).
    """
    user, device = auth
    chain_started_at = getattr(request.state, "device_chain_started_at", None)
    return DeviceTokenResponse(
        device_token=create_device_token(
            str(user.id), str(user.tenant_id), user.role.value, str(device.id),
            first_issued_at=chain_started_at,
        ),
        access_token=create_access_token(str(user.id), str(user.tenant_id), user.role.value),
        tenant_id=user.tenant_id,
    )


@router.post("/devices/{device_id}/revoke", response_model=DeviceResponse)
async def revoke_device(
    device_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoga o dispositivo: no próximo contato ele recebe 401 device_revoked e apaga o banco local."""
    tenant_id, user_id, role = current_user.tenant_id, current_user.id, current_user.role
    device = await db.scalar(
        select(SyncDevice).where(SyncDevice.id == device_id, SyncDevice.tenant_id == tenant_id)
    )
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dispositivo não encontrado.")
    if role not in (UserRole.OWNER, UserRole.ADMIN) and device.user_id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Só o dono, um administrador ou o próprio usuário pode revogar.")
    if device.revoked_at is None:
        device.revoked_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(device)
        response = DeviceResponse.model_validate(device)
        await log_audit_event(
            db=db, tenant_id=tenant_id, action="sync.device.revoke", entity_type="sync_device",
            actor_user_id=user_id, actor_role=role.value, entity_id=device_id,
            after_data={"revoked_at": response.revoked_at.isoformat() if response.revoked_at else None},
        )
        return response
    return DeviceResponse.model_validate(device)


# ---------------------------------------------------------------------------
# Conflitos (histórico de LWW por campo, compartilhado entre dispositivos)
# ---------------------------------------------------------------------------


def _conflicts_scope(current_user: User):
    """Dono/admin veem os conflitos do escritório; membro, os dos próprios dispositivos."""
    stmt = select(SyncConflict).where(SyncConflict.tenant_id == current_user.tenant_id)
    if current_user.role not in (UserRole.OWNER, UserRole.ADMIN):
        own_devices = select(SyncDevice.id).where(
            SyncDevice.tenant_id == current_user.tenant_id, SyncDevice.user_id == current_user.id
        )
        stmt = stmt.where(SyncConflict.device_id.in_(own_devices))
    return stmt


@router.get("/conflicts", response_model=list[ConflictResponse])
async def list_conflicts(
    resolved: bool = Query(False, description="false = só os abertos; true = só os já revisados"),
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Conflitos de sincronização (valor do servidor sobrescrito por edição offline).

    Mais recentes primeiro. A revisão vale para todos os dispositivos do escritório.
    """
    stmt = _conflicts_scope(current_user)
    stmt = stmt.where(SyncConflict.resolved_at.is_not(None) if resolved else SyncConflict.resolved_at.is_(None))
    if entity_type:
        stmt = stmt.where(SyncConflict.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(SyncConflict.entity_id == entity_id)
    result = await db.execute(stmt.order_by(SyncConflict.created_at.desc(), SyncConflict.id.desc()).limit(limit))
    return list(result.scalars().all())


@router.post("/conflicts/{conflict_id}/resolve", response_model=ConflictResponse)
async def resolve_conflict(
    conflict_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Marca o conflito como revisado ("manter como está"). Idempotente.

    Restaurar o valor anterior é uma edição comum (PATCH da entidade ou evento
    `update` do sync), feita antes de resolver.
    """
    tenant_id, user_id, role = current_user.tenant_id, current_user.id, current_user.role
    conflict = await db.scalar(_conflicts_scope(current_user).where(SyncConflict.id == conflict_id))
    if conflict is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conflito não encontrado.")
    if conflict.resolved_at is not None:
        return ConflictResponse.model_validate(conflict)
    conflict.resolved_at = datetime.now(timezone.utc)
    conflict.resolved_by = user_id
    await db.commit()
    await db.refresh(conflict)
    response = ConflictResponse.model_validate(conflict)
    await log_audit_event(
        db=db, tenant_id=tenant_id, action="sync.conflict.resolve", entity_type="sync_conflict",
        actor_user_id=user_id, actor_role=role.value, entity_id=conflict_id,
        after_data={"entity_type": response.entity_type, "entity_id": str(response.entity_id)},
    )
    return response


# ---------------------------------------------------------------------------
# Push
# ---------------------------------------------------------------------------


@router.post("/push")
async def push(
    body: PushRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    auth=Depends(get_current_device),
    db: AsyncSession = Depends(get_db),
):
    """Aplica cada evento uma única vez (`device_id:event_id`), em transação própria.

    Resposta `{acks: [{id, status: ack|rejected, error?, entity?, conflict?, fields_overwritten?}]}`;
    erro transitório de banco → 503 `{acks: [...já obtidos], error}` e nada é gravado para o evento.
    """
    if len(await request.body()) > MAX_PUSH_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Lote maior que 1 MB; envie em partes.")
    user, device = auth
    ctx = _Ctx(user, device)
    acks: list[dict] = []

    for ev in body.events:
        if ev.device_id != ctx.device_id:
            acks.append({"id": str(ev.id), "status": "rejected",
                         "error": "Evento não pertence a este dispositivo."})
            continue
        key = f"{ev.device_id}:{ev.id}"
        try:
            seen = await _find_seen(db, key)
            if seen is not None:
                acks.append(await _ack_from_seen(db, ctx, ev, seen))
                continue

            try:
                applied = await _apply(db, ctx, ev)
                db.add(_event_row(ctx, ev, "applied"))
                await db.commit()
            except SyncRejection as rejection:
                # Validações rodam antes de mexer na sessão; rollback só se algo ficou pendente
                # (rollback expira todos os objetos carregados).
                if db.new or db.dirty or db.deleted:
                    await db.rollback()
                await _record_rejection(db, ctx, ev, str(rejection))
                acks.append({"id": str(ev.id), "status": "rejected", "error": str(rejection)})
                continue
            except sa_exc.IntegrityError:
                await db.rollback()
                seen = await _find_seen(db, key)
                if seen is not None:  # corrida: outra requisição aplicou primeiro
                    acks.append(await _ack_from_seen(db, ctx, ev, seen))
                    continue
                message = "Já existe um registro com esses dados (ex.: mesmo CNPJ/CPF) ou a referência não existe."
                await _record_rejection(db, ctx, ev, message)
                acks.append({"id": str(ev.id), "status": "rejected", "error": message})
                continue

            await db.refresh(applied.obj)
            ack: dict[str, Any] = {"id": str(ev.id), "status": "ack",
                                   "entity": serialize_entity(ev.entity_type, applied.obj)}
            if applied.conflict:
                ack["conflict"] = True
                ack["fields_overwritten"] = applied.conflict
            acks.append(ack)
            if applied.emit_queued:
                from app.api.v1.endpoints.invoices import process_emission_background

                # Mesmo caminho do POST /invoices/{id}/emit.
                background_tasks.add_task(process_emission_background, ev.entity_id, ctx.tenant_id)
            await log_audit_event(
                db=db, tenant_id=ctx.tenant_id, action=f"sync.{ev.entity_type}.{ev.operation}",
                entity_type=ev.entity_type, actor_user_id=ctx.user_id, actor_role=ctx.role,
                entity_id=ev.entity_id, before_data=applied.before,
                after_data={**(applied.after or {}), "event_id": str(ev.id), "device_id": str(ctx.device_id),
                            "conflict": bool(applied.conflict)},
            )
        except Exception as exc:
            try:
                await db.rollback()
            except Exception:
                pass
            if is_transient_db_error(exc):
                logger.error("sync push: erro transitório no evento %s: %s", ev.id, type(exc).__name__)
                return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                                    content={"acks": acks, "error": TRANSIENT_MESSAGE})
            if isinstance(exc, sa_exc.DBAPIError):
                logger.exception("sync push: erro de banco no evento %s", ev.id)
                message = "Erro ao gravar no banco de dados."
                try:
                    await _record_rejection(db, ctx, ev, message)
                except Exception:
                    await db.rollback()
                acks.append({"id": str(ev.id), "status": "rejected", "error": message})
                continue
            # Bug do servidor: não grava rejeição definitiva (um deploy corrigido destrava o evento).
            logger.exception("sync push: falha inesperada no evento %s", ev.id)
            acks.append({"id": str(ev.id), "status": "rejected",
                         "error": "Erro interno ao aplicar a alteração. Tente sincronizar mais tarde."})

    return {"acks": acks}


# ---------------------------------------------------------------------------
# Pull
# ---------------------------------------------------------------------------

_PULL_ENTITIES = {
    "clients": ("client", AccountingClient),
    "deadlines": ("deadline", DeadlineItem),
    "certificates": ("certificate", DigitalCertificate),
    "receivables": ("receivable", AccountReceivable),
    "invoices": ("invoice", Invoice),
}


@router.get("/pull")
async def pull(
    entity: Literal["clients", "deadlines", "certificates", "receivables", "invoices"],
    since: Optional[datetime] = Query(None),
    after_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(PULL_MAX_LIMIT, ge=1, le=PULL_MAX_LIMIT),
    auth=Depends(get_current_device),
    db: AsyncSession = Depends(get_db),
):
    """Delta da entidade: `(updated_at, id) > (since, after_id)` e `updated_at <= now() - 5 s`.

    O cliente só persiste `next` depois de gravar todas as linhas do lote.
    """
    user, _device = auth
    entity_type, model = _PULL_ENTITIES[entity]
    watermark = datetime.now(timezone.utc) - timedelta(seconds=PULL_WATERMARK_SECONDS)
    cursor_since = _utc(since) or _EPOCH
    cursor_id = after_id or _NIL_UUID

    stmt = (
        select(model)
        .where(
            model.tenant_id == user.tenant_id,
            model.updated_at <= watermark,
            tuple_(model.updated_at, model.id)
            > tuple_(literal(cursor_since, model.updated_at.type), literal(cursor_id, model.id.type)),
        )
        .order_by(model.updated_at.asc(), model.id.asc())
        .limit(limit + 1)
    )
    rows = list((await db.execute(stmt)).scalars().unique().all())
    has_more = len(rows) > limit
    rows = rows[:limit]
    if rows:
        last = rows[-1]
        next_cursor = {"since": _utc(last.updated_at).isoformat(), "after_id": str(last.id)}
    else:
        next_cursor = {
            "since": _utc(since).isoformat() if since else None,
            "after_id": str(after_id) if after_id else None,
        }
    serialized = []
    for row in rows:
        data = serialize_entity(entity_type, row)
        data["updated_at"] = _utc(row.updated_at).isoformat()
        data["created_at"] = _utc(row.created_at).isoformat()
        serialized.append(data)
    return {"rows": serialized, "next": next_cursor, "has_more": has_more}
