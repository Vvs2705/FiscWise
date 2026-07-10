"""Ciclos de cobrança e matriz de preços do FiscWise (fonte única de verdade).

Regras de negócio (definidas pelo dono em 09/07/2026, com base em análise de mercado):
- Mensal: assinatura recorrente no cartão (preapproval Mercado Pago), sem desconto.
- Trimestral / Semestral / Anual: pré-pagos via checkout único.
  - Pix: 15% de desconto. O desconto se MANTÉM na renovação se a fatura for paga
    até a data-limite (fim do período vigente); depois disso, preço cheio.
  - Cartão: até 6x SEM JUROS para o cliente (nós absorvemos a taxa do gateway;
    acima de 6x entrariam acréscimos — hoje não oferecido).
  - Anual no cartão: 15% de desconto, parcelável em até 6x sem juros.
- Operacional: NÃO antecipar recebíveis de cartão no Mercado Pago (receber
  parcelado D+30 mantém a taxa ~5%; antecipando sobe p/ ~10-13% e come a margem).

Preços-base (mensal) vivem na tabela `plans` (price_monthly); este módulo só
aplica os ciclos/descontos sobre eles — nunca confiar em valor vindo do cliente.
"""

from decimal import Decimal
from typing import Any

DESCONTO_PIX = 0.15
DESCONTO_ANUAL_CARTAO = 0.15

CICLOS: list[dict[str, Any]] = [
    {"chave": "mensal", "meses": 1, "label": "Mensal",
     "desconto_pix": 0.0, "desconto_cartao": 0.0, "cartao_max_parcelas": 1,
     "obs": "Assinatura recorrente no cartão."},
    {"chave": "trimestral", "meses": 3, "label": "Trimestral",
     "desconto_pix": DESCONTO_PIX, "desconto_cartao": 0.0, "cartao_max_parcelas": 3,
     "obs": "Pix com 15% de desconto ou cartão em até 3x sem juros."},
    {"chave": "semestral", "meses": 6, "label": "Semestral",
     "desconto_pix": DESCONTO_PIX, "desconto_cartao": 0.0, "cartao_max_parcelas": 6,
     "obs": "Pix com 15% de desconto ou cartão em até 6x sem juros."},
    {"chave": "anual", "meses": 12, "label": "Anual",
     "desconto_pix": DESCONTO_PIX, "desconto_cartao": DESCONTO_ANUAL_CARTAO,
     "cartao_max_parcelas": 6,
     "obs": "15% de desconto no Pix OU no cartão em até 6x sem juros."},
]

CICLOS_VALIDOS = {c["chave"] for c in CICLOS}


def get_ciclo(chave: str) -> dict[str, Any] | None:
    return next((c for c in CICLOS if c["chave"] == chave), None)


def _round2(v: float) -> float:
    return round(v + 1e-9, 2)


def linha_preco(preco_mensal: Decimal | float, ciclo: str) -> dict[str, Any]:
    """Totais de um ciclo para um preço mensal. Levanta ValueError em ciclo inválido."""
    c = get_ciclo(ciclo)
    if not c:
        raise ValueError(f"Ciclo inválido: {ciclo}")
    base = float(preco_mensal) * c["meses"]
    pix_total = _round2(base * (1 - c["desconto_pix"]))
    cartao_total = _round2(base * (1 - c["desconto_cartao"]))
    max_parc = int(c["cartao_max_parcelas"])
    return {
        "ciclo": c["chave"],
        "label": c["label"],
        "meses": c["meses"],
        "preco_cheio": _round2(base),
        "pix_total": pix_total,
        "desconto_pix_pct": int(c["desconto_pix"] * 100),
        "cartao_total": cartao_total,
        "desconto_cartao_pct": int(c["desconto_cartao"] * 100),
        "cartao_max_parcelas": max_parc,
        "cartao_parcela": _round2(cartao_total / max_parc),
        "obs": c["obs"],
    }


def tabela_precos(preco_mensal: Decimal | float) -> list[dict[str, Any]]:
    """Tabela completa (todos os ciclos) para a página de preços."""
    return [linha_preco(preco_mensal, c["chave"]) for c in CICLOS]


def valores_aceitos(preco_mensal: Decimal | float, ciclo: str) -> set[float]:
    """Valores de pagamento válidos para (plano, ciclo) — usado pelo webhook
    para conferir o valor pago antes de ativar (anti-fraude)."""
    linha = linha_preco(preco_mensal, ciclo)
    return {linha["pix_total"], linha["cartao_total"]}


def _selfcheck() -> None:
    # Intermediário R$149 — anual: cheio 1788, Pix/cartão 1519.80, 6x de 253.30
    a = linha_preco(149, "anual")
    assert a["preco_cheio"] == 1788.0
    assert a["pix_total"] == 1519.8
    assert a["cartao_total"] == 1519.8
    assert a["cartao_max_parcelas"] == 6
    assert a["cartao_parcela"] == 253.3
    # Trimestral: Pix desconta, cartão NÃO
    t = linha_preco(149, "trimestral")
    assert t["pix_total"] == 379.95 and t["cartao_total"] == 447.0
    assert t["cartao_max_parcelas"] == 3
    # Premium R$349 — semestral Pix 1779.90
    s = linha_preco(349, "semestral")
    assert s["pix_total"] == 1779.9 and s["cartao_total"] == 2094.0
    # Mensal sem desconto
    m = linha_preco(349, "mensal")
    assert m["pix_total"] == 349.0 == m["cartao_total"]
    assert valores_aceitos(149, "anual") == {1519.8}
    assert valores_aceitos(149, "trimestral") == {379.95, 447.0}
    try:
        linha_preco(149, "bienal")
        raise AssertionError("ciclo inválido deveria levantar")
    except ValueError:
        pass
    print("pricing selfcheck OK")


if __name__ == "__main__":
    _selfcheck()
