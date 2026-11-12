"""Procurações (/ecac/proxies): revogar é terminal e idempotente (B-01)."""

PROXY = {
    "outorgante_cpf_cnpj": "10000000000145",
    "procurador_cpf": "10000000019",
    "data_validade": "2027-01-31",
}


def _criar(http):
    resp = http.post("/api/v1/ecac/proxies", json=PROXY)
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "ativa"
    return resp.json()["id"]


def test_revogar_e_idempotente(client_with_auth_a):
    http = client_with_auth_a[0]
    pid = _criar(http)
    for _ in range(2):
        resp = http.put(f"/api/v1/ecac/proxies/{pid}", json={"status": "revogada"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "revogada"


def test_revogada_nao_volta_a_ativa(client_with_auth_a):
    http = client_with_auth_a[0]
    pid = _criar(http)
    assert http.put(f"/api/v1/ecac/proxies/{pid}", json={"status": "revogada"}).status_code == 200
    resp = http.put(f"/api/v1/ecac/proxies/{pid}", json={"status": "ativa"})
    assert resp.status_code == 409
    assert http.get(f"/api/v1/ecac/proxies/{pid}").json()["status"] == "revogada"


def test_revogar_de_outro_tenant_e_404(client_with_auth_a, client_with_auth_b):
    pid = _criar(client_with_auth_a[0])
    resp = client_with_auth_b[0].put(f"/api/v1/ecac/proxies/{pid}", json={"status": "revogada"})
    assert resp.status_code == 404
