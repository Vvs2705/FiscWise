"""
AI Fiscal Assistant Service for FiscWise - Feature #7

Wraps OpenAI GPT-4o Mini for:
1. Tax regime recommendation based on simulation data
2. Conversational fiscal assistant chat

Design decisions:
- Uses GPT-4o Mini for cost efficiency (much cheaper than GPT-4o/GPT-4)
- System prompt is Brazilian Portuguese, focused on fiscal/tax domain
- Graceful degradation: if OPENAI_API_KEY is not set, skips AI and returns None
- No streaming — simpler implementation for MVP
"""

import json
import logging
import re
from decimal import Decimal
import uuid
from typing import Any, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services import rag_service

logger = logging.getLogger(__name__)

_OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
_MODEL = "gpt-4o-mini"
_MAX_TOKENS_RECOMMENDATION = 600
_MAX_TOKENS_CHAT = 800
_MAX_TOKENS_DOCUMENT = 700

_SYSTEM_PROMPT = """Você é o FiscWise, um assistente fiscal especializado no sistema tributário brasileiro.
Você conhece profundamente:
- Simples Nacional (Anexos I a VI, limites, vedações)
- Lucro Presumido (presunção de lucro, alíquotas IRPJ/CSLL, PIS/COFINS cumulativo)
- Lucro Real (apuração real, PIS/COFINS não-cumulativo, créditos)
- ICMS (operações interestaduais, DIFAL, FECOEP, ST)
- PIS/COFINS (cumulativo vs não-cumulativo, créditos, regimes especiais)
- Benefícios fiscais federais e estaduais
- Planejamento tributário lícito

Responda sempre em português do Brasil. Seja objetivo, preciso e cite a legislação quando relevante.
Não faça suposições sem dados. Se faltarem informações para uma análise definitiva, peça os dados necessários.
Não forneça consultoria jurídica formal — indique que o usuário consulte um contador ou advogado tributarista para decisões definitivas."""


def mask_brazilian_tax_ids(text: str) -> str:
    """Mask CPF/CNPJ-like numbers before sending document content to external AI."""

    def mask_match(match: re.Match[str]) -> str:
        value = match.group(0)
        digits = re.sub(r"\D", "", value)
        if len(digits) == 11:
            return "[CPF_MASCARADO]"
        if len(digits) == 14:
            return "[CNPJ_MASCARADO]"
        return value

    masked = re.sub(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b", mask_match, text)
    return re.sub(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", mask_match, masked)


def extract_document_text(parsed_data: dict[str, Any] | None) -> str:
    """Convert parser output into a compact text body for AI classification."""
    if not parsed_data:
        return ""

    doc_type = parsed_data.get("type")
    if doc_type in {"pdf", "word"}:
        return str(parsed_data.get("full_text") or "")
    if doc_type == "text":
        return str(parsed_data.get("content") or "")
    if doc_type == "excel":
        chunks: list[str] = []
        for sheet in parsed_data.get("sheets", [])[:3]:
            chunks.append(str(sheet.get("name", "")))
            for row in sheet.get("rows", [])[:20]:
                chunks.append(" | ".join(str(value) for value in row.get("values", [])))
        return "\n".join(chunks)

    return json.dumps(parsed_data, ensure_ascii=False)[:5000]


async def classify_fiscal_document(
    parsed_data: dict[str, Any] | None,
    file_name: str,
    declared_document_type: str | None = None,
) -> Optional[dict[str, Any]]:
    """Classify a parsed document and extract operational hints for the office."""
    raw_text = extract_document_text(parsed_data)
    masked_text = mask_brazilian_tax_ids(raw_text)[:5000]
    if not masked_text.strip():
        return None

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Classifique o documento fiscal/contabil abaixo e responda exclusivamente em JSON valido, "
                "sem markdown, no formato: "
                '{"document_type":"das|nota_fiscal|contrato_social|certidao|extrato|guia|outro",'
                '"competence_month":"YYYY-MM ou null","amount":"numero ou null","due_date":"YYYY-MM-DD ou null",'
                '"summary":"resumo operacional em uma frase","confidence":0.0,'
                '"warning":"Resultado estimado. Valide com o responsavel tecnico."}\n\n'
                f"Nome do arquivo: {file_name}\n"
                f"Tipo informado pelo usuario: {declared_document_type or 'nao informado'}\n"
                f"Conteudo mascarado:\n{masked_text}"
            ),
        },
    ]

    content, tokens = await _call_openai(messages, _MAX_TOKENS_DOCUMENT)
    if not content:
        return None

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("Document AI classification returned invalid JSON")
        return None

    if not isinstance(parsed, dict):
        return None

    parsed["tokens_used"] = tokens
    parsed["pii_masked"] = raw_text != masked_text
    parsed.setdefault("warning", "Resultado estimado. Valide com o responsavel tecnico.")
    return parsed


async def generate_client_operational_summary(context: dict[str, Any]) -> tuple[Optional[str], Optional[int]]:
    """Generate a short operational summary for a client using masked context."""
    context_json = json.dumps(context, ensure_ascii=False, default=str)
    masked_context = mask_brazilian_tax_ids(context_json)[:6000]

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Gere um resumo operacional para o escritorio contabil sobre este cliente. "
                "Responda em ate 120 palavras, em portugues, priorizando riscos, pendencias e proximas acoes. "
                "Nao invente dados ausentes. Finalize com: Resultado estimado. Valide com o responsavel tecnico.\n\n"
                f"Contexto mascarado:\n{masked_context}"
            ),
        },
    ]

    return await _call_openai(messages, _MAX_TOKENS_DOCUMENT)


async def _call_openai(
    messages: list[dict[str, str]],
    max_tokens: int,
) -> tuple[Optional[str], Optional[int]]:
    """
    Call OpenAI Chat Completions API.

    Returns (content, tokens_used) or (None, None) on failure.
    Failures are logged as warnings, never raised — callers handle gracefully.
    """
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        logger.warning("OPENAI_API_KEY not configured — skipping AI call")
        return None, None

    payload = {
        "model": _MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.3,  # low temp for factual fiscal content
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                _OPENAI_API_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )

        if response.status_code != 200:
            logger.warning(
                "OpenAI API returned %d: %s",
                response.status_code,
                response.text[:200],
            )
            return None, None

        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
        tokens_used = data.get("usage", {}).get("total_tokens")
        return content, tokens_used

    except Exception as exc:
        logger.warning("OpenAI API call failed: %s", exc)
        return None, None


async def generate_regime_recommendation(
    annual_revenue: Decimal,
    annual_costs: Decimal,
    annual_payroll: Decimal,
    scenarios: list[dict[str, Any]],
    activity_code: Optional[str] = None,
) -> Optional[str]:
    """
    Generate an AI recommendation for the best tax regime.

    This runs after the deterministic calculation so the AI has the numbers.
    Returns a Portuguese text recommendation or None if AI is unavailable.
    """
    # Build a concise summary of each scenario for the prompt
    scenario_summaries = []
    for s in scenarios:
        ineligible = s.get("ineligible", False)
        if ineligible:
            scenario_summaries.append(
                f"- {s['regime'].upper()}: INELEGÍVEL (receita acima do limite)"
            )
        else:
            rate_pct = Decimal(str(s['effective_rate'])) * 100
            total = Decimal(str(s['total_tax']))
            recommended = " ★ RECOMENDADO" if s.get("is_recommended") else ""
            scenario_summaries.append(
                f"- {s['regime'].upper()}: alíquota efetiva {rate_pct:.2f}%, "
                f"imposto anual R$ {total:,.2f}{recommended}"
            )

    scenarios_text = "\n".join(scenario_summaries)

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Analise os seguintes dados de uma empresa e os resultados da simulação tributária:\n\n"
                f"**Dados financeiros:**\n"
                f"- Receita bruta anual: R$ {annual_revenue:,.2f}\n"
                f"- Custos anuais: R$ {annual_costs:,.2f}\n"
                f"- Folha de salários: R$ {annual_payroll:,.2f}\n"
                f"- CNAE: {activity_code or 'não informado'}\n\n"
                f"**Resultado da comparação de regimes:**\n{scenarios_text}\n\n"
                f"Forneça uma recomendação objetiva (máximo 300 palavras) explicando:\n"
                f"1. Qual regime é mais vantajoso e por quê\n"
                f"2. Pontos de atenção ou riscos do regime recomendado\n"
                f"3. Se há condições em que outro regime pode ser melhor\n"
                f"Seja direto e use valores concretos."
            ),
        },
    ]

    content, _ = await _call_openai(messages, _MAX_TOKENS_RECOMMENDATION)
    return content


async def generate_icms_analysis(
    result: dict[str, Any],
) -> Optional[str]:
    """Generate a brief AI analysis of an ICMS calculation result."""

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Analise a operação de ICMS abaixo e forneça orientações práticas (máximo 200 palavras):\n\n"
                f"- NCM: {result['ncm_code']}\n"
                f"- Origem: {result['origin_state']} → Destino: {result['destination_state']}\n"
                f"- Valor da operação: R$ {result['operation_value']:,.2f}\n"
                f"- Alíquota interestadual: {result['interstate_rate']*100:.1f}%\n"
                f"- ICMS interestadual: R$ {result['icms_interstate']:,.2f}\n"
                f"- DIFAL: R$ {result['difal_total']:,.2f}\n"
                f"- Alíquota efetiva total: {result['effective_rate']*100:.2f}%\n\n"
                f"Explique o resultado, possíveis obrigações acessórias e dicas de planejamento."
            ),
        },
    ]

    content, _ = await _call_openai(messages, _MAX_TOKENS_RECOMMENDATION)
    return content


async def generate_pis_cofins_analysis(
    result: dict[str, Any],
    activity_description: Optional[str] = None,
) -> Optional[str]:
    """Generate AI analysis for a PIS/COFINS simulation result."""

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Analise o cálculo de PIS/COFINS abaixo (máximo 200 palavras):\n\n"
                f"- Regime: {'Não-cumulativo (Lucro Real)' if result['regime_type'] == 'non_cumulative' else 'Cumulativo (Lucro Presumido)'}\n"
                f"- Receita mensal: R$ {result['monthly_revenue']:,.2f}\n"
                f"- PIS: {result['pis_rate']*100:.2f}% → R$ {result['pis_net']:,.2f}\n"
                f"- COFINS: {result['cofins_rate']*100:.2f}% → R$ {result['cofins_net']:,.2f}\n"
                f"- Total mensal: R$ {result['total_pis_cofins']:,.2f}\n"
                f"- Projeção anual: R$ {result['annual_projection']:,.2f}\n"
                f"- Atividade: {activity_description or 'não informada'}\n\n"
                f"Explique o resultado, diferenças entre regimes e possíveis créditos ou benefícios."
            ),
        },
    ]

    content, _ = await _call_openai(messages, _MAX_TOKENS_RECOMMENDATION)
    return content


async def generate_fator_r_recommendation(
    result: dict[str, Any],
) -> Optional[str]:
    """
    Generate AI recommendation for a Fator R / DAS simulation.

    Provides advice on payroll optimization to reach or maintain the 28%
    threshold, and compares the cost/benefit of switching annexes.
    """
    anexo = result.get("anexo", "?")
    fator_r_pct = result.get("fator_r_percent", "?")
    rbt12 = result.get("rbt12", 0)
    folha_12m = result.get("folha_12m", 0)
    total_das = result.get("total_das_anual", 0)
    comparison = result.get("comparison", {})
    alt_anexo = comparison.get("anexo", "?")
    alt_total = comparison.get("total_das_anual", 0)
    diff = comparison.get("diferenca_anual", 0)

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Analise a simulação de Fator R e DAS abaixo e forneça recomendações (máx 300 palavras):\n\n"
                f"**Dados:**\n"
                f"- RBT12 (receita bruta 12 meses): R$ {rbt12:,.2f}\n"
                f"- Folha de pagamento 12 meses: R$ {folha_12m:,.2f}\n"
                f"- Fator R: {fator_r_pct}\n"
                f"- Anexo enquadrado: {anexo}\n"
                f"- DAS anual no Anexo {anexo}: R$ {total_das:,.2f}\n"
                f"- Se fosse Anexo {alt_anexo}: R$ {alt_total:,.2f}\n"
                f"- Diferença anual: R$ {diff:,.2f}\n\n"
                f"Recomende:\n"
                f"1. Se o Fator R atual é favorável ou desfavorável\n"
                f"2. Se vale a pena aumentar a folha de pagamento para atingir 28% e migrar para o Anexo III\n"
                f"3. Qual o valor ideal de folha para otimizar a carga tributária\n"
                f"4. Cuidados com o pró-labore mínimo e limites legais\n"
                f"Use valores concretos e seja direto."
            ),
        },
    ]

    content, _ = await _call_openai(messages, _MAX_TOKENS_RECOMMENDATION)
    return content


async def chat_with_fiscal_assistant(
    user_message: str,
    conversation_history: list[dict[str, str]],
    db: AsyncSession,
    tenant_id: uuid.UUID,
    simulation_context: Optional[dict[str, Any]] = None,
) -> tuple[Optional[str], Optional[int]]:
    """
    Send a message to the fiscal assistant and return the response.

    conversation_history: list of {"role": "user"|"assistant", "content": "..."}
                          from previous messages in the session (most recent last).
    simulation_context: optional simulation data to prime the conversation.

    Returns (response_text, tokens_used) or (None, None) on failure.
    """
    messages: list[dict[str, str]] = [{"role": "system", "content": _SYSTEM_PROMPT}]

    # RAG: Search knowledge base for office-specific custom procedures
    try:
        rag_results = await rag_service.search_knowledge_base(
            db=db,
            query=user_message,
            tenant_id=tenant_id,
            limit=2
        )
        if rag_results:
            rag_lines = [
                "INFORMAÇÃO DA BASE DE CONHECIMENTO DO ESCRITÓRIO (FONTES CONFIÁVEIS):",
                "Você deve basear sua resposta prioritariamente nestas diretrizes e citar as fontes e o respectivo grau de confiança em sua resposta.",
            ]
            for doc, confidence in rag_results:
                rag_lines.append(
                    f"- Documento: {doc.title}\n"
                    f"  Fonte: {doc.source}\n"
                    f"  Grau de Confiança: {confidence:.0f}%\n"
                    f"  Procedimento:\n{doc.content}"
                )
            messages.append({"role": "system", "content": "\n\n".join(rag_lines)})
    except Exception as exc:
        logger.warning("RAG Fiscal search failed: %s", exc)

    # Inject simulation context if provided
    if simulation_context:
        sim_type = simulation_context.get("simulation_type", "")
        result = simulation_context.get("result_data", {})
        context_text = (
            f"O usuário está analisando uma simulação fiscal do tipo '{sim_type}'. "
            f"Dados principais: {str(result)[:500]}"
        )
        messages.append({"role": "system", "content": context_text})

    # Add conversation history (limit to last 10 to control context window)
    messages.extend(conversation_history[-10:])

    # Add current user message
    messages.append({"role": "user", "content": user_message})

    content, tokens = await _call_openai(messages, _MAX_TOKENS_CHAT)

    if content is None:
        content = (
            "Desculpe, o assistente fiscal está temporariamente indisponível. "
            "Tente novamente em alguns instantes."
        )

    return content, tokens
