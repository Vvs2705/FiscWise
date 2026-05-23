"""Integration tests for the Fiscal Calculator API endpoints."""

import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta
import pytest
from unittest.mock import AsyncMock, patch

from app.models.calculator import CalculatorSimulation, SimulationType, FiscalAssistantMessage, AssistantRole, TaxRegime, TaxScenario
from app.core.plan_access import PLAN_FREE, PLAN_INTERMEDIARIO, PLAN_PREMIUM
from app.schemas.calculator import RegimeSimulationCreate, IcmsSimulationCreate, PisCofinsSimulationCreate, AssistantMessageCreate, PdfExportRequest

@pytest.fixture
def mock_ai_services():
    """Mock the OpenAI integration services to avoid hitting the actual API."""
    with patch("app.api.v1.endpoints.calculator.generate_regime_recommendation", new_callable=AsyncMock) as mock_regime, \
         patch("app.api.v1.endpoints.calculator.generate_icms_analysis", new_callable=AsyncMock) as mock_icms, \
         patch("app.api.v1.endpoints.calculator.generate_pis_cofins_analysis", new_callable=AsyncMock) as mock_pis_cofins, \
         patch("app.api.v1.endpoints.calculator.chat_with_fiscal_assistant", new_callable=AsyncMock) as mock_chat:
        
        mock_regime.return_value = "Recomendação Mock Simples Nacional"
        mock_icms.return_value = "Análise Mock ICMS"
        mock_pis_cofins.return_value = "Análise Mock PIS/COFINS"
        mock_chat.return_value = ("Resposta Mock Chat", 150)
        
        yield {
            "regime": mock_regime,
            "icms": mock_icms,
            "pis_cofins": mock_pis_cofins,
            "chat": mock_chat
        }

@pytest.mark.asyncio
async def test_simulate_regime_free_plan(client_with_auth_a, test_db, mock_ai_services):
    """POST /calculator/simulate-regime on FREE plan does not call AI but returns calculations."""
    client, user_a, _, _ = client_with_auth_a
    
    # Ensure tenant A has FREE plan
    user_a.tenant.plan_slug = PLAN_FREE
    await test_db.commit()

    payload = RegimeSimulationCreate(
        annual_revenue=Decimal("120000.00"),
        annual_costs=Decimal("40000.00"),
        annual_payroll=Decimal("20000.00"),
        activity_code="6201500",
        title="Simulacao Teste Free"
    )

    response = client.post(
        "/api/v1/calculator/simulate-regime",
        json=payload.model_dump(mode="json"),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Simulacao Teste Free"
    assert data["ai_recommendation"] is None
    assert len(data["scenarios"]) == 3
    mock_ai_services["regime"].assert_not_called()

@pytest.mark.asyncio
async def test_simulate_regime_intermediario_plan(client_with_auth_a, test_db, mock_ai_services):
    """POST /calculator/simulate-regime on INTERMEDIARIO plan generates AI recommendation."""
    client, user_a, _, _ = client_with_auth_a
    
    # Upgrade tenant A to INTERMEDIARIO
    user_a.tenant.plan_slug = PLAN_INTERMEDIARIO
    await test_db.commit()

    payload = RegimeSimulationCreate(
        annual_revenue=Decimal("120000.00"),
        annual_costs=Decimal("40000.00"),
        annual_payroll=Decimal("20000.00"),
        activity_code="6201500",
        title="Simulacao Teste Intermediario"
    )

    response = client.post(
        "/api/v1/calculator/simulate-regime",
        json=payload.model_dump(mode="json"),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["ai_recommendation"] == "Recomendação Mock Simples Nacional"
    mock_ai_services["regime"].assert_called_once()

@pytest.mark.asyncio
async def test_simulate_icms_success(client_with_auth_a, test_db, mock_ai_services):
    """POST /calculator/simulate-icms successfully calculates ICMS and DIFAL."""
    client, user_a, _, _ = client_with_auth_a
    user_a.tenant.plan_slug = PLAN_INTERMEDIARIO
    await test_db.commit()

    payload = IcmsSimulationCreate(
        ncm_code="8471.30.12",
        origin_state="SP",
        destination_state="RJ",
        operation_value=Decimal("100000.00"),
        is_buyer_taxpayer=False,
        title="Teste ICMS SP-RJ"
    )

    response = client.post(
        "/api/v1/calculator/simulate-icms",
        json=payload.model_dump(mode="json"),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Teste ICMS SP-RJ"
    assert data["ai_recommendation"] == "Análise Mock ICMS"
    assert data["result_data"]["difal_total"] > 0
    assert data["result_data"]["icms_interstate"] == 12000.0

@pytest.mark.asyncio
async def test_simulate_pis_cofins_success(client_with_auth_a, test_db, mock_ai_services):
    """POST /calculator/simulate-pis-cofins calculates cumulative PIS/COFINS."""
    client, user_a, _, _ = client_with_auth_a
    user_a.tenant.plan_slug = PLAN_INTERMEDIARIO
    await test_db.commit()

    payload = PisCofinsSimulationCreate(
        monthly_revenue=Decimal("100000.00"),
        is_non_cumulative=False,
        activity_description="Serviço de TI",
        title="Teste PIS/COFINS"
    )

    response = client.post(
        "/api/v1/calculator/simulate-pis-cofins",
        json=payload.model_dump(mode="json"),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Teste PIS/COFINS"
    assert data["result_data"]["total_pis_cofins"] == 3650.0 # 0.65% + 3.00%
    assert data["ai_recommendation"] == "Análise Mock PIS/COFINS"

@pytest.mark.asyncio
async def test_chat_access_denied_on_free_plan(client_with_auth_a, test_db):
    """POST /calculator/chat returns 403 Forbidden for FREE plan."""
    client, user_a, _, _ = client_with_auth_a
    user_a.tenant.plan_slug = PLAN_FREE
    await test_db.commit()

    payload = AssistantMessageCreate(content="Qual regime escolher?")

    response = client.post(
        "/api/v1/calculator/chat",
        json=payload.model_dump(mode="json"),
    )
    assert response.status_code == 403
    assert "requer o plano Intermediário" in response.json()["detail"]

@pytest.mark.asyncio
async def test_chat_success_on_intermediario_plan(client_with_auth_a, test_db, mock_ai_services):
    """POST /calculator/chat successfully handles message and updates remaining quota."""
    client, user_a, _, _ = client_with_auth_a
    user_a.tenant.plan_slug = PLAN_INTERMEDIARIO
    await test_db.commit()

    payload = AssistantMessageCreate(content="Como funciona o Lucro Presumido?")

    response = client.post(
        "/api/v1/calculator/chat",
        json=payload.model_dump(mode="json"),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["user_message"]["content"] == "Como funciona o Lucro Presumido?"
    assert data["assistant_message"]["content"] == "Resposta Mock Chat"
    # Starting quota is 20. 1 user message sent, so remaining should be 19.
    assert data["remaining_quota"] == 19

@pytest.mark.asyncio
async def test_chat_quota_limit_enforced(client_with_auth_a, test_db, mock_ai_services):
    """POST /calculator/chat returns 429 Too Many Requests when quota (20 messages) is exceeded."""
    client, user_a, _, _ = client_with_auth_a
    user_a.tenant.plan_slug = PLAN_INTERMEDIARIO
    await test_db.commit()

    # Pre-populate 20 chat messages from this user in the current calendar month
    now = datetime.now(timezone.utc)
    for i in range(20):
        msg = FiscalAssistantMessage(
            tenant_id=user_a.tenant_id,
            role=AssistantRole.USER,
            content=f"Message {i}",
            created_at=now
        )
        test_db.add(msg)
    await test_db.commit()

    payload = AssistantMessageCreate(content="Limit-breaking message")

    response = client.post(
        "/api/v1/calculator/chat",
        json=payload.model_dump(mode="json"),
    )
    assert response.status_code == 429
    assert "atingiu o limite de 20 mensagens mensais" in response.json()["detail"]

@pytest.mark.asyncio
async def test_chat_premium_plan_has_unlimited_quota(client_with_auth_a, test_db, mock_ai_services):
    """POST /calculator/chat allows messages past 20 count for PREMIUM plan."""
    client, user_a, _, _ = client_with_auth_a
    user_a.tenant.plan_slug = PLAN_PREMIUM
    await test_db.commit()

    # Pre-populate 25 chat messages from this user in the current calendar month
    now = datetime.now(timezone.utc)
    for i in range(25):
        msg = FiscalAssistantMessage(
            tenant_id=user_a.tenant_id,
            role=AssistantRole.USER,
            content=f"Message {i}",
            created_at=now
        )
        test_db.add(msg)
    await test_db.commit()

    payload = AssistantMessageCreate(content="Unlimited message")

    response = client.post(
        "/api/v1/calculator/chat",
        json=payload.model_dump(mode="json"),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["assistant_message"]["content"] == "Resposta Mock Chat"
    assert data["remaining_quota"] is None

@pytest.mark.asyncio
async def test_list_simulations(client_with_auth_a, test_db):
    """GET /calculator/simulations retrieves simulation history of the tenant."""
    client, user_a, _, _ = client_with_auth_a

    sim1 = CalculatorSimulation(
        tenant_id=user_a.tenant_id,
        simulation_type=SimulationType.REGIME,
        title="Simulation A",
        input_data={"revenue": 100000},
        result_data={"best": "simples"}
    )
    sim2 = CalculatorSimulation(
        tenant_id=user_a.tenant_id,
        simulation_type=SimulationType.ICMS,
        title="Simulation B",
        input_data={"origin": "SP"},
        result_data={"rate": 0.12}
    )
    test_db.add(sim1)
    test_db.add(sim2)
    await test_db.commit()

    response = client.get("/api/v1/calculator/simulations")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["title"] in ["Simulation A", "Simulation B"]

@pytest.mark.asyncio
async def test_export_pdf_premium_success(client_with_auth_a, test_db):
    """POST /calculator/export-pdf generates and returns PDF report for PREMIUM plan."""
    client, user_a, _, _ = client_with_auth_a
    user_a.tenant.plan_slug = PLAN_PREMIUM
    await test_db.commit()

    sim = CalculatorSimulation(
        tenant_id=user_a.tenant_id,
        simulation_type=SimulationType.REGIME,
        title="Simulation for PDF",
        input_data={"revenue": 100000},
        result_data={"scenarios": [{"regime": "simples_nacional", "effective_rate": 0.05, "total_tax": 5000.0, "is_recommended": True}]}
    )
    test_db.add(sim)
    await test_db.commit()
    await test_db.refresh(sim)

    payload = PdfExportRequest(simulation_id=sim.id)

    response = client.post(
        "/api/v1/calculator/export-pdf",
        json=payload.model_dump(mode="json"),
    )
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/pdf"
    assert b"%PDF-1.4" in response.content

@pytest.mark.asyncio
async def test_export_pdf_denied_on_free_and_intermediario(client_with_auth_a, test_db):
    """POST /calculator/export-pdf returns 403 Forbidden for FREE and INTERMEDIARIO plans."""
    client, user_a, _, _ = client_with_auth_a

    sim = CalculatorSimulation(
        tenant_id=user_a.tenant_id,
        simulation_type=SimulationType.REGIME,
        title="Simulation for PDF",
        input_data={"revenue": 100000},
        result_data={"scenarios": []}
    )
    test_db.add(sim)
    await test_db.commit()
    await test_db.refresh(sim)

    payload = PdfExportRequest(simulation_id=sim.id)

    # 1. Test FREE
    user_a.tenant.plan_slug = PLAN_FREE
    await test_db.commit()
    response = client.post(
        "/api/v1/calculator/export-pdf",
        json=payload.model_dump(mode="json"),
    )
    assert response.status_code == 403
    assert "requer o plano Premium" in response.json()["detail"]

    # 2. Test INTERMEDIARIO
    user_a.tenant.plan_slug = PLAN_INTERMEDIARIO
    await test_db.commit()
    response = client.post(
        "/api/v1/calculator/export-pdf",
        json=payload.model_dump(mode="json"),
    )
    assert response.status_code == 403
    assert "requer o plano Premium" in response.json()["detail"]

@pytest.mark.asyncio
async def test_tenant_isolation_on_calculator(client_with_auth_a, client_with_auth_b, test_db):
    """User B cannot export or view simulations created by Tenant A."""
    client_a, user_a, _, _ = client_with_auth_a
    client_b, user_b, _, _ = client_with_auth_b

    # Set both tenants to Premium to allow exports
    user_a.tenant.plan_slug = PLAN_PREMIUM
    user_b.tenant.plan_slug = PLAN_PREMIUM
    await test_db.commit()

    sim_a = CalculatorSimulation(
        tenant_id=user_a.tenant_id,
        simulation_type=SimulationType.REGIME,
        title="Simulation A Only",
        input_data={"revenue": 100000},
        result_data={"scenarios": []}
    )
    test_db.add(sim_a)
    await test_db.commit()
    await test_db.refresh(sim_a)

    payload = PdfExportRequest(simulation_id=sim_a.id)

    # User B tries to export User A's simulation -> should return 404
    response = client_b.post(
        "/api/v1/calculator/export-pdf",
        json=payload.model_dump(mode="json"),
    )
    assert response.status_code == 404
