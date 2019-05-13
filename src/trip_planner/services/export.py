"""Export an itinerary as GeoJSON (RFC 7946) for use in other mapping tools."""

from __future__ import annotations

from typing import Any

from ..models import Trip


def trip_geojson(trip: Trip) -> dict[str, Any]:
    features: list[dict[str, Any]] = []
    for day in trip.days:
        coords = [[s.lon, s.lat] for s in day.stops]  # GeoJSON is lon, lat
        for stop in day.stops:
            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [stop.lon, stop.lat]},
                    "properties": {
                        "kind": "stop",
                        "day": day.number,
                        "date": day.date.isoformat(),
                        "order": stop.position + 1,
                        "name": stop.name,
                        "address": stop.address,
                        "osm_ref": stop.osm_ref,
                    },
                }
            )
        if len(coords) > 1:
            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": coords},
                    "properties": {
                        "kind": "route",
                        "day": day.number,
                        "date": day.date.isoformat(),
                    },
                }
            )
    return {"type": "FeatureCollection", "features": features}
