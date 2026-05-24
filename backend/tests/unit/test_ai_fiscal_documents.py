import pytest

from app.services.ai_fiscal import (
    extract_document_text,
    generate_client_operational_summary,
    mask_brazilian_tax_ids,
)


def test_mask_brazilian_tax_ids_masks_cpf_and_cnpj() -> None:
    text = "CPF 123.456.789-09 e CNPJ 12.345.678/0001-90 devem ser mascarados"

    masked = mask_brazilian_tax_ids(text)

    assert "123.456.789-09" not in masked
    assert "12.345.678/0001-90" not in masked
    assert "[CPF_MASCARADO]" in masked
    assert "[CNPJ_MASCARADO]" in masked


def test_extract_document_text_from_excel_parser_output() -> None:
    parsed = {
        "type": "excel",
        "sheets": [
            {
                "name": "DAS",
                "rows": [
                    {"row": 1, "values": ["Competencia", "Valor"]},
                    {"row": 2, "values": ["2026-05", "1500.00"]},
                ],
            }
        ],
    }

    text = extract_document_text(parsed)

    assert "DAS" in text
    assert "Competencia | Valor" in text
    assert "2026-05 | 1500.00" in text


@pytest.mark.asyncio
async def test_generate_client_operational_summary_masks_tax_ids(monkeypatch) -> None:
    calls: dict[str, object] = {}

    async def fake_call_openai(messages, max_tokens):
        calls["messages"] = messages
        calls["max_tokens"] = max_tokens
        return "Resumo seguro do cliente.", 42

    monkeypatch.setattr("app.services.ai_fiscal._call_openai", fake_call_openai)

    summary, tokens = await generate_client_operational_summary(
        {
            "name": "Clinica Exemplo",
            "document": "12.345.678/0001-90",
            "responsible_cpf": "123.456.789-09",
            "tax_regime": "simples_nacional",
            "documents": [
                {
                    "name": "DAS Maio",
                    "parsed_data": {
                        "ai_classification": {
                            "summary": "DAS com CNPJ 12.345.678/0001-90",
                        }
                    },
                }
            ],
        }
    )

    assert summary == "Resumo seguro do cliente."
    assert tokens == 42
    prompt = calls["messages"][1]["content"]
    assert "12.345.678/0001-90" not in prompt
    assert "123.456.789-09" not in prompt
    assert "[CNPJ_MASCARADO]" in prompt
    assert "[CPF_MASCARADO]" in prompt
