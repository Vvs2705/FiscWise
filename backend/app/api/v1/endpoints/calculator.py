"""Fiscal Calculator endpoints — Feature #7."""

import logging
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.plan_access import (
    has_ai_access,
    has_pdf_export,
    require_ai_access,
    require_pdf_export,
)
from app.models.calculator import CalculatorSimulation, FiscalAssistantMessage, SimulationStatus
from app.models.user import User
from app.schemas.calculator import (
    ChatRequest,
    ChatResponse,
    SimulateIcmsRequest,
    SimulateIcmsResponse,
    SimulatePisCofinsRequest,
    SimulatePisCofinsResponse,
    SimulateRegimeRequest,
    SimulateRegimeResponse,
    SimulationDetailResponse,
    SimulationHistoryItem,
    TaxRegimeResult,
)
from app.services import fiscal_calculator as calc
from app.services import ai_fiscal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calculator", tags=["Calculator"])


# ---------------------------------------------------------------------------
# Regime simulation
# ---------------------------------------------------------------------------

@router.post("/simulate-regime", response_model=SimulateRegimeResponse)
async def simulate_regime(
    body: SimulateRegimeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SimulateRegimeResponse:
    """Simulate all fiscal regimes and return best recommendation.

    - FREE plan: returns raw numbers only, no AI recommendation.
    - INTERMEDIARIO/PREMIUM: includes AI-generated recommendation.
    """
    results_raw, recommended_regime = calc.compare_regimes(
        annual_revenue=body.annual_revenue,
        activity_type=body.activity_type,
        payroll_total=body.payroll_total,
    )

    # Fetch tenant for plan check
    tenant = current_user.tenant
    plan_required_for_ai: Optional[str] = None
    ai_recommendation: Optional[str] = None

    if has_ai_access(tenant):
        try:
            ai_recommendation = await ai_fiscal.generate_regime_recommendation(
                annual_revenue=body.annual_revenue,
                activity_type=body.activity_type,
                recommended_regime=recommended_regime,
                results=results_raw,
            )
        except Exception as exc:
            logger.warning("AI recommendation generation failed: %s", exc)
    else:
        plan_required_for_ai = "intermediario"

    # Persist simulation
    simulation = CalculatorSimulation(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        client_id=body.client_id,
        annual_revenue=body.annual_revenue,
        activity_type=body.activity_type,
        cnae_code=body.cnae_code,
        state=body.state,
        has_employees=body.has_employees,
        employee_count=body.employee_count,
        payroll_total=body.payroll_total,
        results=[{k: str(v) if hasattr(v, '__class__') and v.__class__.__name__ == 'Decimal' else v for k, v in r.items()} for r in results_raw],
        recommended_regime=recommended_regime,
        ai_recommendation=ai_recommendation,
        status=SimulationStatus.COMPLETED,
        completed_at=datetime.utcnow(),
    )
    db.add(simulation)
    await db.commit()
    await db.refresh(simulation)

    regime_results = [TaxRegimeResult(**r) for r in results_raw]

    return SimulateRegimeResponse(
        simulation_id=simulation.id,
        annual_revenue=body.annual_revenue,
        results=regime_results,
        recommended_regime=recommended_regime,
        ai_recommendation=ai_recommendation,
        plan_required_for_ai=plan_required_for_ai,
    )


# ---------------------------------------------------------------------------
# ICMS simulation (stateless — no persistence)
# ---------------------------------------------------------------------------

@router.post("/simulate-icms", response_model=SimulateIcmsResponse)
async def simulate_icms(
    body: SimulateIcmsRequest,
    current_user: User = Depends(get_current_user),
) -> SimulateIcmsResponse:
    """Calculate inter-state ICMS and DIFAL."""
    result = calc.simulate_icms(
        origin_state=body.origin_state,
        destination_state=body.destination_state,
        transaction_value=body.transaction_value,
    )
    return SimulateIcmsResponse(**result)


# ---------------------------------------------------------------------------
# PIS/COFINS simulation (stateless)
# ---------------------------------------------------------------------------

@router.post("/simulate-pis-cofins", response_model=SimulatePisCofinsResponse)
async def simulate_pis_cofins(
    body: SimulatePisCofinsRequest,
    current_user: User = Depends(get_current_user),
) -> SimulatePisCofinsResponse:
    """Calculate monthly PIS/COFINS tax burden."""
    result = calc.simulate_pis_cofins(
        regime=body.regime,
        monthly_revenue=body.monthly_revenue,
        deductible_costs=body.deductible_costs,
    )
    return SimulatePisCofinsResponse(**result)


# ---------------------------------------------------------------------------
# AI Chat
# ---------------------------------------------------------------------------

@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """Chat with the AI fiscal assistant.

    Requires INTERMEDIARIO or PREMIUM plan.
    """
    require_ai_access(current_user.tenant)

    simulation_context: Optional[dict] = None
    if body.simulation_id:
        sim = await db.execute(
            select(CalculatorSimulation).where(
                CalculatorSimulation.id == body.simulation_id,
                CalculatorSimulation.tenant_id == current_user.tenant_id,
            )
        )
        sim_obj = sim.scalar_one_or_none()
        if sim_obj:
            simulation_context = {
                "annual_revenue": str(sim_obj.annual_revenue),
                "activity_type": sim_obj.activity_type,
                "recommended_regime": sim_obj.recommended_regime,
            }

    history = [{"role": m.role, "content": m.content} for m in body.history]

    try:
        reply, tokens_used = await ai_fiscal.chat_with_fiscal_assistant(
            user_message=body.message,
            history=history,
            simulation_context=simulation_context,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    # Persist both turns
    user_msg = FiscalAssistantMessage(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        simulation_id=body.simulation_id,
        role="user",
        content=body.message,
        tokens_used=0,
    )
    assistant_msg = FiscalAssistantMessage(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        simulation_id=body.simulation_id,
        role="assistant",
        content=reply,
        tokens_used=tokens_used,
    )
    db.add_all([user_msg, assistant_msg])
    await db.commit()

    return ChatResponse(
        message=reply,
        simulation_id=body.simulation_id,
        tokens_used=tokens_used,
    )


# ---------------------------------------------------------------------------
# Simulation history
# ---------------------------------------------------------------------------

@router.get("/simulations", response_model=list[SimulationHistoryItem])
async def list_simulations(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SimulationHistoryItem]:
    """List past simulations for the current user."""
    result = await db.execute(
        select(CalculatorSimulation)
        .where(
            CalculatorSimulation.tenant_id == current_user.tenant_id,
            CalculatorSimulation.user_id == current_user.id,
        )
        .order_by(CalculatorSimulation.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    simulations = result.scalars().all()
    return [SimulationHistoryItem.model_validate(s) for s in simulations]


@router.get("/simulations/{simulation_id}", response_model=SimulationDetailResponse)
async def get_simulation(
    simulation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SimulationDetailResponse:
    """Get details of a specific simulation."""
    result = await db.execute(
        select(CalculatorSimulation).where(
            CalculatorSimulation.id == simulation_id,
            CalculatorSimulation.tenant_id == current_user.tenant_id,
        )
    )
    sim = result.scalar_one_or_none()
    if not sim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found")
    return SimulationDetailResponse.model_validate(sim)


# ---------------------------------------------------------------------------
# PDF Export (PREMIUM only)
# ---------------------------------------------------------------------------

@router.get("/simulations/{simulation_id}/export-pdf")
async def export_simulation_pdf(
    simulation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Export a simulation as PDF.

    Requires PREMIUM plan.
    """
    require_pdf_export(current_user.tenant)

    result = await db.execute(
        select(CalculatorSimulation).where(
            CalculatorSimulation.id == simulation_id,
            CalculatorSimulation.tenant_id == current_user.tenant_id,
        )
    )
    sim = result.scalar_one_or_none()
    if not sim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found")

    pdf_content = _generate_simulation_pdf(sim)

    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="simulacao-fiscal-{simulation_id}.pdf"'
        },
    )


def _generate_simulation_pdf(sim: CalculatorSimulation) -> bytes:
    """Generate a minimal PDF for the simulation.

    Uses reportlab if available, falls back to a plain-text PDF stub.
    """
    try:
        import io
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("Relatório de Simulação Fiscal", styles["Title"]))
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"Faturamento anual: R$ {sim.annual_revenue:,.2f}", styles["Normal"]))
        story.append(Paragraph(f"Atividade: {sim.activity_type}", styles["Normal"]))
        story.append(Paragraph(f"Regime recomendado: {sim.recommended_regime or 'N/A'}", styles["Normal"]))
        story.append(Spacer(1, 12))

        if sim.ai_recommendation:
            story.append(Paragraph("Recomendação IA", styles["Heading2"]))
            story.append(Paragraph(sim.ai_recommendation, styles["Normal"]))

        doc.build(story)
        return buffer.getvalue()

    except ImportError:
        logger.warning("reportlab not installed; returning minimal PDF stub")
        # Minimal valid PDF stub
        return (
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj "
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj "
            b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj "
            b"xref\n0 4\n0000000000 65535 f \n"
            b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n0\n%%EOF"
        )
