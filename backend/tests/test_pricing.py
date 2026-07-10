"""Testes da matriz de preços/ciclos (caminho de dinheiro — regras do dono).

Regras: Pix -15% nos ciclos pré-pagos; cartão até 6x SEM JUROS ao cliente;
anual no cartão também -15%; mensal recorrente sem desconto.
"""
import pytest

from app.core.pricing import (
    CICLOS_VALIDOS,
    get_ciclo,
    linha_preco,
    tabela_precos,
    valores_aceitos,
)


def test_ciclos_validos():
    assert CICLOS_VALIDOS == {"mensal", "trimestral", "semestral", "anual"}
    assert get_ciclo("anual")["cartao_max_parcelas"] == 6


def test_intermediario_149_anual():
    a = linha_preco(149, "anual")
    assert a["preco_cheio"] == 1788.0
    assert a["pix_total"] == 1519.8          # -15%
    assert a["cartao_total"] == 1519.8       # anual no cartão também -15%
    assert a["cartao_max_parcelas"] == 6     # 6x sem juros ao cliente
    assert a["cartao_parcela"] == 253.3


def test_trimestral_semestral_cartao_sem_desconto():
    t = linha_preco(149, "trimestral")
    assert t["pix_total"] == 379.95 and t["cartao_total"] == 447.0
    assert t["cartao_max_parcelas"] == 3
    s = linha_preco(349, "semestral")
    assert s["pix_total"] == 1779.9 and s["cartao_total"] == 2094.0
    assert s["cartao_max_parcelas"] == 6


def test_mensal_sem_desconto():
    m = linha_preco(349, "mensal")
    assert m["pix_total"] == m["cartao_total"] == 349.0


def test_valores_aceitos_para_webhook():
    # Anual: Pix e cartão têm o MESMO valor (-15%) → um único valor aceito.
    assert valores_aceitos(149, "anual") == {1519.8}
    # Trimestral: Pix descontado OU cartão cheio.
    assert valores_aceitos(149, "trimestral") == {379.95, 447.0}


def test_tabela_completa_e_ciclo_invalido():
    tabela = tabela_precos(349)
    assert [l["ciclo"] for l in tabela] == ["mensal", "trimestral", "semestral", "anual"]
    with pytest.raises(ValueError):
        linha_preco(149, "bienal")
