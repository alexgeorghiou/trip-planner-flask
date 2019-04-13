from trip_planner.app import create_app
from trip_planner.geocoding import FakeGeocoder, Geocoder, GeocodingError


def test_search_uses_configured_geocoder(client):
    resp = client.get("/api/places/search?q=trevi")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body[0]["name"] == "Trevi Fountain"
    assert body[0]["osm_ref"] == "W32590911"


def test_search_args_are_validated(client):
    assert client.get("/api/places/search").status_code == 422
    assert client.get("/api/places/search?q=a").status_code == 422
    assert client.get("/api/places/search?q=rome&limit=100").status_code == 422
    assert client.get("/api/places/search?q=rome&country=spain").status_code == 422


def test_country_codes_are_passed_through():
    class Spy(FakeGeocoder):
        def search(self, query, *, limit=5, country_codes=None):
            self.seen = (query, limit, country_codes)
            return []

    spy = Spy()
    client = create_app("testing", geocoder=spy).test_client()
    client.get("/api/places/search?q=museum&limit=3&country=it,fr")
    assert spy.seen == ("museum", 3, ["it", "fr"])


def test_upstream_failure_is_502():
    class Broken(Geocoder):
        def search(self, query, *, limit=5, country_codes=None):
            raise GeocodingError("Nominatim returned HTTP 503")

    client = create_app("testing", geocoder=Broken()).test_client()
    resp = client.get("/api/places/search?q=rome")
    assert resp.status_code == 502
    assert "503" in resp.get_json()["message"]
