"""
Calculator Endpoints for FiscWise - Feature #7

All endpoints under /calculator prefix:
  POST /calculator/simulate-regime    — Compare 3 regimes (all plans, AI = intermediario+)
  POST /calculator/simulate-icms     — ICMS per NCM (all plans, AI = intermediario+)
  POST /calculator/simulate-pis-cofins — PIS/COFINS (all plans, AI = intermediario+)
  POST /calculator/chat               — Chat with AI assistant (intermediario+)
  GET  /calculator/simulations        — Simulation history (all plans)
  POST /calculator/export-pdf         — PDF report (premium only)

Plan enforcement uses app.core.plan_access.
"""

import logging
import uuid
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.plan_access import (
    PLAN_INTERMEDIARIO,
    PLAN_PREMIUM,
    check_chat_quota,
    has_plan,
    require_plan,
    resolve_user_plan,
)
from app.models.calculator import (
    AssistantRole,
    CalculatorSimulation,
    FiscalAssistantMessage,
    SimulationType,
    TaxRegime,
    TaxScenario,
)
from app.models.user import User
from app.schemas.calculator import (
    AssistantMessageCreate,
    AssistantMessageResponse,
    ChatResponse,
    FatorRSimulationCreate,
    FatorRSimulationResponse,
    IcmsSimulationCreate,
    IcmsSimulationResponse,
    PdfExportRequest,
    PisCofinsSimulationCreate,
    PisCofinsSimulationResponse,
    RegimeSimulationCreate,
    RegimeSimulationResponse,
    SimulationHistoryResponse,
    SimulationListItem,
    TaxScenarioResponse,
)
from app.services.ai_fiscal import (
    chat_with_fiscal_assistant,
    generate_fator_r_recommendation,
    generate_icms_analysis,
    generate_pis_cofins_analysis,
    generate_regime_recommendation,
)
from app.services.fiscal_calculator import (
    calculate_fator_r,
    calculate_icms,
    calculate_pis_cofins,
    compare_tax_regimes,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tenant_id(current_user: User) -> uuid.UUID:
    return current_user.tenant_id


def _plan(current_user: User) -> Optional[str]:
    return resolve_user_plan(current_user)


async def _commit_refresh(db: AsyncSession, instance):
    await db.commit()
    await db.refresh(instance)
    return instance


# ---------------------------------------------------------------------------
# POST /calculator/simulate-regime
# ---------------------------------------------------------------------------


@router.post(
    "/simulate-regime",
    response_model=RegimeSimulationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Comparar regimes tributários",
    description=(
        "Compara Simples Nacional, Lucro Presumido e Lucro Real para a receita informada. "
        "Todos os planos têm acesso. Recomendação por IA disponível no plano Intermediário+"
    ),
)
async def simulate_regime(
    payload: RegimeSimulationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RegimeSimulationResponse:
    tenant_id = _tenant_id(current_user)
    plan = _plan(current_user)

    # ── Deterministic calculation (all plans) ────────────────────────────────
    scenarios_data = compare_tax_regimes(
        annual_revenue=payload.annual_revenue,
        annual_costs=payload.annual_costs,
        annual_payroll=payload.annual_payroll,
        activity_code=payload.activity_code,
        cogs=payload.cogs,
    )

    # ── AI recommendation (INTERMEDIARIO+ only) ───────────────────────────────
    ai_recommendation: Optional[str] = None
    if has_plan(plan, PLAN_INTERMEDIARIO):
        ai_recommendation = await generate_regime_recommendation(
            annual_revenue=payload.annual_revenue,
            annual_costs=payload.annual_costs,
            annual_payroll=payload.annual_payroll,
            scenarios=scenarios_data,
            activity_code=payload.activity_code,
        )

    # ── Persist simulation ────────────────────────────────────────────────────
    input_data = payload.model_dump(mode="json")
    result_data = {"scenarios": scenarios_data}

    simulation = CalculatorSimulation(
        tenant_id=tenant_id,
        simulation_type=SimulationType.REGIME,
        title=payload.title or f"Simulação de Regime — R$ {float(payload.annual_revenue):,.2f}",
        input_data=input_data,
        result_data=result_data,
        ai_recommendation=ai_recommendation,
        plan_slug=plan,
    )
    db.add(simulation)
    await db.flush()  # get simulation.id before persisting scenarios

    # Persist individual scenarios
    scenario_objects = []
    for s in scenarios_data:
        if s.get("ineligible"):
            continue
        regime_map = {
            "simples_nacional": TaxRegime.SIMPLES_NACIONAL,
            "lucro_presumido": TaxRegime.LUCRO_PRESUMIDO,
            "lucro_real": TaxRegime.LUCRO_REAL,
        }
        regime_enum = regime_map.get(s["regime"])
        if regime_enum is None:
            continue
        scenario = TaxScenario(
            tenant_id=tenant_id,
            simulation_id=simulation.id,
            regime=regime_enum,
            annual_revenue=Decimal(str(s["annual_revenue"])),
            effective_rate=Decimal(str(s["effective_rate"])),
            total_tax=Decimal(str(s["total_tax"])),
            tax_breakdown=s["tax_breakdown"],
            is_recommended=s.get("is_recommended", False),
        )
        db.add(scenario)
        scenario_objects.append(scenario)

    await db.commit()
    await db.refresh(simulation)
    for sc in scenario_objects:
        await db.refresh(sc)

    # Build response
    scenario_responses = [
        TaxScenarioResponse(
            id=sc.id,
            regime=sc.regime,
            annual_revenue=sc.annual_revenue,
            effective_rate=sc.effective_rate,
            total_tax=sc.total_tax,
            tax_breakdown=sc.tax_breakdown,
            is_recommended=sc.is_recommended,
        )
        for sc in scenario_objects
    ]

    return RegimeSimulationResponse(
        id=simulation.id,
        simulation_type=simulation.simulation_type,
        title=simulation.title,
        input_data=simulation.input_data,
        result_data=simulation.result_data,
        ai_recommendation=simulation.ai_recommendation,
        scenarios=scenario_responses,
        created_at=simulation.created_at,
    )


# ---------------------------------------------------------------------------
# POST /calculator/simulate-icms
# ---------------------------------------------------------------------------


@router.post(
    "/simulate-icms",
    response_model=IcmsSimulationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Calcular ICMS por NCM",
    description=(
        "Calcula ICMS para operação interestadual dado NCM, estados e valor. "
        "Inclui cálculo de DIFAL quando o comprador é consumidor final. "
        "Análise de IA disponível no plano Intermediário+."
    ),
)
async def simulate_icms(
    payload: IcmsSimulationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IcmsSimulationResponse:
    tenant_id = _tenant_id(current_user)
    plan = _plan(current_user)

    result_data = calculate_icms(
        ncm_code=payload.ncm_code,
        origin_state=payload.origin_state,
        destination_state=payload.destination_state,
        operation_value=payload.operation_value,
        is_buyer_taxpayer=payload.is_buyer_taxpayer,
    )

    ai_recommendation: Optional[str] = None
    if has_plan(plan, PLAN_INTERMEDIARIO):
        ai_recommendation = await generate_icms_analysis(result_data)

    simulation = CalculatorSimulation(
        tenant_id=tenant_id,
        simulation_type=SimulationType.ICMS,
        title=(
            payload.title
            or f"ICMS {payload.origin_state}→{payload.destination_state} NCM {payload.ncm_code}"
        ),
        input_data=payload.model_dump(mode="json"),
        result_data=result_data,
        ai_recommendation=ai_recommendation,
        plan_slug=plan,
    )
    db.add(simulation)
    await _commit_refresh(db, simulation)

    return IcmsSimulationResponse(
        id=simulation.id,
        simulation_type=simulation.simulation_type,
        title=simulation.title,
        input_data=simulation.input_data,
        result_data=simulation.result_data,
        ai_recommendation=simulation.ai_recommendation,
        created_at=simulation.created_at,
    )


# ---------------------------------------------------------------------------
# POST /calculator/simulate-pis-cofins
# ---------------------------------------------------------------------------


@router.post(
    "/simulate-pis-cofins",
    response_model=PisCofinsSimulationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Calcular PIS/COFINS",
    description=(
        "Calcula PIS e COFINS mensais (cumulativo ou não-cumulativo). "
        "Análise de IA disponível no plano Intermediário+."
    ),
)
async def simulate_pis_cofins(
    payload: PisCofinsSimulationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PisCofinsSimulationResponse:
    tenant_id = _tenant_id(current_user)
    plan = _plan(current_user)

    result_data = calculate_pis_cofins(
        monthly_revenue=payload.monthly_revenue,
        is_non_cumulative=payload.is_non_cumulative,
        deductible_credits=payload.deductible_credits,
    )

    ai_recommendation: Optional[str] = None
    if has_plan(plan, PLAN_INTERMEDIARIO):
        ai_recommendation = await generate_pis_cofins_analysis(
            result_data,
            activity_description=payload.activity_description,
        )

    regime_label = "Não-cumulativo" if payload.is_non_cumulative else "Cumulativo"
    simulation = CalculatorSimulation(
        tenant_id=tenant_id,
        simulation_type=SimulationType.PIS_COFINS,
        title=(
            payload.title
            or f"PIS/COFINS {regime_label} — R$ {float(payload.monthly_revenue):,.2f}/mês"
        ),
        input_data=payload.model_dump(mode="json"),
        result_data=result_data,
        ai_recommendation=ai_recommendation,
        plan_slug=plan,
    )
    db.add(simulation)
    await _commit_refresh(db, simulation)

    return PisCofinsSimulationResponse(
        id=simulation.id,
        simulation_type=simulation.simulation_type,
        title=simulation.title,
        input_data=simulation.input_data,
        result_data=simulation.result_data,
        ai_recommendation=simulation.ai_recommendation,
        created_at=simulation.created_at,
    )


# ---------------------------------------------------------------------------
# POST /calculator/simulate-fator-r
# ---------------------------------------------------------------------------


@router.post(
    "/simulate-fator-r",
    response_model=FatorRSimulationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Simulação de Fator R e DAS",
    description=(
        "Calcula o Fator R (folha/receita) para determinar se a empresa se enquadra "
        "no Anexo III ou V do Simples Nacional. Inclui cálculo mensal do DAS e "
        "comparação com o anexo alternativo. Análise de IA disponível no plano Intermediário+."
    ),
)
async def simulate_fator_r(
    payload: FatorRSimulationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FatorRSimulationResponse:
    tenant_id = _tenant_id(current_user)
    plan = _plan(current_user)

    # ── Extract monthly data from payload ─────────────────────────────────────
    monthly_revenues = [m.revenue for m in payload.months]
    monthly_payrolls = [m.total_payroll for m in payload.months]

    # ── Deterministic calculation (all plans) ────────────────────────────────
    result_data = calculate_fator_r(
        monthly_revenues=monthly_revenues,
        monthly_payrolls=monthly_payrolls,
    )

    # ── AI recommendation (INTERMEDIARIO+ only) ───────────────────────────────
    ai_recommendation: Optional[str] = None
    if has_plan(plan, PLAN_INTERMEDIARIO):
        ai_recommendation = await generate_fator_r_recommendation(result_data)

    # ── Persist simulation ────────────────────────────────────────────────────
    input_data = payload.model_dump(mode="json")

    simulation = CalculatorSimulation(
        tenant_id=tenant_id,
        simulation_type=SimulationType.FATOR_R,
        title=(
            payload.title
            or f"Fator R — {result_data['fator_r_percent']} (Anexo {result_data['anexo']})"
        ),
        input_data=input_data,
        result_data=result_data,
        ai_recommendation=ai_recommendation,
        plan_slug=plan,
    )
    db.add(simulation)
    await _commit_refresh(db, simulation)

    return FatorRSimulationResponse(
        id=simulation.id,
        simulation_type=simulation.simulation_type,
        title=simulation.title,
        rbt12=Decimal(str(result_data["rbt12"])),
        folha_12m=Decimal(str(result_data["folha_12m"])),
        fator_r=Decimal(str(result_data["fator_r"])),
        fator_r_percent=result_data["fator_r_percent"],
        anexo=result_data["anexo"],
        monthly_details=result_data["monthly_details"],
        total_das_anual=Decimal(str(result_data["total_das_anual"])),
        comparison=result_data["comparison"],
        ai_recommendation=simulation.ai_recommendation,
        created_at=simulation.created_at,
    )


# ---------------------------------------------------------------------------
# POST /calculator/chat
# ---------------------------------------------------------------------------


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Chat com assistente fiscal (IA)",
    description=(
        "Envia uma mensagem para o assistente fiscal com IA. "
        "Plano Intermediário: 20 mensagens/mês. Plano Premium: ilimitado. "
        "Plano Free: acesso negado."
    ),
)
async def chat(
    payload: AssistantMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    tenant_id = _tenant_id(current_user)
    plan = _plan(current_user)

    # Enforce plan access
    require_plan(plan, PLAN_INTERMEDIARIO, "Chat com assistente fiscal")

    # Check monthly quota
    has_quota, remaining = await check_chat_quota(tenant_id, plan, db)
    if not has_quota:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Você atingiu o limite de 20 mensagens mensais do plano Intermediário. "
                "Faça upgrade para o plano Premium para ter acesso ilimitado."
            ),
        )

    # Fetch simulation context if linked
    simulation_context: Optional[dict] = None
    if payload.simulation_id:
        result = await db.execute(
            select(CalculatorSimulation).where(
                CalculatorSimulation.id == payload.simulation_id,
                CalculatorSimulation.tenant_id == tenant_id,
            )
        )
        sim = result.scalar_one_or_none()
        if sim:
            simulation_context = {
                "simulation_type": sim.simulation_type.value,
                "result_data": sim.result_data,
            }

    # Fetch recent conversation history for context
    history_result = await db.execute(
        select(FiscalAssistantMessage)
        .where(
            FiscalAssistantMessage.tenant_id == tenant_id,
            FiscalAssistantMessage.simulation_id == payload.simulation_id,
        )
        .order_by(FiscalAssistantMessage.created_at.asc())
        .limit(20)
    )
    history_msgs = history_result.scalars().all()
    conversation_history = [
        {"role": msg.role.value, "content": msg.content}
        for msg in history_msgs
    ]

    # Persist user message
    user_msg = FiscalAssistantMessage(
        tenant_id=tenant_id,
        simulation_id=payload.simulation_id,
        role=AssistantRole.USER,
        content=payload.content,
        tokens_used=None,
    )
    db.add(user_msg)
    await db.flush()

    # Call AI
    ai_response, tokens_used = await chat_with_fiscal_assistant(
        user_message=payload.content,
        conversation_history=conversation_history,
        simulation_context=simulation_context,
    )

    # Persist assistant message
    assistant_msg = FiscalAssistantMessage(
        tenant_id=tenant_id,
        simulation_id=payload.simulation_id,
        role=AssistantRole.ASSISTANT,
        content=ai_response or "Desculpe, não foi possível processar sua mensagem.",
        tokens_used=tokens_used,
    )
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(user_msg)
    await db.refresh(assistant_msg)

    # Re-check remaining after persisting
    _, remaining_after = await check_chat_quota(tenant_id, plan, db)

    return ChatResponse(
        user_message=AssistantMessageResponse(
            id=user_msg.id,
            role=user_msg.role,
            content=user_msg.content,
            simulation_id=user_msg.simulation_id,
            tokens_used=user_msg.tokens_used,
            created_at=user_msg.created_at,
        ),
        assistant_message=AssistantMessageResponse(
            id=assistant_msg.id,
            role=assistant_msg.role,
            content=assistant_msg.content,
            simulation_id=assistant_msg.simulation_id,
            tokens_used=assistant_msg.tokens_used,
            created_at=assistant_msg.created_at,
        ),
        remaining_quota=remaining_after,
    )


# ---------------------------------------------------------------------------
# GET /calculator/simulations
# ---------------------------------------------------------------------------


@router.get(
    "/simulations",
    response_model=SimulationHistoryResponse,
    summary="Histórico de simulações",
    description="Lista todas as simulações do tenant, paginada. Disponível em todos os planos.",
)
async def list_simulations(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    simulation_type: Optional[str] = Query(
        default=None,
        description="Filter by type: regime, icms, pis_cofins",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SimulationHistoryResponse:
    tenant_id = _tenant_id(current_user)

    base_query = select(CalculatorSimulation).where(
        CalculatorSimulation.tenant_id == tenant_id
    )

    if simulation_type:
        try:
            sim_type_enum = SimulationType(simulation_type)
            base_query = base_query.where(
                CalculatorSimulation.simulation_type == sim_type_enum
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid simulation_type '{simulation_type}'. "
                       f"Valid values: regime, icms, pis_cofins",
            )

    # Count total
    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = int(count_result.scalar_one() or 0)

    # Fetch page
    offset = (page - 1) * page_size
    items_result = await db.execute(
        base_query
        .order_by(CalculatorSimulation.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    simulations = items_result.scalars().all()

    return SimulationHistoryResponse(
        items=[
            SimulationListItem(
                id=sim.id,
                simulation_type=sim.simulation_type,
                title=sim.title,
                plan_slug=sim.plan_slug,
                input_data=sim.input_data,
                result_data=sim.result_data,
                created_at=sim.created_at,
            )
            for sim in simulations
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# POST /calculator/export-pdf
# ---------------------------------------------------------------------------


@router.post(
    "/export-pdf",
    summary="Exportar relatório PDF (Premium)",
    description="Gera e retorna um relatório PDF da simulação. Disponível apenas no plano Premium.",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "PDF report",
        }
    },
)
async def export_pdf(
    payload: PdfExportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    tenant_id = _tenant_id(current_user)
    plan = _plan(current_user)

    # Enforce PREMIUM plan
    require_plan(plan, PLAN_PREMIUM, "Exportação de relatório PDF")

    # Fetch simulation
    result = await db.execute(
        select(CalculatorSimulation).where(
            CalculatorSimulation.id == payload.simulation_id,
            CalculatorSimulation.tenant_id == tenant_id,
        )
    )
    simulation = result.scalar_one_or_none()
    if simulation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulation not found",
        )

    # Generate PDF
    pdf_bytes = _generate_pdf(simulation, payload.include_ai_recommendation)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="fiscwise-relatorio-{simulation.id}.pdf"'
            ),
        },
    )


def _generate_pdf(simulation: CalculatorSimulation, include_ai: bool) -> bytes:
    """
    Generate a basic PDF report for a simulation.

    Uses only the standard library (no reportlab/weasyprint dependency for MVP).
    Generates a minimal valid PDF manually.

    For production quality, replace with reportlab or WeasyPrint.
    """
    import io

    sim_type_labels = {
        "regime": "Comparação de Regimes Tributários",
        "icms": "Simulação de ICMS",
        "pis_cofins": "Simulação de PIS/COFINS",
    }
    type_label = sim_type_labels.get(simulation.simulation_type.value, "Simulação Fiscal")

    lines = [
        "FiscWise — Relatório de Simulação Fiscal",
        "=" * 48,
        f"Tipo: {type_label}",
        f"Título: {simulation.title or 'N/A'}",
        f"Data: {simulation.created_at.strftime('%d/%m/%Y %H:%M')}",
        f"Plano: {simulation.plan_slug or 'free'}",
        "",
        "DADOS DE ENTRADA",
        "-" * 48,
    ]

    for k, v in (simulation.input_data or {}).items():
        lines.append(f"  {k}: {v}")

    lines += [
        "",
        "RESULTADO",
        "-" * 48,
    ]

    result = simulation.result_data or {}
    scenarios = result.get("scenarios", [])
    if scenarios:
        for s in scenarios:
            regime = s.get("regime", "N/A").upper()
            rate = s.get("effective_rate", 0)
            total = s.get("total_tax", 0)
            rec = " ← RECOMENDADO" if s.get("is_recommended") else ""
            lines.append(f"  {regime}: alíquota {rate*100:.2f}% | imposto R$ {total:,.2f}{rec}")
    else:
        for k, v in result.items():
            lines.append(f"  {k}: {v}")

    if include_ai and simulation.ai_recommendation:
        lines += [
            "",
            "RECOMENDAÇÃO DA IA",
            "-" * 48,
            simulation.ai_recommendation,
        ]

    lines += [
        "",
        "-" * 48,
        "Relatório gerado pelo FiscWise (fiscwise.com.br)",
        "Este relatório é informativo. Consulte um contador para decisões definitivas.",
    ]

    # Build minimal PDF structure
    objects: list[bytes] = []

    def add_obj(content: bytes) -> int:
        objects.append(content)
        return len(objects)

    # Object 1: Catalog
    add_obj(b"<< /Type /Catalog /Pages 2 0 R >>")

    # Object 2: Pages
    add_obj(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")

    # Object 3: Page
    add_obj(
        b"<< /Type /Page /Parent 2 0 R "
        b"/MediaBox [0 0 595 842] "
        b"/Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>"
    )

    # Object 4: Content stream
    # Split into lines and render with simple text positioning
    stream_lines = []
    y = 800
    stream_lines.append(b"BT")
    stream_lines.append(b"/F1 10 Tf")
    for line in lines:
        safe_line = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        safe_bytes = safe_line.encode("latin-1", errors="replace")
        stream_lines.append(f"40 {y} Td".encode())
        stream_lines.append(b"0 0 Td")
        stream_lines.append(b"(" + safe_bytes + b") Tj")
        y -= 14
        if y < 40:
            # Simple page overflow prevention — stop rendering
            break
    stream_lines.append(b"ET")

    stream_content = b"\n".join(stream_lines)
    add_obj(
        b"<< /Length " + str(len(stream_content)).encode() + b" >>\n"
        b"stream\n" + stream_content + b"\nendstream"
    )

    # Object 5: Font
    add_obj(
        b"<< /Type /Font /Subtype /Type1 "
        b"/BaseFont /Courier /Encoding /WinAnsiEncoding >>"
    )

    # Build PDF bytes
    buf = io.BytesIO()
    buf.write(b"%PDF-1.4\n")

    offsets: list[int] = []
    for i, obj_content in enumerate(objects, start=1):
        offsets.append(buf.tell())
        buf.write(f"{i} 0 obj\n".encode())
        buf.write(obj_content)
        buf.write(b"\nendobj\n")

    xref_offset = buf.tell()
    buf.write(b"xref\n")
    buf.write(f"0 {len(objects) + 1}\n".encode())
    buf.write(b"0000000000 65535 f \n")
    for offset in offsets:
        buf.write(f"{offset:010d} 00000 n \n".encode())

    buf.write(b"trailer\n")
    buf.write(f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode())
    buf.write(b"startxref\n")
    buf.write(f"{xref_offset}\n".encode())
    buf.write(b"%%EOF\n")

    return buf.getvalue()
