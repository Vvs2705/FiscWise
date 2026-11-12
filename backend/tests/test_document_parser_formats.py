"""Parser: XML de NF-e/NFS-e, CSV, OFX e formatos pulados (imagem, .doc)."""


import pytest

from app.api.v1.endpoints import operations
from app.models.operations import ClientDocument
from app.services.document_parser import is_skipped, parse_document

CHAVE = "35261012345678000195550010000012341000012345"

NFE_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
  <NFe><infNFe Id="NFe{CHAVE}" versao="4.00">
    <ide><mod>55</mod><serie>1</serie><nNF>1234</nNF><natOp>Venda</natOp>
      <dhEmi>2026-10-05T10:30:00-03:00</dhEmi></ide>
    <emit><CNPJ>12345678000195</CNPJ><xNome>Loja Teste LTDA</xNome></emit>
    <dest><CPF>12345678909</CPF><xNome>Cliente Final</xNome></dest>
    <det nItem="1"><prod><xProd>Caneta azul</xProd><NCM>96081000</NCM>
      <CFOP>5102</CFOP><vProd>10.00</vProd></prod></det>
    <det nItem="2"><prod><xProd>Caderno</xProd><NCM>48202000</NCM>
      <CFOP>5102</CFOP><vProd>25.50</vProd></prod></det>
    <total><ICMSTot><vNF>35.50</vNF></ICMSTot></total>
  </infNFe></NFe>
  <protNFe><infProt><chNFe>{CHAVE}</chNFe></infProt></protNFe>
</nfeProc>"""

OFX = """OFXHEADER:100
DATA:OFXSGML
<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS><CURDEF>BRL
<BANKACCTFROM><BANKID>341<BRANCHID>0001<ACCTID>12345-6</BANKACCTFROM>
<BANKTRANLIST><DTSTART>20261001000000[-3:BRT]<DTEND>20261031235959[-3:BRT]
<STMTTRN><TRNTYPE>DEBIT<DTPOSTED>20261002<TRNAMT>-50.00</STMTTRN>
<STMTTRN><TRNTYPE>CREDIT<DTPOSTED>20261003<TRNAMT>200.00</STMTTRN>
</BANKTRANLIST><LEDGERBAL><BALAMT>1234.56<DTASOF>20261031</LEDGERBAL>
</STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>"""


def _write(tmp_path, name, data):
    p = tmp_path / name
    p.write_bytes(data.encode("utf-8") if isinstance(data, str) else data)
    return str(p)


async def test_nfe_xml(tmp_path):
    data, err = await parse_document(_write(tmp_path, "nota.xml", NFE_XML), "nota.xml")
    assert err is None
    assert data["type"] == "nfe"
    assert data["chave_acesso"] == CHAVE
    assert (data["numero"], data["serie"], data["modelo"]) == ("1234", "1", "55")
    assert data["data_emissao"] == "2026-10-05"
    assert data["emitente"] == {"cnpj": "12345678000195", "cpf": None, "razao_social": "Loja Teste LTDA"}
    assert data["destinatario"]["cpf"] == "12345678909"
    assert data["valor_total"] == "35.50"
    assert data["itens"][1] == {"descricao": "Caderno", "ncm": "48202000", "cfop": "5102", "valor": "25.50"}
    assert data["total_itens"] == 2


async def test_nfe_sem_campos_fica_none(tmp_path):
    xml = '<NFe xmlns="http://www.portalfiscal.inf.br/nfe"><infNFe Id="x"><ide/></infNFe></NFe>'
    data, err = await parse_document(_write(tmp_path, "n.xml", xml), "n.xml")
    assert err is None and data["type"] == "nfe"
    assert data["chave_acesso"] is None and data["valor_total"] is None and data["emitente"] is None
    assert data["itens"] == []


async def test_nfe_limita_itens(tmp_path):
    dets = "".join(f"<det><prod><xProd>i{i}</xProd></prod></det>" for i in range(30))
    xml = f'<NFe xmlns="http://www.portalfiscal.inf.br/nfe"><infNFe>{dets}</infNFe></NFe>'
    data, _ = await parse_document(_write(tmp_path, "n.xml", xml), "n.xml")
    assert len(data["itens"]) == 20 and data["total_itens"] == 30


async def test_nfse_abrasf(tmp_path):
    xml = """<CompNfse xmlns="http://www.abrasf.org.br/nfse.xsd"><Nfse><InfNfse>
      <Numero>77</Numero><DataEmissao>2026-09-01T08:00:00</DataEmissao>
      <ValoresNfse><ValorLiquidoNfse>900.00</ValorLiquidoNfse></ValoresNfse>
      <PrestadorServico><IdentificacaoPrestador><Cnpj>11222333000181</Cnpj></IdentificacaoPrestador>
        <RazaoSocial>Servicos SA</RazaoSocial></PrestadorServico>
    </InfNfse></Nfse></CompNfse>"""
    data, err = await parse_document(_write(tmp_path, "s.xml", xml), "s.xml")
    assert err is None and data["type"] == "nfse"
    assert data["numero"] == "77" and data["valor_total"] == "900.00"
    assert data["data_emissao"] == "2026-09-01"
    assert data["emitente"]["cnpj"] == "11222333000181"
    assert data["destinatario"] is None


async def test_xml_com_entidade_recusado(tmp_path):
    xml = '<?xml version="1.0"?><!DOCTYPE a [<!ENTITY x "y">]><a>&x;</a>'
    data, err = await parse_document(_write(tmp_path, "a.xml", xml), "a.xml")
    assert data is None and "DOCTYPE" in err


async def test_csv_metadados(tmp_path):
    content = "data;descricao;valor\n01/10/2026;Aluguel;1500,00\n02/10/2026;Luz;200,00\n\n"
    data, err = await parse_document(_write(tmp_path, "e.csv", content), "e.csv")
    assert err is None
    assert data == {"type": "csv", "delimiter": ";", "columns": ["data", "descricao", "valor"],
                    "total_columns": 3, "total_rows": 2}


async def test_ofx(tmp_path):
    data, err = await parse_document(_write(tmp_path, "x.ofx", OFX), "x.ofx")
    assert err is None
    assert data["banco"] == "341" and data["conta"] == "12345-6" and data["agencia"] == "0001"
    assert (data["periodo_inicio"], data["periodo_fim"]) == ("2026-10-01", "2026-10-31")
    assert data["saldo"] == "1234.56" and data["data_saldo"] == "2026-10-31"
    assert data["total_lancamentos"] == 2


@pytest.mark.parametrize("name,motivo", [("foto.jpg", "imagem sem OCR"), ("velho.doc", ".doc")])
async def test_formatos_pulados(tmp_path, name, motivo):
    data, err = await parse_document(_write(tmp_path, name, b"\xff\xd8\xff"), name)
    assert err is None
    assert motivo in is_skipped(data)


async def test_background_marca_skipped(tmp_path, test_db, client_a, monkeypatch):
    doc = ClientDocument(tenant_id=client_a.tenant_id, client_id=client_a.id, name="foto.png",
                         file_url=None, parse_status="processing")
    test_db.add(doc)
    await test_db.commit()

    class _Ctx:
        async def __aenter__(self):
            return test_db

        async def __aexit__(self, *a):
            return False

    async def _noop(*a, **k):
        return None

    async def _no_ai(*a, **k):
        raise AssertionError("IA não deve ser chamada para arquivo pulado")

    monkeypatch.setattr("app.core.deps.get_sessionmaker", lambda: _Ctx)
    monkeypatch.setattr("app.core.deps._set_current_tenant_context", _noop)
    monkeypatch.setattr(operations, "classify_fiscal_document", _no_ai)
    path = _write(tmp_path, "foto.png", b"\x89PNG\r\n\x1a\n")
    await operations._parse_document_background(doc.id, path, "foto.png", client_a.tenant_id)
    await test_db.refresh(doc)
    assert doc.parse_status == "skipped"
    assert doc.parse_error == "imagem sem OCR"
    assert not (tmp_path / "foto.png").exists()
