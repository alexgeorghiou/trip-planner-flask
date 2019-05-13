def test_geojson_export(client):
    trip = client.post(
        "/api/trips", json={"title": "Paris", "start_date": "2026-06-01", "end_date": "2026-06-02"}
    ).get_json()
    day = trip["days"][0]["id"]
    for name, lat, lon in (("Louvre", 48.8606, 2.3376), ("Notre-Dame", 48.8530, 2.3499)):
        client.post(f"/api/days/{day}/stops", json={"name": name, "lat": lat, "lon": lon})

    resp = client.get(f"/api/trips/{trip['id']}/geojson")
    assert resp.status_code == 200
    assert resp.mimetype == "application/geo+json"
    data = resp.get_json(force=True)
    assert data["type"] == "FeatureCollection"
    points = [f for f in data["features"] if f["geometry"]["type"] == "Point"]
    lines = [f for f in data["features"] if f["geometry"]["type"] == "LineString"]
    assert [p["properties"]["name"] for p in points] == ["Louvre", "Notre-Dame"]
    assert points[0]["geometry"]["coordinates"] == [2.3376, 48.8606]  # lon, lat order
    assert len(lines) == 1 and lines[0]["properties"]["day"] == 1
