"""Small helpers for building itineraries in tests."""

from __future__ import annotations

import datetime as dt

from trip_planner.services import itinerary

BCN = {
    "Sagrada Familia": (41.4036, 2.1744),
    "Park Güell": (41.4145, 2.1527),
    "Casa Batlló": (41.3916, 2.1649),
    "La Boqueria": (41.3817, 2.1716),
    "Barceloneta Beach": (41.3784, 2.1925),
    "Montjuïc Castle": (41.3634, 2.1658),
}


def make_trip(title="Barcelona long weekend", start=dt.date(2026, 5, 1), days=3, **extra):
    return itinerary.create_trip({
        "title": title,
        "destination": "Barcelona",
        "start_date": start,
        "end_date": start + dt.timedelta(days=days - 1),
        **extra,
    })


def add_named_stops(day, names):
    return [
        itinerary.add_stop(day, {"name": n, "lat": BCN[n][0], "lon": BCN[n][1]}) for n in names
    ]
