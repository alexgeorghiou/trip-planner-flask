def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_openapi_document_is_served(client):
    resp = client.get("/api/openapi.json")
    assert resp.status_code == 200
    assert resp.get_json()["info"]["title"] == "Trip Planner API"


def test_openapi_documents_every_resource(client):
    spec = client.get("/api/openapi.json").get_json()
    paths = set(spec["paths"])
    assert {
        "/api/trips",
        "/api/trips/{trip_id}",
        "/api/trips/{trip_id}/shift",
        "/api/days/{day_id}/stops",
        "/api/days/{day_id}/stops/order",
        "/api/days/{day_id}/optimize",
        "/api/stops/{stop_id}/move",
        "/api/places/search",
        "/api/trips/{trip_id}/shares",
        "/api/shared/{token}",
    } <= paths
    schemas = spec["components"]["schemas"]
    # Partial (PATCH) variants get their own component names.
    assert {"Trip", "TripBase", "TripBasePatch", "Stop", "StopPatch", "RoutePlan"} <= set(schemas)


def test_swagger_ui_is_served(client):
    assert client.get("/api/docs").status_code == 200


def test_unknown_geocoder_config_fails_fast():
    import pytest

    from trip_planner.app import create_app

    with pytest.raises(ValueError):
        create_app("testing", {"GEOCODER": "nope"})
