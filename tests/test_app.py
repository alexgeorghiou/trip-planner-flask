def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_openapi_document_is_served(client):
    resp = client.get("/api/openapi.json")
    assert resp.status_code == 200
    assert resp.get_json()["info"]["title"] == "Trip Planner API"
