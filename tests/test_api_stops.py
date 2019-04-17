import pytest

PLACES = {
    "Colosseum": (41.8902, 12.4922),
    "Trevi Fountain": (41.9009, 12.4833),
    "Pantheon": (41.8986, 12.4769),
    "Vatican Museums": (41.9065, 12.4536),
    "Trastevere": (41.8897, 12.4708),
}


@pytest.fixture()
def trip(client):
    resp = client.post(
        "/api/trips", json={"title": "Rome", "start_date": "2026-04-10", "end_date": "2026-04-11"}
    )
    return resp.get_json()


def add(client, day_id, name, **extra):
    lat, lon = PLACES[name]
    resp = client.post(
        f"/api/days/{day_id}/stops", json={"name": name, "lat": lat, "lon": lon, **extra}
    )
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


def stop_names(client, day_id):
    return [s["name"] for s in client.get(f"/api/days/{day_id}").get_json()["stops"]]


def test_add_stops_and_day_distance(client, trip):
    day = trip["days"][0]["id"]
    add(client, day, "Colosseum", arrival_time="09:30:00", duration_minutes=90)
    add(client, day, "Pantheon")
    body = client.get(f"/api/days/{day}").get_json()
    assert [s["position"] for s in body["stops"]] == [0, 1]
    assert body["stops"][0]["arrival_time"] == "09:30:00"
    assert body["distance_km"] == pytest.approx(1.4, abs=0.2)


def test_insert_at_position(client, trip):
    day = trip["days"][0]["id"]
    add(client, day, "Colosseum")
    add(client, day, "Pantheon")
    add(client, day, "Trevi Fountain", position=0)
    assert stop_names(client, day) == ["Trevi Fountain", "Colosseum", "Pantheon"]


@pytest.mark.parametrize(
    "bad", [{"lat": 95}, {"lon": -200}, {"name": ""}, {"duration_minutes": -5}]
)
def test_invalid_stop_payloads(client, trip, bad):
    body = {"name": "x", "lat": 41.9, "lon": 12.5, **bad}
    resp = client.post(f"/api/days/{trip['days'][0]['id']}/stops", json=body)
    assert resp.status_code == 422


def test_unknown_day_is_404(client):
    resp = client.post("/api/days/999/stops", json={"name": "x", "lat": 1, "lon": 1})
    assert resp.status_code == 404


def test_patch_and_delete_stop(client, trip):
    day = trip["days"][0]["id"]
    a = add(client, day, "Colosseum")
    add(client, day, "Pantheon")
    resp = client.patch(f"/api/stops/{a['id']}", json={"notes": "book tickets online"})
    assert resp.get_json()["notes"] == "book tickets online"
    assert client.delete(f"/api/stops/{a['id']}").status_code == 204
    body = client.get(f"/api/days/{day}").get_json()
    assert [(s["name"], s["position"]) for s in body["stops"]] == [("Pantheon", 0)]


def test_reorder(client, trip):
    day = trip["days"][0]["id"]
    ids = [add(client, day, n)["id"] for n in ("Colosseum", "Pantheon", "Trevi Fountain")]
    resp = client.put(f"/api/days/{day}/stops/order", json={"stop_ids": ids[::-1]})
    assert resp.status_code == 200
    assert stop_names(client, day) == ["Trevi Fountain", "Pantheon", "Colosseum"]
    resp = client.put(f"/api/days/{day}/stops/order", json={"stop_ids": ids[:2]})
    assert resp.status_code == 422


def test_move_between_days(client, trip):
    d1, d2 = trip["days"][0]["id"], trip["days"][1]["id"]
    a = add(client, d1, "Colosseum")
    resp = client.post(f"/api/stops/{a['id']}/move", json={"day_id": d2})
    assert resp.status_code == 200 and resp.get_json()["day_id"] == d2
    assert stop_names(client, d1) == []
    assert stop_names(client, d2) == ["Colosseum"]


def test_optimize_endpoint(client, trip):
    day = trip["days"][0]["id"]
    for name in ("Colosseum", "Vatican Museums", "Trastevere", "Trevi Fountain", "Pantheon"):
        add(client, day, name)

    preview = client.post(f"/api/days/{day}/optimize?apply=false").get_json()
    assert preview["applied"] is False
    assert preview["total_km"] < preview["original_km"]
    assert preview["saved_km"] == pytest.approx(
        preview["original_km"] - preview["total_km"], abs=0.002
    )
    assert stop_names(client, day)[1] == "Vatican Museums"  # unchanged

    applied = client.post(f"/api/days/{day}/optimize").get_json()
    assert applied["applied"] is True
    assert stop_names(client, day) == [s["name"] for s in applied["stops"]]
    assert stop_names(client, day)[0] == "Colosseum"
    assert len(applied["legs_km"]) == 4


def test_day_title_patch(client, trip):
    day = trip["days"][0]["id"]
    resp = client.patch(f"/api/days/{day}", json={"title": "Ancient Rome"})
    assert resp.get_json()["title"] == "Ancient Rome"
