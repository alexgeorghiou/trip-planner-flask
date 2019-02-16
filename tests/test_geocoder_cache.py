import pytest

from trip_planner.geocoding import (
    CachingGeocoder,
    FakeGeocoder,
    NominatimGeocoder,
    build_geocoder,
)


def test_repeated_queries_are_served_from_cache():
    fake = FakeGeocoder()
    g = CachingGeocoder(fake)
    first = g.search("Louvre")
    second = g.search("  louvre ")
    assert first == second
    assert fake.queries == ["Louvre"]
    assert (g.hits, g.misses) == (1, 1)


def test_limit_is_part_of_the_key():
    fake = FakeGeocoder()
    g = CachingGeocoder(fake)
    g.search("paris", limit=1)
    g.search("paris", limit=3)
    assert len(fake.queries) == 2


def test_evicts_least_recently_used():
    fake = FakeGeocoder()
    g = CachingGeocoder(fake, maxsize=2)
    g.search("a")
    g.search("b")
    g.search("a")  # refresh a
    g.search("c")  # evicts b
    g.search("b")
    assert fake.queries == ["a", "b", "c", "b"]


def test_build_geocoder_from_config():
    assert isinstance(build_geocoder({"GEOCODER": "fake"}), FakeGeocoder)
    real = build_geocoder({"GEOCODER": "nominatim", "NOMINATIM_USER_AGENT": "tp-test/1.0"})
    assert isinstance(real, CachingGeocoder)
    assert isinstance(real.inner, NominatimGeocoder)
    real.close()
    with pytest.raises(ValueError):
        build_geocoder({"GEOCODER": "google"})
