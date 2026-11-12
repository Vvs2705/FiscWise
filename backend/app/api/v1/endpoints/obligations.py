"""Fiscal Obligation Engine API endpoints.

Covers:
  - GET  /obligations/rules                         — list global obligation rules
  - GET  /obligations/instances                     — list obligation instances for tenant
  - POST /obligations/instances                     — create manual obligation instance
  - PATCH /obligations/instances/{id}               — update status / assignment
  - DELETE /obligations/instances/{id}              — cancel (soft delete, status=cancelled)
  - GET  /obligations/profiles/{client_id}          — get client fiscal profile
  - PUT  /obligations/profiles/{client_id}          — upsert client fiscal profile
  - GET  /obligations/checklist                     — list checklist items
  - POST /obligations/checklist                     — add checklist item
  - PATCH /obligations/checklist/{id}               — update checklist item status
  - POST /obligations/generate                      — manually trigger generation (owner only)
"""

import logging
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_principal, get_current_user, get_db
from app.core.tenant_guard import ensure_client_in_tenant
from app.services import webhook_service as _webhook_svc
from app.models.obligation import (
    ClientObligationProfile,
    DocumentChecklistItem,
    ObligationInstance,
    ObligationRule,
)
from app.models.user import User
from app.services.audit import log_audit_event

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Nome da obrigação avulsa
# ---------------------------------------------------------------------------
# ObligationInstance não tem coluna de nome: obrigações avulsas (rule_id nulo)
# guardam o nome na primeira linha de `notes`, com este prefixo. A API devolve
# o nome em `custom_name` e as observações sem o prefixo em `notes`.
CUSTOM_NAME_PREFIX = "[Avulsa] "


def _compose_notes(custom_name: Optional[str], notes: Optional[str]) -> Optional[str]:
    name = (custom_name or "").strip().replace("\n", " ")
    if not name:
        return notes
    head = f"{CUSTOM_NAME_PREFIX}{name}"
    return f"{head}\n{notes}" if notes else head


def _split_notes(raw: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    if not raw or not raw.startswith(CUSTOM_NAME_PREFIX):
        return None, raw
    head, _, rest = raw.partition("\n")
    return head[len(CUSTOM_NAME_PREFIX):] or None, rest or None


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ObligationRuleOut(BaseModel):
    id: UUID
    code: str
    name: str
    description: Optional[str]
    jurisdiction: str
    state: Optional[str]
    applies_to_regimes: Optional[List[str]]
    recurrence: str
    due_day: Optional[int]
    requires_employees: bool
    active: bool

    class Config:
        from_attributes = True


class ObligationInstanceOut(BaseModel):
    id: UUID
    client_id: UUID
    rule_id: Optional[UUID]
    competence_month: date
    due_date: date
    status: str
    priority: str
    assigned_to: Optional[UUID]
    notes: Optional[str]
    custom_name: Optional[str] = None
    completed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

    @model_validator(mode="after")
    def _split_custom_name(self) -> "ObligationInstanceOut":
        # O nome da obrigação avulsa viaja dentro de `notes` (ver _compose_notes).
        if self.custom_name is None:
            self.custom_name, self.notes = _split_notes(self.notes)
        return self


class CreateObligationInstanceRequest(BaseModel):
    client_id: UUID
    rule_id: Optional[UUID] = None
    competence_month: date
    due_date: date
    status: str = "pending"
    priority: str = "medium"
    assigned_to: Optional[UUID] = None
    notes: Optional[str] = None
    custom_name: Optional[str] = Field(None, max_length=200)


class UpdateObligationInstanceRequest(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[UUID] = None
    delivery_proof: Optional[str] = None
    notes: Optional[str] = None


class ClientObligationProfileOut(BaseModel):
    id: UUID
    client_id: UUID
    tax_regime: Optional[str]
    cnae_main: Optional[str]
    cnae_secondary: Optional[List[str]]
    state: Optional[str]
    has_employees: bool
    has_state_registration: bool
    has_municipal_registration: bool
    updated_at: datetime

    class Config:
        from_attributes = True


class UpsertProfileRequest(BaseModel):
    tax_regime: Optional[str] = Field(None, description="simples_nacional | lucro_presumido | lucro_real | mei")
    cnae_main: Optional[str] = Field(None, max_length=10)
    cnae_secondary: Optional[List[str]] = None
    state: Optional[str] = Field(None, max_length=2)
    has_employees: bool = False
    has_state_registration: bool = False
    has_municipal_registration: bool = False


class ChecklistItemOut(BaseModel):
    id: UUID
    client_id: UUID
    obligation_id: Optional[UUID]
    competence_month: date
    document_name: str
    status: str
    received_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class CreateChecklistItemRequest(BaseModel):
    client_id: UUID
    obligation_id: Optional[UUID] = None
    competence_month: date
    document_name: str = Field(..., min_length=1, max_length=200)
    notes: Optional[str] = None


class UpdateChecklistItemRequest(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


class GenerateObligationsRequest(BaseModel):
    year: int = Field(..., ge=2020, le=2099)
    month: int = Field(..., ge=1, le=12)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_INSTANCE_STATUSES = {"pending", "in_progress", "delivered", "overdue", "cancelled"}
VALID_PRIORITIES = {"low", "medium", "high", "critical"}
VALID_CHECKLIST_STATUSES = {"pending", "received", "approved", "rejected"}


def _require_owner_or_admin(user: User) -> None:
    if user.role.value not in ("owner", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can perform this action",
        )


# ---------------------------------------------------------------------------
# Obligation Rules
# ---------------------------------------------------------------------------

@router.get("/rules", response_model=List[ObligationRuleOut], summary="List obligation rules")
async def list_obligation_rules(
    active_only: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all available global obligation rules (catálogo global, cache de 5 min)."""
    from app.services.catalog_cache import get_obligation_rules

    return await get_obligation_rules(db, active_only)


# ---------------------------------------------------------------------------
# Obligation Instances
# ---------------------------------------------------------------------------

@router.get("/instances", response_model=List[ObligationInstanceOut], summary="List obligation instances")
async def list_obligation_instances(
    competence_month: Optional[date] = Query(None, description="Filter by competence month (YYYY-MM-DD, first day)"),
    client_id: Optional[UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    """List obligation instances for the current tenant."""
    conditions = [ObligationInstance.tenant_id == current_user.tenant_id]

    if competence_month:
        conditions.append(ObligationInstance.competence_month == competence_month)
    if client_id:
        conditions.append(ObligationInstance.client_id == client_id)
    if status_filter:
        conditions.append(ObligationInstance.status == status_filter)

    result = await db.execute(
        select(ObligationInstance)
        .where(and_(*conditions))
        .order_by(ObligationInstance.due_date, ObligationInstance.priority.desc())
    )
    return result.scalars().all()


@router.post("/instances", response_model=ObligationInstanceOut, status_code=status.HTTP_201_CREATED,
             summary="Create manual obligation instance")
async def create_obligation_instance(
    body: CreateObligationInstanceRequest,
    current_user: User = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    """Create a manual obligation instance (not auto-generated)."""
    _require_owner_or_admin(current_user)

    if body.status not in VALID_INSTANCE_STATUSES:
        raise HTTPException(422, f"Invalid status. Valid: {sorted(VALID_INSTANCE_STATUSES)}")
    if body.priority not in VALID_PRIORITIES:
        raise HTTPException(422, f"Invalid priority. Valid: {sorted(VALID_PRIORITIES)}")

    await ensure_client_in_tenant(db, current_user.tenant_id, body.client_id)
    instance = ObligationInstance(
        tenant_id=current_user.tenant_id,
        client_id=body.client_id,
        rule_id=body.rule_id,
        competence_month=body.competence_month,
        due_date=body.due_date,
        status=body.status,
        priority=body.priority,
        assigned_to=body.assigned_to,
        notes=_compose_notes(body.custom_name if body.rule_id is None else None, body.notes),
    )
    db.add(instance)
    await db.commit()
    await db.refresh(instance)
    return instance


@router.patch("/instances/{instance_id}", response_model=ObligationInstanceOut,
              summary="Update obligation instance")
async def update_obligation_instance(
    instance_id: UUID,
    body: UpdateObligationInstanceRequest,
    current_user: User = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
):
    """Update status, assignment, or notes of an obligation instance."""
    result = await db.execute(
        select(ObligationInstance).where(
            and_(
                ObligationInstance.id == instance_id,
                ObligationInstance.tenant_id == current_user.tenant_id,
            )
        )
    )
    instance = result.scalar_one_or_none()
    if not instance:
        raise HTTPException(status_code=404, detail="Obligation instance not found")

    became_delivered = False
    if body.status is not None:
        if body.status not in VALID_INSTANCE_STATUSES:
            raise HTTPException(422, f"Invalid status. Valid: {sorted(VALID_INSTANCE_STATUSES)}")
        became_delivered = body.status == "delivered" and instance.status != "delivered"
        instance.status = body.status
        if body.status == "delivered" and not instance.completed_at:
            instance.completed_at = datetime.utcnow()

    if body.priority is not None:
        if body.priority not in VALID_PRIORITIES:
            raise HTTPException(422, f"Invalid priority. Valid: {sorted(VALID_PRIORITIES)}")
        instance.priority = body.priority

    if body.assigned_to is not None:
        instance.assigned_to = body.assigned_to
    if body.delivery_proof is not None:
        instance.delivery_proof = body.delivery_proof
    if body.notes is not None:
        # Preserva o nome da avulsa ao editar as observações.
        current_name, _ = _split_notes(instance.notes)
        instance.notes = _compose_notes(current_name, body.notes or None)

    await db.commit()
    await db.refresh(instance)
    if became_delivered:
        await _webhook_svc.dispatch_event(
            db=db,
            tenant_id=current_user.tenant_id,
            event="obligation.completed",
            data={
                "id": str(instance.id),
                "client_id": str(instance.client_id),
                "rule_id": str(instance.rule_id) if instance.rule_id else None,
                "competence_month": instance.competence_month,
                "status": instance.status,
                "completed_at": instance.completed_at.isoformat() if instance.completed_at else None,
            },
        )
    return instance


@router.delete("/instances/{instance_id}", response_model=ObligationInstanceOut,
               summary="Cancel obligation instance (soft delete)")
async def cancel_obligation_instance(
    instance_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Exclusão lógica: marca a obrigação como `cancelled`.

    Idempotente (cancelar de novo devolve 200 com o mesmo estado). Obrigação já
    entregue (`delivered`) é status terminal e não pode ser cancelada (409).
    """
    result = await db.execute(
        select(ObligationInstance).where(
            and_(
                ObligationInstance.id == instance_id,
                ObligationInstance.tenant_id == current_user.tenant_id,
            )
        )
    )
    instance = result.scalar_one_or_none()
    if not instance:
        raise HTTPException(status_code=404, detail="Obligation instance not found")
    if instance.status == "cancelled":
        return instance
    if instance.status == "delivered":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Obrigação já entregue não pode ser excluída.",
        )

    before_status = instance.status
    instance.status = "cancelled"
    await db.commit()
    await db.refresh(instance)
    await log_audit_event(
        db=db,
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        action="obligation_instance.cancel",
        entity_type="obligation_instance",
        entity_id=instance.id,
        before_data={"status": before_status},
        after_data={"status": "cancelled"},
    )
    return instance


# ---------------------------------------------------------------------------
# Client Obligation Profiles
# ---------------------------------------------------------------------------

@router.get("/profiles/{client_id}", response_model=ClientObligationProfileOut,
            summary="Get client fiscal profile")
async def get_client_profile(
    client_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the fiscal profile for a client."""
    result = await db.execute(
        select(ClientObligationProfile).where(
            and_(
                ClientObligationProfile.client_id == client_id,
                ClientObligationProfile.tenant_id == current_user.tenant_id,
            )
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Fiscal profile not found for this client")
    return profile


@router.put("/profiles/{client_id}", response_model=ClientObligationProfileOut,
            summary="Upsert client fiscal profile")
async def upsert_client_profile(
    client_id: UUID,
    body: UpsertProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or update the fiscal profile for a client."""
    _require_owner_or_admin(current_user)

    result = await db.execute(
        select(ClientObligationProfile).where(
            and_(
                ClientObligationProfile.client_id == client_id,
                ClientObligationProfile.tenant_id == current_user.tenant_id,
            )
        )
    )
    profile = result.scalar_one_or_none()

    if profile:
        # Update existing
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(profile, field, value)
    else:
        # Create new
        profile = ClientObligationProfile(
            tenant_id=current_user.tenant_id,
            client_id=client_id,
            **body.model_dump(),
        )
        db.add(profile)

    await db.commit()
    await db.refresh(profile)
    return profile


# ---------------------------------------------------------------------------
# Document Checklist
# ---------------------------------------------------------------------------

@router.get("/checklist", response_model=List[ChecklistItemOut], summary="List checklist items")
async def list_checklist_items(
    client_id: Optional[UUID] = Query(None),
    competence_month: Optional[date] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List document checklist items for the tenant."""
    conditions = [DocumentChecklistItem.tenant_id == current_user.tenant_id]

    if client_id:
        conditions.append(DocumentChecklistItem.client_id == client_id)
    if competence_month:
        conditions.append(DocumentChecklistItem.competence_month == competence_month)
    if status_filter:
        conditions.append(DocumentChecklistItem.status == status_filter)

    result = await db.execute(
        select(DocumentChecklistItem)
        .where(and_(*conditions))
        .order_by(DocumentChecklistItem.competence_month.desc(), DocumentChecklistItem.created_at)
    )
    return result.scalars().all()


@router.post("/checklist", response_model=ChecklistItemOut, status_code=status.HTTP_201_CREATED,
             summary="Add checklist item")
async def create_checklist_item(
    body: CreateChecklistItemRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a document checklist item for a client."""
    _require_owner_or_admin(current_user)

    await ensure_client_in_tenant(db, current_user.tenant_id, body.client_id)
    item = DocumentChecklistItem(
        tenant_id=current_user.tenant_id,
        client_id=body.client_id,
        obligation_id=body.obligation_id,
        competence_month=body.competence_month,
        document_name=body.document_name,
        notes=body.notes,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/checklist/{item_id}", response_model=ChecklistItemOut, summary="Update checklist item")
async def update_checklist_item(
    item_id: UUID,
    body: UpdateChecklistItemRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the status or notes of a checklist item."""
    result = await db.execute(
        select(DocumentChecklistItem).where(
            and_(
                DocumentChecklistItem.id == item_id,
                DocumentChecklistItem.tenant_id == current_user.tenant_id,
            )
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Checklist item not found")

    if body.status is not None:
        if body.status not in VALID_CHECKLIST_STATUSES:
            raise HTTPException(422, f"Invalid status. Valid: {sorted(VALID_CHECKLIST_STATUSES)}")
        item.status = body.status
        if body.status == "received" and not item.received_at:
            item.received_at = datetime.utcnow()

    if body.notes is not None:
        item.notes = body.notes

    await db.commit()
    await db.refresh(item)
    return item


# ---------------------------------------------------------------------------
# Manual trigger (owner only)
# ---------------------------------------------------------------------------

@router.post("/generate", summary="Manually trigger obligation generation (owner only)")
async def trigger_obligation_generation(
    body: GenerateObligationsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger the obligation engine for a specific month.

    Useful for backfilling obligations or testing.
    Only accessible by tenant owners.
    """
    if current_user.role.value != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can trigger manual obligation generation",
        )

    from app.services.obligation_engine import generate_obligations_for_month

    summary = await generate_obligations_for_month(
        db, body.year, body.month, tenant_id=current_user.tenant_id
    )
    return {
        "status": "completed",
        "competence_month": f"{body.year:04d}-{body.month:02d}",
        **summary,
    }
