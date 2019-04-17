import pytest


@pytest.fixture()
def trip(client):
    resp = client.post(
        "/api/trips",
        json={
            "title": "Kyoto",
            "start_date": "2026-03-01",
            "end_date": "2026-03-02",
            "notes": "private notes",
        },
    )
    trip = resp.get_json()
    client.post(
        f"/api/days/{trip['days'][0]['id']}/stops",
        json={"name": "Fushimi Inari", "lat": 34.9671, "lon": 135.7727},
    )
    return trip


def test_share_lifecycle(client, trip):
    resp = client.post(
        f"/api/trips/{trip['id']}/shares", json={"label": "parents", "expires_in_days": 30}
    )
    assert resp.status_code == 201
    link = resp.get_json()
    assert link["active"] is True
    assert link["url"].endswith(f"/s/{link['token']}")

    shared = client.get(f"/api/shared/{link['token']}")
    assert shared.status_code == 200
    body = shared.get_json()
    assert body["title"] == "Kyoto"
    assert body["days"][0]["stops"][0]["name"] == "Fushimi Inari"
    assert "notes" not in body and "id" not in body

    revoked = client.delete(f"/api/shares/{link['id']}").get_json()
    assert revoked["active"] is False and revoked["revoked_at"]
    assert client.get(f"/api/shared/{link['token']}").status_code == 404


def test_list_shares(client, trip):
    client.post(f"/api/trips/{trip['id']}/shares", json={})
    client.post(f"/api/trips/{trip['id']}/shares", json={"label": "friends"})
    links = client.get(f"/api/trips/{trip['id']}/shares").get_json()
    assert [link["label"] for link in links] == [None, "friends"]


def test_unknown_token_is_404(client):
    assert client.get("/api/shared/not-a-real-token").status_code == 404


def test_share_api_has_no_write_endpoints(client, trip):
    token = client.post(f"/api/trips/{trip['id']}/shares", json={}).get_json()["token"]
    for method in ("post", "put", "patch", "delete"):
        assert getattr(client, method)(f"/api/shared/{token}").status_code == 405
