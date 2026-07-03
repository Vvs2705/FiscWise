"""Roundtrip da camada fiscal: montar NF-e -> XML -> objeto."""

from app.fiscal.nfe import build_nfe_exemplo, parse_nfe, serialize_nfe


def test_nfe_roundtrip():
    nfe = build_nfe_exemplo(
        cnpj_emitente="12345678000195",
        razao_social="Empresa Exemplo LTDA",
        numero_nota="123",
    )
    xml = serialize_nfe(nfe)
    assert xml.startswith("<?xml")
    assert "portalfiscal.inf.br/nfe" in xml

    back = parse_nfe(xml)
    assert back.infNFe.emit.CNPJ == "12345678000195"
    assert back.infNFe.emit.xNome == "Empresa Exemplo LTDA"
    assert back.infNFe.ide.nNF == "123"
    assert back.infNFe.versao == "4.00"
