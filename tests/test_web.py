import re

import pytest

HX = {"HX-Request": "true"}


@pytest.fixture()
def trip_id(client):
    resp = client.post("/trips", data={"title": "Barcelona", "destination": "Barcelona",
                                       "start_date": "2026-05-01", "end_date": "2026-05-02",
                                       "notes": ""})
    assert resp.status_code == 303
    return int(resp.headers["Location"].rsplit("/", 1)[-1])


def first_day_id(client, trip_id):
    return client.get(f"/api/trips/{trip_id}").get_json()["days"][0]["id"]


def add_from_search(client, day_id, query):
    html = client.get(f"/days/{day_id}/search?q={query}", headers=HX).get_data(as_text=True)
    fields = dict(re.findall(r'name="(\w+)" value="([^"]*)"', html))
    return client.post(f"/days/{day_id}/stops", data=fields, headers=HX)


def test_index_lists_trips(client, trip_id):
    html = client.get("/").get_data(as_text=True)
    assert "Barcelona" in html and "2 days" in html


def test_create_trip_form_errors_rerender(client):
    resp = client.post("/trips", data={"title": "", "start_date": "2026-05-02",
                                       "end_date": "2026-05-01"})
    assert resp.status_code == 422
    html = resp.get_data(as_text=True)
    assert "field-error" in html


def test_htmx_create_uses_hx_redirect(client):
    resp = client.post("/trips", data={"title": "Paris", "start_date": "2026-06-01",
                                       "end_date": "2026-06-01"}, headers=HX)
    assert resp.status_code == 204
    assert resp.headers["HX-Redirect"].startswith("/trips/")


def test_trip_page_renders_days_and_tools(client, trip_id):
    html = client.get(f"/trips/{trip_id}").get_data(as_text=True)
    assert html.count('class="day card"') == 2
    assert "Search a place to add" in html
    assert 'id="shares"' in html


def test_search_and_add_stop(client, trip_id):
    day = first_day_id(client, trip_id)
    resp = add_from_search(client, day, "sagrada")
    assert resp.status_code == 200
    assert resp.headers["HX-Trigger"] == "itinerary-changed"
    html = resp.get_data(as_text=True)
    assert "Added Sagrada Familia." in html
    assert f'id="day-{day}"' in html


def test_search_with_no_results(client, trip_id):
    day = first_day_id(client, trip_id)
    html = client.get(f"/days/{day}/search?q=atlantis", headers=HX).get_data(as_text=True)
    assert "No places found" in html


def test_invalid_stop_returns_422_fragment(client, trip_id):
    day = first_day_id(client, trip_id)
    resp = client.post(f"/days/{day}/stops", data={"name": "x", "lat": "200", "lon": "0"}, headers=HX)
    assert resp.status_code == 422
    assert "flash error" in resp.get_data(as_text=True)


def test_nudge_delete_and_optimize(client, trip_id):
    day = first_day_id(client, trip_id)
    for q in ("park g", "montju", "sagrada", "boqueria"):
        add_from_search(client, day, q)
    stops = client.get(f"/api/days/{day}").get_json()["stops"]
    names = [s["name"] for s in stops]

    client.post(f"/stops/{stops[1]['id']}/up", headers=HX)
    moved = [s["name"] for s in client.get(f"/api/days/{day}").get_json()["stops"]]
    assert moved == [names[1], names[0], *names[2:]]

    html = client.post(f"/days/{day}/optimize", headers=HX).get_data(as_text=True)
    assert "Route reordered" in html or "Already in a good order" in html

    client.post(f"/stops/{stops[0]['id']}/delete", headers=HX)
    assert len(client.get(f"/api/days/{day}").get_json()["stops"]) == 3


def test_optimize_needs_three_stops(client, trip_id):
    day = first_day_id(client, trip_id)
    html = client.post(f"/days/{day}/optimize", headers=HX).get_data(as_text=True)
    assert "at least three stops" in html


def test_map_json(client, trip_id):
    day = first_day_id(client, trip_id)
    add_from_search(client, day, "casa batll")
    data = client.get(f"/trips/{trip_id}/map.json").get_json()
    assert data["days"][0]["stops"][0]["name"] == "Casa Batlló"
    assert data["days"][1]["stops"] == []


def test_share_flow_renders_read_only_page(client, trip_id):
    day = first_day_id(client, trip_id)
    add_from_search(client, day, "boqueria")
    html = client.post(f"/trips/{trip_id}/shares", data={"label": "friends", "expires_in_days": "7"},
                       headers=HX).get_data(as_text=True)
    url = re.search(r'value="(http://[^"]+/s/[^"]+)"', html).group(1)
    path = url.split("localhost", 1)[1]

    resp = client.get(path)
    assert resp.status_code == 200
    assert resp.headers["X-Robots-Tag"] == "noindex, nofollow"
    page = resp.get_data(as_text=True)
    assert "La Boqueria" in page and "Read-only view" in page
    # No editing affordances leak into the shared page.
    assert "hx-post" not in page and "Search a place" not in page

    link_id = client.get(f"/api/trips/{trip_id}/shares").get_json()[0]["id"]
    html = client.post(f"/shares/{link_id}/revoke", headers=HX).get_data(as_text=True)
    assert "revoked" in html
    assert client.get(path).status_code == 404


def test_unknown_pages_use_html_404(client):
    resp = client.get("/s/whatever")
    assert resp.status_code == 404
    assert "share link has expired" in resp.get_data(as_text=True)


def test_delete_trip(client, trip_id):
    resp = client.post(f"/trips/{trip_id}/delete", headers=HX)
    assert resp.headers["HX-Redirect"] == "/"
    assert client.get(f"/trips/{trip_id}").status_code == 404
