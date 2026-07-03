"""Camada fina de acesso a NF-e.

TODO acesso a NF-e (montagem, serialização e parse de XML) passa por este
módulo — o resto do projeto nunca importa nfelib diretamente. Isso isola a
lib fiscal atrás de uma interface própria e facilita trocar de biblioteca
no futuro sem tocar nos chamadores.

Escopo: apenas bindings/XML (nfelib). Assinatura com certificado e
transmissão à SEFAZ (erpbrasil.edoc) ficam fora deste módulo.
"""

from nfelib.nfe.bindings.v4_0.nfe_v4_00 import Nfe


def build_nfe_exemplo(
    cnpj_emitente: str = "12345678000195",
    razao_social: str = "Empresa Exemplo LTDA",
    numero_nota: str = "123",
    serie: str = "1",
) -> Nfe:
    """Monta uma NF-e mínima de exemplo com dados fictícios.

    ponytail: só ide + emit; não é XSD-completa (sem det/total/pag).
    Expandir campos quando houver emissão real.
    """
    return Nfe(
        infNFe=Nfe.InfNfe(
            versao="4.00",
            Id=f"NFe35260101{cnpj_emitente}55{serie.zfill(3)}{numero_nota.zfill(9)}1000000123",
            ide=Nfe.InfNfe.Ide(
                cUF="35",
                natOp="Venda",
                mod="55",
                serie=serie,
                nNF=numero_nota,
            ),
            emit=Nfe.InfNfe.Emit(CNPJ=cnpj_emitente, xNome=razao_social),
        )
    )


def serialize_nfe(nfe: Nfe) -> str:
    """Serializa uma NF-e para XML (string)."""
    return nfe.to_xml()


def parse_nfe(xml: str) -> Nfe:
    """Parseia o XML de uma NF-e e retorna o objeto binding."""
    return Nfe.from_xml(xml)
