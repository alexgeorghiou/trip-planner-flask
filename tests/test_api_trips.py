import json


def create_trip(client, **overrides):
    body = {
        "title": "Rome in spring",
        "destination": "Rome",
        "start_date": "2026-04-10",
        "end_date": "2026-04-12",
        **overrides,
    }
    resp = client.post("/api/trips", json=body)
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


def test_create_and_fetch_trip(client):
    trip = create_trip(client)
    assert trip["length_days"] == 3
    assert [d["number"] for d in trip["days"]] == [1, 2, 3]
    assert trip["days"][0]["date"] == "2026-04-10"

    resp = client.get(f"/api/trips/{trip['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Rome in spring"


def test_validation_errors_are_422(client):
    resp = client.post("/api/trips", json={"title": "", "start_date": "2026-01-02",
                                           "end_date": "2026-01-01"})
    assert resp.status_code == 422
    errors = resp.get_json()["errors"]["json"]
    assert "title" in errors and "end_date" in errors


def test_unknown_fields_are_rejected(client):
    resp = client.post("/api/trips", json={"title": "x", "start_date": "2026-01-01",
                                           "end_date": "2026-01-01", "owner": "me"})
    assert resp.status_code == 422


def test_domain_limit_surfaces_as_422(client):
    resp = client.post("/api/trips", json={"title": "World tour", "start_date": "2026-01-01",
                                           "end_date": "2026-12-31"})
    assert resp.status_code == 422
    assert "90 days" in resp.get_json()["message"]


def test_list_filters_and_paginates(client):
    create_trip(client, title="Rome in spring", start_date="2026-04-10", end_date="2026-04-12")
    create_trip(client, title="Kyoto temples", destination="Kyoto",
                start_date="2026-03-01", end_date="2026-03-05")
    create_trip(client, title="Paris weekend", destination="Paris",
                start_date="2026-06-01", end_date="2026-06-02")

    resp = client.get("/api/trips")
    assert [t["title"] for t in resp.get_json()] == ["Kyoto temples", "Rome in spring", "Paris weekend"]

    resp = client.get("/api/trips?q=kyo")
    assert [t["title"] for t in resp.get_json()] == ["Kyoto temples"]

    resp = client.get("/api/trips?page=2&page_size=2")
    assert [t["title"] for t in resp.get_json()] == ["Paris weekend"]
    pagination = json.loads(resp.headers["X-Pagination"])
    assert pagination["total"] == 3 and pagination["total_pages"] == 2


def test_patch_extends_trip(client):
    trip = create_trip(client)
    resp = client.patch(f"/api/trips/{trip['id']}", json={"end_date": "2026-04-14", "notes": "pack light"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["length_days"] == 5 and body["notes"] == "pack light"


def test_patch_cannot_drop_days_with_stops(client):
    trip = create_trip(client)
    last_day = trip["days"][-1]["id"]
    client.post(f"/api/days/{last_day}/stops", json={"name": "Pantheon", "lat": 41.8986, "lon": 12.4769})
    resp = client.patch(f"/api/trips/{trip['id']}", json={"end_date": "2026-04-11"})
    assert resp.status_code == 409
    assert resp.get_json()["errors"]["json"]["end_date"]
    # Nothing changed.
    assert client.get(f"/api/trips/{trip['id']}").get_json()["length_days"] == 3


def test_shift_trip(client):
    trip = create_trip(client)
    resp = client.post(f"/api/trips/{trip['id']}/shift", json={"start_date": "2026-05-01"})
    body = resp.get_json()
    assert body["start_date"] == "2026-05-01" and body["end_date"] == "2026-05-03"


def test_delete_trip(client):
    trip = create_trip(client)
    assert client.delete(f"/api/trips/{trip['id']}").status_code == 204
    assert client.get(f"/api/trips/{trip['id']}").status_code == 404


def test_days_listing(client):
    trip = create_trip(client)
    days = client.get(f"/api/trips/{trip['id']}/days").get_json()
    assert len(days) == 3 and all(d["stops"] == [] for d in days)


def test_api_404_is_json(client):
    resp = client.get("/api/trips/12345")
    assert resp.status_code == 404
    assert resp.is_json and resp.get_json()["code"] == 404
