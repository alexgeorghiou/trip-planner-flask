"""The real client is exercised against an in-process httpx MockTransport: no network."""

import httpx
import pytest

from trip_planner.geocoding.base import GeocodingError
from trip_planner.geocoding.nominatim import NominatimGeocoder

SAMPLE = [
    {
        "place_id": 1,
        "osm_type": "way",
        "osm_id": 5013364,
        "lat": "48.8582599",
        "lon": "2.2945006",
        "category": "man_made",
        "type": "tower",
        "place_rank": 30,
        "name": "Eiffel Tower",
        "display_name": "Eiffel Tower, Avenue Gustave Eiffel, Paris, France",
    },
    {"lat": "not-a-number", "lon": "2", "display_name": "broken"},
]


def make(handler, **kwargs):
    return NominatimGeocoder(
        user_agent="trip-planner-tests/1.0 (test@example.org)",
        transport=httpx.MockTransport(handler),
        sleep=lambda _s: None,
        **kwargs,
    )


def test_sends_identifying_headers_and_params():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["request"] = request
        return httpx.Response(200, json=SAMPLE)

    g = make(handler, email="ops@example.org")
    places = g.search("eiffel tower", limit=3, country_codes=["FR"])

    req = seen["request"]
    assert req.url.path == "/search"
    assert req.headers["User-Agent"] == "trip-planner-tests/1.0 (test@example.org)"
    assert req.headers["Accept-Language"] == "en"
    assert req.url.params["q"] == "eiffel tower"
    assert req.url.params["format"] == "jsonv2"
    assert req.url.params["limit"] == "3"
    assert req.url.params["countrycodes"] == "fr"
    assert req.url.params["email"] == "ops@example.org"

    assert len(places) == 1  # malformed row skipped
    p = places[0]
    assert p.name == "Eiffel Tower"
    assert p.lat == pytest.approx(48.8582599)
    assert p.osm_ref == "W5013364"
    assert p.category == "man_made"
    assert p.extra["type"] == "tower"


def test_falls_back_to_first_display_segment_for_name():
    g = make(lambda r: httpx.Response(200, json=[{"lat": "1", "lon": "2", "display_name": "Foo, Bar"}]))
    assert g.search("foo")[0].name == "Foo"


def test_blank_query_does_not_hit_the_network():
    def handler(request):
        raise AssertionError("should not be called")

    assert make(handler).search("  ") == []


@pytest.mark.parametrize("status", [429, 500, 503])
def test_http_errors_become_geocoding_errors(status):
    g = make(lambda r: httpx.Response(status))
    with pytest.raises(GeocodingError, match=str(status)):
        g.search("x")


def test_transport_errors_become_geocoding_errors():
    def handler(request):
        raise httpx.ConnectTimeout("boom", request=request)

    with pytest.raises(GeocodingError):
        make(handler).search("x")


def test_unexpected_payload_shape():
    with pytest.raises(GeocodingError):
        make(lambda r: httpx.Response(200, json={"error": "nope"})).search("x")


def test_rejects_generic_user_agent():
    with pytest.raises(ValueError):
        NominatimGeocoder(user_agent="python-httpx/0.28")


def test_throttles_to_one_request_per_interval():
    now = [100.0]
    sleeps: list[float] = []

    def sleep(s):
        sleeps.append(s)
        now[0] += s

    g = NominatimGeocoder(
        user_agent="trip-planner-tests/1.0",
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=[])),
        clock=lambda: now[0],
        sleep=sleep,
        min_interval=1.0,
    )
    g.search("a")
    now[0] += 0.25
    g.search("b")
    assert sleeps == [pytest.approx(0.75)]
