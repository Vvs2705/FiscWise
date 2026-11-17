"""Assinatura XMLDSig da DPS e dos pedidos de evento.

Padrão usado (mesmo da NFS-e devolvida pelo Sistema Nacional nos exemplos
oficiais do nfelib): assinatura enveloped, RSA-SHA256, digest SHA-256,
canonicalização C14N 2001 (inclusiva), transforms enveloped-signature + c14n,
``<Signature>`` sem prefixo no namespace xmldsig, logo após o elemento
assinado, com o certificado X.509 em KeyInfo.

A chave vem do cofre de certificados (PEM em memória, sem senha) e não é
gravada em disco aqui.
"""

from __future__ import annotations

from lxml import etree

C14N_2001 = "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"


class AssinaturaInvalida(RuntimeError):
    """Não foi possível assinar ou verificar o XML."""


def _signer(signature_algorithm: str, digest_algorithm: str):
    import signxml

    signer = signxml.XMLSigner(
        method=signxml.methods.enveloped,
        signature_algorithm=signature_algorithm,
        digest_algorithm=digest_algorithm,
        c14n_algorithm=C14N_2001,
    )
    # <Signature xmlns="http://www.w3.org/2000/09/xmldsig#"> sem prefixo ds:
    signer.namespaces = {None: signxml.namespaces.ds}
    return signer


def assinar_xml(
    xml: bytes,
    *,
    referencia_id: str,
    chave_pem: bytes,
    cert_pem: bytes,
    signature_algorithm: str = "rsa-sha256",
    digest_algorithm: str = "sha256",
) -> bytes:
    """Assina o elemento com ``Id=referencia_id`` e devolve o XML assinado."""
    parser = etree.XMLParser(no_network=True, resolve_entities=False, remove_blank_text=True)
    raiz = etree.fromstring(xml, parser)
    if raiz.find(f".//*[@Id='{referencia_id}']") is None:
        raise AssinaturaInvalida(f"Elemento com Id {referencia_id} não encontrado no XML.")
    try:
        assinado = _signer(signature_algorithm, digest_algorithm).sign(
            raiz,
            key=chave_pem,
            cert=cert_pem.decode("ascii") if isinstance(cert_pem, bytes) else cert_pem,
            reference_uri=f"#{referencia_id}",
        )
    except Exception as exc:  # noqa: BLE001 - mensagem limpa para quem chama
        raise AssinaturaInvalida(f"Falha ao assinar o XML: {type(exc).__name__}") from exc
    return etree.tostring(assinado, xml_declaration=True, encoding="UTF-8")


def verificar_assinatura(xml_assinado: bytes, cert_pem: bytes) -> None:
    """Confere a assinatura com o certificado informado (usado nos testes e no
    diagnóstico). Levanta AssinaturaInvalida se não bater."""
    import signxml
    from signxml.verifier import SignatureConfiguration

    config = SignatureConfiguration(
        signature_methods=frozenset({signxml.SignatureMethod.RSA_SHA256}),
        digest_algorithms=frozenset({signxml.DigestAlgorithm.SHA256}),
    )
    try:
        signxml.XMLVerifier().verify(
            xml_assinado,
            x509_cert=cert_pem.decode("ascii") if isinstance(cert_pem, bytes) else cert_pem,
            expect_config=config,
        )
    except Exception as exc:  # noqa: BLE001
        raise AssinaturaInvalida(f"Assinatura inválida: {exc}") from exc
