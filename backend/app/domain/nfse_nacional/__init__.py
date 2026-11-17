"""Emissão de NFS-e pelo padrão nacional (Sistema Nacional NFS-e / Sefin Nacional).

Módulos:
- dps: monta e valida a DPS (Declaração de Prestação de Serviço) no leiaute 1.01.
- eventos: monta o pedido de registro de evento (cancelamento).
- assinatura: assina XML (XMLDSig enveloped, RSA-SHA256, C14N 2001).
- cliente: chama a API da Sefin Nacional com TLS mútuo (certificado A1).

O provider que junta tudo fica em app/domain/invoices/providers/nfse_nacional.py.
"""
