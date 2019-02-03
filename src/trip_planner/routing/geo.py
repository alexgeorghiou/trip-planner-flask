"""Great-circle distance helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass

EARTH_RADIUS_KM = 6371.0088  # IUGG mean radius


@dataclass(frozen=True, slots=True)
class Point:
    lat: float
    lon: float

    def __post_init__(self) -> None:
        if not -90.0 <= self.lat <= 90.0:
            raise ValueError(f"latitude out of range: {self.lat}")
        if not -180.0 <= self.lon <= 180.0:
            raise ValueError(f"longitude out of range: {self.lon}")


def haversine_km(a: Point, b: Point) -> float:
    """Distance in kilometres between two WGS84 points along the great circle."""
    lat1, lon1, lat2, lon2 = map(math.radians, (a.lat, a.lon, b.lat, b.lon))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    # Clamp guards against tiny floating point overshoot for antipodal points.
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(h)))


def distance_matrix(points: list[Point]) -> list[list[float]]:
    n = len(points)
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = haversine_km(points[i], points[j])
            matrix[i][j] = matrix[j][i] = d
    return matrix
