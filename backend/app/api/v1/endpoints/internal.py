"""
Endpoints internos, chamados por infraestrutura (não pelo frontend).

POST /internal/tick — disparado de hora em hora pelo Google Cloud Scheduler
quando SCHEDULER_MODE=external. Executa as rotinas agendadas devidas naquela
hora (ver app.services.scheduler). Só toca no banco quando alguma rotina está
devida (no mínimo a diária das 08:00), o que já basta para o Supabase Free não
pausar por 7 dias sem uso — sem manter o banco ocupado nas outras horas.
"""

import hmac

from fastapi import APIRouter, Header, HTTPException, status

from app.core.config import settings
from app.services.scheduler import run_due_jobs


router = APIRouter()


@router.post(
    "/internal/tick",
    summary="Scheduler tick",
    description="Runs the scheduled jobs due this hour. Requires X-Cron-Secret.",
    tags=["Internal"],
    include_in_schema=False,
)
async def scheduler_tick(x_cron_secret: str | None = Header(default=None)):
    # Fail closed: sem CRON_SECRET configurado o endpoint não existe.
    if not settings.CRON_SECRET:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    if not x_cron_secret or not hmac.compare_digest(
        x_cron_secret.encode(), settings.CRON_SECRET.encode()
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid cron secret")
    return await run_due_jobs()
