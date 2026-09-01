"""AI Fiscal Assistant — OpenAI GPT-4o Mini integration.

Provides regime recommendations and a conversational fiscal assistant.
All external calls are isolated here so the rest of the codebase does
not depend directly on the openai SDK.
"""

import logging
from decimal import Decimal
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """Você é um assistente fiscal especializado no sistema tributário brasileiro.
Seu papel é ajudar contadores e empresários a entenderem as implicações dos diferentes regimes
tributários (MEI, Simples Nacional, Lucro Presumido, Lucro Real) e tomar decisões informadas.

Diretrizes:
- Seja objetivo e preciso com os números.
- Sempre esclareça que suas respostas são orientativas e não substituem assessoria contábil profissional.
- Use linguagem acessível, evitando jargão excessivo.
- Quando mencionar valores, use o formato R$ X.XXX,XX.
- Responda sempre em português do Brasil.
"""

_RECOMMENDATION_PROMPT = """Com base nos seguintes dados de simulação fiscal, forneça uma recomendação
objetiva do melhor regime tributário para esta empresa:

Faturamento anual: R$ {revenue}
Atividade: {activity}
Regime recomendado pela análise numérica: {recommended_regime}

Resultados por regime:
{results_summary}

Forneça em 3-4 parágrafos:
1. Por que o regime recomendado é vantajoso neste caso.
2. Pontos de atenção ou condições que poderiam mudar a recomendação.
3. Próximos passos sugeridos.

Seja conciso e prático.
"""


def _build_client():
    """Return an OpenAI client. Raises RuntimeError if key is not configured."""
    try:
        from openai import AsyncOpenAI
    except ImportError as exc:
        raise RuntimeError(
            "Pacote 'openai' não instalado. Adicione 'openai>=1.0.0' ao requirements.txt."
        ) from exc

    api_key = settings.OPENAI_API_KEY
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY não configurada. "
            "Adicione o secret via: flyctl secrets set OPENAI_API_KEY=<sua-chave>"
        )
    return AsyncOpenAI(api_key=api_key)


async def generate_regime_recommendation(
    annual_revenue: Decimal,
    activity_type: str,
    recommended_regime: str,
    results: list[dict],
) -> str:
    """Generate an AI recommendation for the best fiscal regime.

    Returns a plain-text recommendation. Returns an empty string if
    OPENAI_API_KEY is not configured (plan gating should prevent this).
    """
    results_summary = "\n".join(
        f"- {r['regime_label']}: Carga anual R$ {r['annual_tax_burden']}, "
        f"Alíquota efetiva {float(r['effective_rate']) * 100:.2f}%"
        for r in results
        if r.get("eligible")
    )

    prompt = _RECOMMENDATION_PROMPT.format(
        revenue=f"{annual_revenue:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        activity=activity_type,
        recommended_regime=recommended_regime,
        results_summary=results_summary,
    )

    try:
        client = _build_client()
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=600,
            temperature=0.3,
        )
        return response.choices[0].message.content or ""
    except RuntimeError as exc:
        logger.warning("AI recommendation skipped: %s", exc)
        return ""
    except Exception as exc:
        logger.error("OpenAI API error generating recommendation: %s", exc, exc_info=True)
        return ""


async def chat_with_fiscal_assistant(
    user_message: str,
    history: list[dict],
    simulation_context: Optional[dict] = None,
) -> tuple[str, int]:
    """Send a message to the AI fiscal assistant.

    Returns (reply_text, tokens_used).
    Raises RuntimeError if OPENAI_API_KEY is not configured.
    """
    client = _build_client()

    messages: list[dict] = [{"role": "system", "content": _SYSTEM_PROMPT}]

    if simulation_context:
        context_text = (
            f"Contexto da simulação: Faturamento anual de R$ {simulation_context.get('annual_revenue')}, "
            f"atividade '{simulation_context.get('activity_type')}', "
            f"regime recomendado: {simulation_context.get('recommended_regime')}."
        )
        messages.append({"role": "system", "content": context_text})

    # Add conversation history (cap at last 10 turns to control cost)
    for msg in history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": user_message})

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=800,
            temperature=0.4,
        )
        reply = response.choices[0].message.content or ""
        tokens = response.usage.total_tokens if response.usage else 0
        return reply, tokens
    except Exception as exc:
        logger.error("OpenAI API error in chat: %s", exc, exc_info=True)
        raise RuntimeError(f"Erro ao comunicar com o assistente IA: {exc}") from exc
