from trip_planner.geocoding import FakeGeocoder, Place


def test_matches_case_insensitively():
    g = FakeGeocoder()
    hits = g.search("eiffel")
    assert [p.name for p in hits] == ["Eiffel Tower"]


def test_display_name_matches_rank_after_name_matches():
    g = FakeGeocoder([
        Place("Old Town", "Old Town, Rome", 41.9, 12.5),
        Place("Rome Gate", "Gate, Somewhere", 41.0, 12.0),
    ])
    assert [p.name for p in g.search("rome")] == ["Rome Gate", "Old Town"]


def test_limit_and_blank_query():
    g = FakeGeocoder()
    assert len(g.search("barcelona", limit=2)) == 2
    assert g.search("   ") == []
    assert g.queries == ["barcelona", "   "]


def test_osm_ref_formatting():
    assert Place("x", "x", 0, 0, osm_type="way", osm_id=12).osm_ref == "W12"
    assert Place("x", "x", 0, 0).osm_ref is None
