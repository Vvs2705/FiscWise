"""NFS-e padrão nacional: DPS, assinatura, cliente mTLS e provider (sem rede)."""

import base64
import datetime as dt
import gzip
import json
import ssl
from dataclasses import dataclass

import httpx
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from lxml import etree

from app.domain.invoices.providers.base import TransientEmissionError
from app.domain.invoices.providers.mock import MockNfseProvider
from app.domain.invoices.providers.nfse_nacional import NfseNacionalProvider
from app.domain.nfse_nacional.assinatura import AssinaturaInvalida, assinar_xml, verificar_assinatura
from app.domain.nfse_nacional.cliente import contexto_tls, de_gzip_b64, gzip_b64
from app.domain.nfse_nacional.dps import (
    DpsInvalida,
    codigo_tributacao_nacional,
    montar_dps,
    montar_id_dps,
    validar_xml,
)
from app.domain.nfse_nacional.eventos import montar_cancelamento

NS = "{http://www.sped.fazenda.gov.br/nfse}"
CNPJ = "01761135000132"
# Chave de acesso (50): município (7) + ambiente gerador (1) + tipo de inscrição
# (1 = CPF, 2 = CNPJ) + inscrição (14) + demais campos numéricos (27).
CHAVE = "1400159" + "1" + "2" + "01761135000132" + "0" * 27

try:  # contrato com a frente do cofre (C1)
    from app.domain.certificados.cofre import MaterialCertificado  # type: ignore
except Exception:  # pragma: no cover - cofre ainda não existe nesta árvore
    @dataclass
    class MaterialCertificado:  # type: ignore[no-redef]
        certificado_id: str
        documento: str
        cert_pem: bytes
        chave_pem: bytes
        cadeia_pem: bytes = b""


def _material(documento: str = CNPJ) -> MaterialCertificado:
    chave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nome = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, f"EMPRESA TESTE:{documento}")])
    agora = dt.datetime.now(dt.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(nome).issuer_name(nome).public_key(chave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(agora - dt.timedelta(days=1)).not_valid_after(agora + dt.timedelta(days=365))
        .sign(chave, hashes.SHA256())
    )
    kwargs = dict(
        certificado_id="teste",
        documento=documento,
        cert_pem=cert.public_bytes(serialization.Encoding.PEM),
        chave_pem=chave.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()
        ),
        cadeia_pem=b"",
    )
    try:
        return MaterialCertificado(**kwargs)
    except TypeError:  # cofre real com campos a mais/menos
        obj = MaterialCertificado.__new__(MaterialCertificado)
        for k, v in kwargs.items():
            setattr(obj, k, v)
        return obj


MATERIAL = _material()


def _dados(**extra):
    base = {
        "cnpj_emissor": CNPJ,
        "inscricao_municipal": "12345",
        "municipio_ibge": "1400159",
        "regime_tributario": "simples",
        "cod_servico_lc116": "01.07",
        "aliquota_iss": "0.02",
        "retencao_iss": False,
        "competencia": dt.date(2026, 11, 10),
        "valor_servico": 1500,
        "descricao_servico": "Consultoria em sistemas de informação",
        "tomador_cpf_cnpj": "11.222.333/0001-81",
        "tomador_nome": "Cliente Tomador LTDA",
        "tomador_email": "financeiro@tomador.com.br",
        "serie_dps": "900",
        "numero_dps": "6",
    }
    base.update(extra)
    return base


def _nfse_xml(numero: str = "123") -> bytes:
    return (
        f'<NFSe xmlns="http://www.sped.fazenda.gov.br/nfse" versao="1.01"><infNFSe Id="NFS{CHAVE}">'
        f"<nNFSe>{numero}</nNFSe></infNFSe></NFSe>"
    ).encode()


# ---------------------------------------------------------------------------
# DPS
# ---------------------------------------------------------------------------

def test_id_dps_igual_ao_exemplo_oficial():
    assert montar_id_dps("1400159", CNPJ, "900", "6") == "DPS140015920176113500013200900000000000000006"
    # CPF: tipo 1 e inscrição com zeros à esquerda
    assert montar_id_dps("3550308", "12345678909", "1", "1").startswith("DPS35503081000" + "12345678909")


def test_codigo_tributacao_nacional():
    assert codigo_tributacao_nacional("010701") == ("010701", None)
    cod, aviso = codigo_tributacao_nacional("1.07")
    assert cod == "010701" and "desdobro" in aviso
    assert codigo_tributacao_nacional("17.01.02")[0] == "170102"
    with pytest.raises(DpsInvalida):
        codigo_tributacao_nacional("abc")


def test_dps_simples_valida_no_xsd_oficial():
    dps = montar_dps(_dados())
    validar_xml(dps.xml)  # XSD DPS_v1.01 do nfelib
    raiz = etree.fromstring(dps.xml)
    inf = raiz.find(f"{NS}infDPS")
    assert raiz.get("versao") == "1.01"
    assert inf.get("Id") == dps.id_dps
    assert inf.findtext(f"{NS}finNFSe") == "0"
    assert inf.findtext(f"{NS}tpAmb") == "2"
    assert inf.findtext(f"{NS}prest/{NS}regTrib/{NS}opSimpNac") == "3"
    assert inf.findtext(f"{NS}prest/{NS}regTrib/{NS}regApTribSN") == "1"
    assert inf.findtext(f"{NS}serv/{NS}cServ/{NS}cTribNac") == "010701"
    assert inf.findtext(f"{NS}valores/{NS}vServPrest/{NS}vServ") == "1500.00"
    assert inf.findtext(f"{NS}valores/{NS}trib/{NS}tribMun/{NS}pAliq") == "2.00"
    assert inf.findtext(f"{NS}toma/{NS}CNPJ") == "11222333000181"
    assert any("desdobro" in a for a in dps.avisos)


def test_dps_mei_sem_aliquota_e_com_retencao():
    dps = montar_dps(_dados(regime_tributario="mei", retencao_iss=True, cod_servico_lc116="010701"))
    validar_xml(dps.xml)
    inf = etree.fromstring(dps.xml).find(f"{NS}infDPS")
    assert inf.findtext(f"{NS}prest/{NS}regTrib/{NS}opSimpNac") == "2"
    assert inf.find(f"{NS}valores/{NS}trib/{NS}tribMun/{NS}pAliq") is None
    assert inf.findtext(f"{NS}valores/{NS}trib/{NS}tribMun/{NS}tpRetISSQN") == "2"


@pytest.mark.parametrize("campo,valor", [
    ("numero_dps", None), ("valor_servico", 0), ("descricao_servico", ""),
    ("municipio_ibge", "123"), ("cnpj_emissor", "1234"),
])
def test_dps_invalida(campo, valor):
    with pytest.raises(DpsInvalida):
        montar_dps(_dados(**{campo: valor}))


# ---------------------------------------------------------------------------
# Assinatura e compactação
# ---------------------------------------------------------------------------

def test_assinatura_rsa_sha256_verifica_e_continua_no_xsd():
    dps = montar_dps(_dados())
    assinado = assinar_xml(dps.xml, referencia_id=dps.id_dps, chave_pem=MATERIAL.chave_pem, cert_pem=MATERIAL.cert_pem)
    verificar_assinatura(assinado, MATERIAL.cert_pem)
    validar_xml(assinado)
    texto = assinado.decode()
    assert 'xmlns="http://www.w3.org/2000/09/xmldsig#"' in texto
    assert "rsa-sha256" in texto and "REC-xml-c14n-20010315" in texto
    assert f'URI="#{dps.id_dps}"' in texto
    # Adulterar o XML quebra a assinatura
    with pytest.raises(AssinaturaInvalida):
        verificar_assinatura(assinado.replace(b"1500.00", b"9500.00"), MATERIAL.cert_pem)


def test_gzip_b64_ida_e_volta():
    assert de_gzip_b64(gzip_b64(b"<a>teste</a>")) == b"<a>teste</a>"


def test_contexto_tls_carrega_certificado():
    ctx = contexto_tls(MATERIAL.cert_pem, MATERIAL.chave_pem)
    assert isinstance(ctx, ssl.SSLContext)


# ---------------------------------------------------------------------------
# Provider com a Sefin simulada
# ---------------------------------------------------------------------------

def _provider(handler):
    return NfseNacionalProvider(transport=httpx.MockTransport(handler))


async def test_emit_sucesso_envia_dps_assinada_e_le_numero():
    vistos = {}

    def handler(request: httpx.Request):
        vistos["url"] = str(request.url)
        corpo = json.loads(request.content)
        vistos["dps"] = de_gzip_b64(corpo["dpsXmlGZipB64"])
        return httpx.Response(201, json={
            "tipoAmbiente": 2, "idDps": "x", "chaveAcesso": CHAVE,
            "nfseXmlGZipB64": base64.b64encode(gzip.compress(_nfse_xml("987"))).decode(),
            "alertas": [{"Codigo": "A1", "Descricao": "Alerta de teste"}],
        })

    res = await _provider(handler).emit(_dados(), MATERIAL)
    assert res["status"] == "issued"
    assert res["protocol"] == CHAVE and res["numero"] == "987"
    assert vistos["url"].endswith("/API/SefinNacional/nfse")
    assert b"<Signature" in vistos["dps"]
    verificar_assinatura(vistos["dps"], MATERIAL.cert_pem)
    assert "Alerta de teste" in res["avisos"]


async def test_emit_rejeitada_traz_codigo_e_descricao():
    def handler(request):
        return httpx.Response(400, json={"erros": [{"Codigo": "E0014", "Descricao": "DPS já processada", "Complemento": "x"}]})

    res = await _provider(handler).emit(_dados(), MATERIAL)
    assert res["status"] == "rejected"
    assert res["codigo_rejeicao"] == "E0014"
    assert "DPS já processada" in res["descricao"]


async def test_emit_timeout_recupera_pela_dps():
    def handler(request):
        if request.method == "POST":
            raise httpx.ReadTimeout("demorou", request=request)
        assert "/dps/DPS" in str(request.url)
        return httpx.Response(200, json={"chaveAcesso": CHAVE,
                                         "nfseXmlGZipB64": gzip_b64(_nfse_xml("55"))})

    res = await _provider(handler).emit(_dados(), MATERIAL)
    assert res["status"] == "issued" and res["numero"] == "55"


async def test_emit_indisponivel_vira_transitorio():
    def handler(request):
        return httpx.Response(503, json={})

    with pytest.raises(TransientEmissionError):
        await _provider(handler).emit(_dados(), MATERIAL)


async def test_emit_erro_tls_vira_certificado_recusado():
    def handler(request):
        raise httpx.ConnectError("handshake", request=request) from ssl.SSLError("tlsv1 alert bad certificate")

    res = await _provider(handler).emit(_dados(), MATERIAL)
    assert res["status"] == "failed"
    assert "certificado" in res["descricao"].lower()


async def test_emit_sem_certificado_e_dps_invalida():
    p = _provider(lambda r: httpx.Response(500))
    assert (await p.emit(_dados(), None))["status"] == "failed"
    res = await p.emit(_dados(numero_dps=None), MATERIAL)
    assert res["status"] == "rejected" and res["codigo_rejeicao"] == "FISCWISE"


async def test_testar_conexao():
    p404 = _provider(lambda r: httpx.Response(404, json={}))
    ok = await p404.testar_conexao(MATERIAL, {"cnpj": CNPJ, "municipio_ibge": "1400159"})
    assert ok["ok"] is True
    p403 = _provider(lambda r: httpx.Response(403, json={"erros": [{"Codigo": "X", "Descricao": "negado"}]}))
    nao = await p403.testar_conexao(MATERIAL, {"cnpj": CNPJ, "municipio_ibge": "1400159"})
    assert nao["ok"] is False and "procuração" in nao["mensagem"]
    # Certificado de outro documento = modo procurador
    proc = await p404.testar_conexao(_material("12345678000195"), {"cnpj": CNPJ, "municipio_ibge": "1400159"})
    assert proc["ok"] is True and proc["detalhes"]["modo"] == "procurador"


def test_evento_cancelamento_valida_no_xsd():
    ev = montar_cancelamento(chave_acesso=CHAVE, documento_autor=CNPJ, motivo="Erro no valor do serviço informado")
    validar_xml(ev.xml, "pedRegEvento_v1.01.xsd")
    assert ev.id_evento == f"PRE{CHAVE}101101" and len(ev.id_evento) == 59
    with pytest.raises(DpsInvalida):
        montar_cancelamento(chave_acesso=CHAVE, documento_autor=CNPJ, motivo="curto")


async def test_cancelamento():
    vistos = {}

    def handler(request):
        vistos["url"] = str(request.url)
        vistos["evento"] = de_gzip_b64(json.loads(request.content)["pedidoRegistroEventoXmlGZipB64"])
        return httpx.Response(201, json={"eventoXmlGZipB64": ""})

    res = await _provider(handler).cancel(CHAVE, "Erro no valor do serviço informado", MATERIAL)
    assert res["status"] == "cancelled"
    assert vistos["url"].endswith(f"/nfse/{CHAVE}/eventos")
    assert b"e101101" in vistos["evento"]
    verificar_assinatura(vistos["evento"], MATERIAL.cert_pem)


async def test_consulta():
    p = _provider(lambda r: httpx.Response(200, json={"nfseXmlGZipB64": gzip_b64(_nfse_xml("7"))}))
    res = await p.query_status(CHAVE, MATERIAL)
    assert res["status"] == "issued" and res["numero"] == "7"
    p404 = _provider(lambda r: httpx.Response(404))
    assert (await p404.query_status(CHAVE, MATERIAL))["status"] == "not_found"


async def test_mock_compativel_com_o_contrato_novo():
    mock = MockNfseProvider()
    assert (await mock.emit({"descricao_servico": "ok", "valor_servico": 1}))["status"] == "issued"
    assert (await mock.testar_conexao(None, {}))["ok"] is True
