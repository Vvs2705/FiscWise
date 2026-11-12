"""Status dos jobs da fila em segundo plano (somente leitura, do escritório do usuário).

GET /api/v1/jobs/{id}
GET /api/v1/jobs?status=&limit=
"""

import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.background_job import BackgroundJob
from app.models.user import User

router = APIRouter()

JobStatus = Literal["queued", "running", "done", "failed", "cancelled"]


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    status: str
    attempts: int
    max_attempts: int
    last_error: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    run_after: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


@router.get("/jobs/{job_id}", response_model=JobOut, summary="Status de um job")
async def get_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Filtro explícito por tenant além do RLS (jobs globais, tenant_id NULL, nunca aparecem).
    job = (
        await db.execute(
            select(BackgroundJob).where(
                BackgroundJob.id == job_id, BackgroundJob.tenant_id == current_user.tenant_id
            )
        )
    ).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job não encontrado")
    return job


@router.get("/jobs", response_model=list[JobOut], summary="Jobs recentes do escritório")
async def list_jobs(
    status_filter: Optional[JobStatus] = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(BackgroundJob).where(BackgroundJob.tenant_id == current_user.tenant_id)
    if status_filter:
        stmt = stmt.where(BackgroundJob.status == status_filter)
    stmt = stmt.order_by(BackgroundJob.created_at.desc()).limit(limit)
    return list((await db.execute(stmt)).scalars().all())
