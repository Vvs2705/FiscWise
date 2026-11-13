"""O tour de boas-vindas aparece só no primeiro acesso da conta."""


async def test_tour_de_boas_vindas_so_no_primeiro_acesso(client_with_auth_a):
    http, *_ = client_with_auth_a
    assert http.get("/api/v1/auth/me").json()["welcome_tour_seen"] is False

    resp = http.post("/api/v1/auth/me/welcome-tour")
    assert resp.status_code == 200, resp.text
    assert http.get("/api/v1/auth/me").json()["welcome_tour_seen"] is True

    # Marcar de novo não muda nada nem dá erro.
    assert http.post("/api/v1/auth/me/welcome-tour").status_code == 200
    assert http.get("/api/v1/auth/me").json()["welcome_tour_seen"] is True


def test_tour_exige_login(client):
    # Sem login (e sem tenant), a requisição é recusada antes de chegar à conta.
    assert client.post("/api/v1/auth/me/welcome-tour").status_code in (400, 401, 403)
