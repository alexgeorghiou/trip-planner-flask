import datetime as dt

import pytest

from trip_planner.errors import ConflictError, DomainError
from trip_planner.services import itinerary

from .factories import BCN, add_named_stops, make_trip


@pytest.fixture()
def ctx(app):
    with app.app_context():
        yield


def names(day):
    return [s.name for s in day.stops]


def positions(day):
    return [s.position for s in day.stops]


def test_create_trip_generates_one_day_per_date(ctx):
    trip = make_trip(days=4)
    assert [d.date for d in trip.days] == [dt.date(2026, 5, i) for i in range(1, 5)]
    assert [d.number for d in trip.days] == [1, 2, 3, 4]


def test_rejects_inverted_and_overlong_ranges(ctx):
    with pytest.raises(DomainError):
        itinerary.create_trip(
            {"title": "x", "start_date": dt.date(2026, 1, 2), "end_date": dt.date(2026, 1, 1)}
        )
    with pytest.raises(DomainError, match="90 days"):
        make_trip(days=91)


def test_extending_trip_adds_days(ctx):
    trip = make_trip(days=2)
    itinerary.update_trip(
        trip, {"end_date": dt.date(2026, 5, 4), "start_date": dt.date(2026, 4, 30)}
    )
    assert [d.date.day for d in trip.days] == [30, 1, 2, 3, 4]


def test_shortening_drops_empty_days(ctx):
    trip = make_trip(days=3)
    itinerary.update_trip(trip, {"end_date": dt.date(2026, 5, 1)})
    assert len(trip.days) == 1


def test_shortening_refuses_to_drop_planned_stops(ctx):
    trip = make_trip(days=3)
    add_named_stops(trip.days[2], ["La Boqueria"])
    with pytest.raises(ConflictError, match="2026-05-03"):
        itinerary.update_trip(trip, {"end_date": dt.date(2026, 5, 2)})


def test_shift_trip_keeps_plans_with_their_day(ctx):
    trip = make_trip(days=3)
    add_named_stops(trip.days[0], ["Park Güell"])
    add_named_stops(trip.days[1], ["La Boqueria"])
    itinerary.shift_trip(trip, dt.date(2026, 5, 2))  # overlapping shift forward
    assert trip.start_date == dt.date(2026, 5, 2)
    assert [(d.date.day, names(d)) for d in trip.days] == [
        (2, ["Park Güell"]),
        (3, ["La Boqueria"]),
        (4, []),
    ]
    itinerary.shift_trip(trip, dt.date(2026, 4, 29))  # and backward
    assert [d.date.day for d in trip.days] == [29, 30, 1]


def test_add_stop_appends_or_inserts(ctx):
    trip = make_trip()
    day = trip.days[0]
    add_named_stops(day, ["Park Güell", "La Boqueria"])
    lat, lon = BCN["Casa Batlló"]
    itinerary.add_stop(day, {"name": "Casa Batlló", "lat": lat, "lon": lon}, position=1)
    assert names(day) == ["Park Güell", "Casa Batlló", "La Boqueria"]
    assert positions(day) == [0, 1, 2]


def test_delete_stop_renumbers(ctx):
    day = make_trip().days[0]
    stops = add_named_stops(day, ["Park Güell", "Casa Batlló", "La Boqueria"])
    itinerary.delete_stop(stops[0])
    assert names(day) == ["Casa Batlló", "La Boqueria"]
    assert positions(day) == [0, 1]


def test_reorder_requires_exact_permutation(ctx):
    day = make_trip().days[0]
    a, b, c = add_named_stops(day, ["Park Güell", "Casa Batlló", "La Boqueria"])
    itinerary.reorder_stops(day, [c.id, a.id, b.id])
    assert names(day) == ["La Boqueria", "Park Güell", "Casa Batlló"]
    for bad in ([a.id, b.id], [a.id, a.id, b.id], [a.id, b.id, c.id, 999]):
        with pytest.raises(DomainError):
            itinerary.reorder_stops(day, bad)


def test_move_stop_between_days(ctx):
    trip = make_trip()
    d1, d2 = trip.days[0], trip.days[1]
    a, _b = add_named_stops(d1, ["Park Güell", "Casa Batlló"])
    add_named_stops(d2, ["La Boqueria"])
    itinerary.move_stop(a, d2, position=0)
    assert names(d1) == ["Casa Batlló"] and positions(d1) == [0]
    assert names(d2) == ["Park Güell", "La Boqueria"] and positions(d2) == [0, 1]


def test_move_stop_within_day(ctx):
    day = make_trip().days[0]
    a, _b, _c = add_named_stops(day, ["Park Güell", "Casa Batlló", "La Boqueria"])
    itinerary.move_stop(a, day)
    assert names(day) == ["Casa Batlló", "La Boqueria", "Park Güell"]


def test_move_stop_across_trips_is_rejected(ctx):
    a = add_named_stops(make_trip().days[0], ["Park Güell"])[0]
    other = make_trip(title="Other").days[0]
    with pytest.raises(DomainError):
        itinerary.move_stop(a, other)


def test_optimize_day_orders_stops_geographically(ctx):
    day = make_trip().days[0]
    # Zig-zag order: north, south, north, south...
    add_named_stops(
        day,
        [
            "Park Güell",
            "Montjuïc Castle",
            "Sagrada Familia",
            "La Boqueria",
            "Casa Batlló",
            "Barceloneta Beach",
        ],
    )
    before = sum(itinerary.day_legs_km(day))
    result = itinerary.optimize_day(day)
    after = sum(itinerary.day_legs_km(day))
    assert names(day)[0] == "Park Güell"  # start pinned
    assert after < before
    assert after == pytest.approx(result.plan.total_km)
    assert positions(day) == list(range(6))


def test_optimize_day_preview_does_not_persist(ctx):
    day = make_trip().days[0]
    add_named_stops(day, ["Park Güell", "Montjuïc Castle", "Sagrada Familia"])
    original = names(day)
    result = itinerary.optimize_day(day, apply=False)
    assert names(day) == original
    assert [s.name for s in result.stops] != original


def test_optimize_day_with_pinned_end(ctx):
    day = make_trip().days[0]
    add_named_stops(day, ["Park Güell", "Barceloneta Beach", "Sagrada Familia", "Montjuïc Castle"])
    itinerary.optimize_day(day, keep_first=True, keep_last=True)
    assert names(day)[0] == "Park Güell"
    assert names(day)[-1] == "Montjuïc Castle"


def test_optimize_empty_day_is_a_noop(ctx):
    day = make_trip().days[0]
    result = itinerary.optimize_day(day, keep_last=True)
    assert result.stops == [] and result.plan.total_km == 0
