"""Cofre de certificados A1 e liberação da emissão de NFS-e por emissor.

Os certificados são gerados aqui (AC de teste com O=ICP-Brasil e e-CNPJ com o
otherName 2.16.76.1.3.3), nunca há arquivo real no repositório.
"""

from __future__ import annotations

import base64
import os
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
from sqlalchemy import select

from app.core.config import settings
from app.domain.certificados import cofre
from app.domain.certificados.models import CertificadoA1
from app.domain.certificados.validacao import CertificadoInvalido, conferir

SENHA = "senha-teste-123"
CNPJ_A = "76069336914468"  # documento do client_a do conftest
CNPJ_ESCRITORIO = "11222333000181"


# ---------------------------------------------------------------------------
# Geração de certificados de teste
# ---------------------------------------------------------------------------

_CHAVES: dict[str, rsa.RSAPrivateKey] = {}


def _chave(nome: str) -> rsa.RSAPrivateKey:
    if nome not in _CHAVES:
        _CHAVES[nome] = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return _CHAVES[nome]


def _ac(org: str = "ICP-Brasil"):
    chave = _chave(f"ac-{org}")
    nome = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, org),
        x509.NameAttribute(NameOID.COMMON_NAME, f"AC Teste {org}"),
    ])
    agora = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(nome)
        .issuer_name(nome)
        .public_key(chave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(agora - timedelta(days=30))
        .not_valid_after(agora + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(chave, hashes.SHA256())
    )
    return chave, cert


def gerar_pfx(
    *,
    documento: str = CNPJ_A,
    nome: str = "EMPRESA TESTE LTDA",
    senha: str = SENHA,
    org_ac: str = "ICP-Brasil",
    validade_dias: int = 365,
    inicio_dias: int = -1,
    tipo: str = "cnpj",
) -> bytes:
    ac_chave, ac_cert = _ac(org_ac)
    chave = _chave(f"titular-{documento}-{validade_dias}-{inicio_dias}")
    agora = datetime.now(timezone.utc)
    if tipo == "cnpj":
        oid, valor = "2.16.76.1.3.3", documento.encode()
    else:  # e-CPF: data de nascimento (8) + CPF (11) + PIS etc.
        oid, valor = "2.16.76.1.3.1", ("01011980" + documento + "0" * 11).encode()
    der = b"\x04" + bytes([len(valor)]) + valor  # OCTET STRING
    cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ICP-Brasil"),
            x509.NameAttribute(NameOID.COMMON_NAME, f"{nome}:{documento}"),
        ]))
        .issuer_name(ac_cert.subject)
        .public_key(chave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(agora + timedelta(days=inicio_dias))
        .not_valid_after(agora + timedelta(days=validade_dias))
        .add_extension(
            x509.SubjectAlternativeName([x509.OtherName(x509.ObjectIdentifier(oid), der)]),
            critical=False,
        )
        .sign(ac_chave, hashes.SHA256())
    )
    return pkcs12.serialize_key_and_certificates(
        b"teste", chave, cert, [ac_cert], serialization.BestAvailableEncryption(senha.encode())
    )


@pytest.fixture
def chave_cofre(monkeypatch):
    monkeypatch.setattr(
        settings, "CERT_ENCRYPTION_KEY", base64.b64encode(os.urandom(32)).decode(), raising=False
    )


def _enviar(http, conteudo: bytes, *, escopo="cliente", client_id=None, senha=SENHA):
    data = {"senha": senha, "escopo": escopo}
    if client_id:
        data["client_id"] = str(client_id)
    return http.post(
        "/api/v1/certificados",
        data=data,
        files={"arquivo": ("cert.pfx", conteudo, "application/x-pkcs12")},
    )


def _criar_emissor(http, client_id, cnpj=CNPJ_A):
    r = http.post("/api/v1/invoices/issuers", json={
        "client_id": str(client_id), "cnpj": cnpj, "inscricao_municipal": "123456",
        "regime_tributario": "simples", "municipio_ibge": "3550308",
        "cod_servico_lc116": "17.01", "aliquota_iss": "0.02",
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ---------------------------------------------------------------------------
# Validação
# ---------------------------------------------------------------------------


def test_conferir_extrai_cnpj_validade_e_icp():
    dados = conferir(gerar_pfx(), SENHA)
    assert dados.documento == CNPJ_A and dados.tipo_documento == "cnpj"
    assert dados.titular_nome == "EMPRESA TESTE LTDA"
    assert dados.icp_brasil is True
    assert dados.valido_ate > datetime.now(timezone.utc)
    assert len(dados.thumbprint_sha256) == 64


def test_conferir_extrai_cpf_do_e_cpf():
    dados = conferir(gerar_pfx(documento="12345678909", tipo="cpf", nome="FULANO"), SENHA)
    assert dados.documento == "12345678909" and dados.tipo_documento == "cpf"


@pytest.mark.parametrize(
    "conteudo,senha,trecho",
    [
        (b"nao sou um pfx", SENHA, "A1"),
        (b"", SENHA, "vazio"),
    ],
)
def test_conferir_recusa_arquivo_invalido(conteudo, senha, trecho):
    with pytest.raises(CertificadoInvalido) as exc:
        conferir(conteudo, senha)
    assert trecho in str(exc.value)


def test_conferir_recusa_senha_errada_vencido_e_nao_icp():
    with pytest.raises(CertificadoInvalido, match="Senha"):
        conferir(gerar_pfx(), "errada")
    with pytest.raises(CertificadoInvalido, match="vencido"):
        conferir(gerar_pfx(validade_dias=-1, inicio_dias=-400), SENHA)
    with pytest.raises(CertificadoInvalido, match="ICP-Brasil"):
        conferir(gerar_pfx(org_ac="Outra AC"), SENHA)


def test_conferir_recusa_arquivo_grande():
    with pytest.raises(CertificadoInvalido, match="grande"):
        conferir(b"\x30" + b"\x00" * (60 * 1024), SENHA)


# ---------------------------------------------------------------------------
# Envio e cofre
# ---------------------------------------------------------------------------


async def test_envio_cifra_e_material_abre(client_with_auth_a, chave_cofre):
    http, user, client_a, db = client_with_auth_a
    pfx = gerar_pfx()
    r = _enviar(http, pfx, client_id=client_a.id)
    assert r.status_code == 201, r.text
    corpo = r.json()
    assert corpo["documento"] == CNPJ_A and corpo["status"] == "valido"
    assert "pfx" not in str(corpo).lower() and SENHA not in r.text

    cert = (await db.execute(select(CertificadoA1).where(CertificadoA1.id == uuid.UUID(corpo["id"])))).scalar_one()
    assert cert.pfx_cifrado != pfx and SENHA.encode() not in cert.senha_cifrada

    material = await cofre.obter_material(db, cert.id, tenant_id=cert.tenant_id, finalidade="teste")
    x509.load_pem_x509_certificate(material.cert_pem)
    serialization.load_pem_private_key(material.chave_pem, password=None)
    assert material.documento == CNPJ_A and material.cadeia_pem.startswith(b"-----BEGIN CERTIFICATE")
    assert "chave_pem" not in repr(material)

    # Mesmo certificado de novo: recusado.
    assert _enviar(http, pfx, client_id=client_a.id).status_code == 409


async def test_envio_recusa_cnpj_de_outro_cliente(client_with_auth_a, chave_cofre):
    http, _, client_a, _ = client_with_auth_a
    r = _enviar(http, gerar_pfx(documento="99888777000161"), client_id=client_a.id)
    assert r.status_code == 400
    assert "99888777000161" in r.json()["detail"]


async def test_envio_sem_chave_do_cofre_503(client_with_auth_a, monkeypatch):
    monkeypatch.setattr(settings, "CERT_ENCRYPTION_KEY", "", raising=False)
    http, _, client_a, _ = client_with_auth_a
    assert _enviar(http, gerar_pfx(), client_id=client_a.id).status_code == 503


async def test_envio_senha_errada_400(client_with_auth_a, chave_cofre):
    http, _, client_a, _ = client_with_auth_a
    r = _enviar(http, gerar_pfx(), client_id=client_a.id, senha="errada")
    assert r.status_code == 400 and "Senha" in r.json()["detail"]


async def test_membro_nao_envia_e_outro_escritorio_nao_ve(
    client_with_auth_a, client_with_auth_b, chave_cofre
):
    http_a, _, client_a, _ = client_with_auth_a
    http_b, _, client_b, _ = client_with_auth_b  # user_b é MEMBER do escritório B
    assert _enviar(http_a, gerar_pfx(), client_id=client_a.id).status_code == 201
    assert _enviar(http_b, gerar_pfx(documento=client_b.document), client_id=client_b.id).status_code == 403
    assert http_b.get("/api/v1/certificados").json() == []
    issuer_a = _criar_emissor(http_a, client_a.id)
    assert http_b.get(f"/api/v1/certificados/emissao/{issuer_a}").status_code == 404


async def test_bloqueado_e_vencido_nao_entregam_material(client_with_auth_a, chave_cofre):
    http, user, client_a, db = client_with_auth_a
    cert_id = uuid.UUID(_enviar(http, gerar_pfx(), client_id=client_a.id).json()["id"])

    assert http.post(f"/api/v1/certificados/{cert_id}/bloquear", json={"motivo": "teste"}).status_code == 200
    with pytest.raises(cofre.CertificadoIndisponivel, match="bloqueado"):
        await cofre.obter_material(db, cert_id, tenant_id=user.tenant_id, finalidade="teste")

    assert http.post(f"/api/v1/certificados/{cert_id}/desbloquear").status_code == 200
    cert = (await db.execute(select(CertificadoA1).where(CertificadoA1.id == cert_id))).scalar_one()
    cert.valido_ate = datetime.now(timezone.utc) - timedelta(days=1)
    await db.commit()
    with pytest.raises(cofre.CertificadoIndisponivel, match="venceu"):
        await cofre.obter_material(db, cert.id, tenant_id=cert.tenant_id, finalidade="teste")
    assert http.get("/api/v1/certificados").json()[0]["status"] == "vencido"


# ---------------------------------------------------------------------------
# Liberação da emissão por emissor
# ---------------------------------------------------------------------------


class _ProviderTeste:
    def __init__(self, ok=True):
        self.ok = ok
        self.chamadas = []

    async def testar_conexao(self, material, issuer):
        self.chamadas.append((material.documento, issuer.cnpj))
        return {"ok": self.ok, "mensagem": "ok" if self.ok else "recusado pelo teste", "detalhes": {}}


@pytest.fixture
def provider_teste(monkeypatch):
    from app.domain.invoices.providers import nfse_nacional

    p = _ProviderTeste()
    monkeypatch.setattr(nfse_nacional, "NfseNacionalProvider", lambda *a, **k: p)
    return p


async def test_modo_proprio_libera_so_depois_do_teste(client_with_auth_a, chave_cofre, provider_teste):
    http, _, client_a, _ = client_with_auth_a
    issuer = _criar_emissor(http, client_a.id)
    estado = http.get(f"/api/v1/certificados/emissao/{issuer}").json()
    assert estado["emissao_liberada"] is False
    assert any("Escolha como" in p for p in estado["pendencias"])

    cert_id = _enviar(http, gerar_pfx(), client_id=client_a.id).json()["id"]
    estado = http.put(f"/api/v1/certificados/emissao/{issuer}",
                      json={"modo_certificado": "proprio", "certificado_id": cert_id}).json()
    assert estado["emissao_liberada"] is False
    assert estado["pendencias"] == ["Faça o teste de emissão para liberar."]

    estado = http.post(f"/api/v1/certificados/emissao/{issuer}/testar").json()
    assert estado["emissao_liberada"] is True and estado["ultimo_teste_ok"] is True
    assert provider_teste.chamadas == [(CNPJ_A, CNPJ_A)]

    # Teste reprovado bloqueia de novo.
    provider_teste.ok = False
    estado = http.post(f"/api/v1/certificados/emissao/{issuer}/testar").json()
    assert estado["emissao_liberada"] is False
    assert "recusado pelo teste" in estado["pendencias"][0]


async def test_modo_procuracao_exige_certificado_do_escritorio_e_confirmacao(
    client_with_auth_a, chave_cofre, provider_teste
):
    http, _, client_a, _ = client_with_auth_a
    issuer = _criar_emissor(http, client_a.id)
    cert_cliente = _enviar(http, gerar_pfx(), client_id=client_a.id).json()["id"]
    cert_escr = _enviar(
        http, gerar_pfx(documento=CNPJ_ESCRITORIO, nome="ESCRITORIO"), escopo="escritorio"
    ).json()["id"]

    r = http.put(f"/api/v1/certificados/emissao/{issuer}",
                 json={"modo_certificado": "procuracao", "certificado_id": cert_cliente})
    assert r.status_code == 400

    estado = http.put(f"/api/v1/certificados/emissao/{issuer}",
                      json={"modo_certificado": "procuracao", "certificado_id": cert_escr}).json()
    assert any("procuração eletrônica" in p for p in estado["pendencias"])
    assert http.post(f"/api/v1/certificados/emissao/{issuer}/testar").status_code == 409

    estado = http.put(f"/api/v1/certificados/emissao/{issuer}", json={
        "modo_certificado": "procuracao", "certificado_id": cert_escr, "procuracao_confirmada": True,
    }).json()
    assert estado["procuracao_confirmada_em"] is not None
    estado = http.post(f"/api/v1/certificados/emissao/{issuer}/testar").json()
    assert estado["emissao_liberada"] is True

    # Trocar o modo zera o teste e bloqueia.
    estado = http.put(f"/api/v1/certificados/emissao/{issuer}",
                      json={"modo_certificado": "proprio", "certificado_id": cert_cliente}).json()
    assert estado["emissao_liberada"] is False and estado["ultimo_teste_ok"] is None
    assert estado["procuracao_confirmada_em"] is None

    # Modo próprio com certificado de outro CNPJ: recusado.
    r = http.put(f"/api/v1/certificados/emissao/{issuer}",
                 json={"modo_certificado": "proprio", "certificado_id": cert_escr})
    assert r.status_code == 400


async def test_apagar_certificado_bloqueia_emissor(client_with_auth_a, chave_cofre, provider_teste):
    http, _, client_a, _ = client_with_auth_a
    issuer = _criar_emissor(http, client_a.id)
    cert_id = _enviar(http, gerar_pfx(), client_id=client_a.id).json()["id"]
    http.put(f"/api/v1/certificados/emissao/{issuer}",
             json={"modo_certificado": "proprio", "certificado_id": cert_id})
    assert http.post(f"/api/v1/certificados/emissao/{issuer}/testar").json()["emissao_liberada"]

    r = http.delete(f"/api/v1/certificados/{cert_id}")
    assert r.status_code == 200 and r.json()["emissores_afetados"] == 1
    estado = http.get(f"/api/v1/certificados/emissao/{issuer}").json()
    assert estado["emissao_liberada"] is False and estado["certificado_id"] is None


# ---------------------------------------------------------------------------
# Emissão
# ---------------------------------------------------------------------------


def _criar_nota(http, issuer):
    r = http.post("/api/v1/invoices", json={
        "issuer_id": issuer, "competencia": date.today().replace(day=1).isoformat(),
        "valor_servico": "150.00", "descricao_servico": "Honorários contábeis",
        "tomador_nome": "Tomador", "tomador_cpf_cnpj": "11222333000181",
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def test_emissao_sem_liberacao_responde_409(client_with_auth_a, chave_cofre, monkeypatch):
    monkeypatch.setattr(settings, "NFSE_PROVIDER", "nacional", raising=False)
    http, _, client_a, _ = client_with_auth_a
    issuer = _criar_emissor(http, client_a.id)
    nota = _criar_nota(http, issuer)
    r = http.post(f"/api/v1/invoices/{nota}/emit")
    assert r.status_code == 409
    assert "não liberada" in r.json()["detail"]


async def test_emissao_liberada_passa_o_certificado_ao_provider(
    client_with_auth_a, chave_cofre, provider_teste, monkeypatch
):
    from app.domain.invoices.repository import InvoiceRepository
    from app.domain.invoices.service import InvoiceService

    http, user, client_a, db = client_with_auth_a
    issuer = _criar_emissor(http, client_a.id)
    cert_id = _enviar(http, gerar_pfx(), client_id=client_a.id).json()["id"]
    http.put(f"/api/v1/certificados/emissao/{issuer}",
             json={"modo_certificado": "proprio", "certificado_id": cert_id})
    assert http.post(f"/api/v1/certificados/emissao/{issuer}/testar").json()["emissao_liberada"]
    nota = uuid.UUID(_criar_nota(http, issuer))

    monkeypatch.setattr(settings, "NFSE_PROVIDER", "nacional", raising=False)

    class _Emissor:
        material = None

        async def emit(self, invoice_data, material=None):
            _Emissor.material = material
            assert invoice_data["cnpj_emissor"] == CNPJ_A
            assert invoice_data["cod_servico_lc116"] == "17.01"
            return {"status": "issued", "numero": "1", "protocol": "P1", "raw": {}, "xml": "<x/>"}

    service = InvoiceService(InvoiceRepository(db))
    await service.queue_emission(nota, user.tenant_id)
    invoice = await service.process_emission_sync(nota, user.tenant_id, _Emissor())
    assert invoice.status == "issued"
    assert _Emissor.material is not None and _Emissor.material.documento == CNPJ_A
    # Número da DPS reservado na nota; reservar de novo (retentativa) reaproveita.
    assert invoice.numero_dps == 1 and invoice.serie_dps == settings.NFSE_SERIE_DPS
    assert (await service._reservar_numero_dps(invoice)).numero_dps == 1
    outra = await service.get_invoice(uuid.UUID(_criar_nota(http, issuer)), user.tenant_id)
    assert (await service._reservar_numero_dps(outra)).numero_dps == 2


async def test_rejeicao_do_padrao_nacional_grava_todas(
    client_with_auth_a, chave_cofre, provider_teste, monkeypatch
):
    from app.domain.invoices.repository import InvoiceRepository
    from app.domain.invoices.service import InvoiceService

    http, user, client_a, db = client_with_auth_a
    issuer = _criar_emissor(http, client_a.id)
    cert_id = _enviar(http, gerar_pfx(), client_id=client_a.id).json()["id"]
    http.put(f"/api/v1/certificados/emissao/{issuer}",
             json={"modo_certificado": "proprio", "certificado_id": cert_id})
    http.post(f"/api/v1/certificados/emissao/{issuer}/testar")
    nota = uuid.UUID(_criar_nota(http, issuer))
    monkeypatch.setattr(settings, "NFSE_PROVIDER", "nacional", raising=False)

    class _Rejeita:
        async def emit(self, invoice_data, material=None):
            return {
                "status": "rejected", "codigo_rejeicao": "E1", "descricao": "Primeira",
                "rejeicoes": [
                    {"codigo": "E1", "descricao": "Primeira", "complemento": "campo x"},
                    {"codigo": "E2", "descricao": "Segunda"},
                ],
                "raw": {},
            }

    service = InvoiceService(InvoiceRepository(db))
    await service.queue_emission(nota, user.tenant_id)
    invoice = await service.process_emission_sync(nota, user.tenant_id, _Rejeita())
    assert invoice.status == "rejected"
    rejeicoes = await InvoiceRepository(db).list_rejections(nota, user.tenant_id)
    assert {(r.codigo_rejeicao, r.descricao) for r in rejeicoes} == {
        ("E1", "Primeira (campo x)"), ("E2", "Segunda"),
    }
