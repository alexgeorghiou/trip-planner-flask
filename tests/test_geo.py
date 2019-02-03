import math

import pytest

from trip_planner.routing.geo import Point, distance_matrix, haversine_km


def test_zero_distance_for_same_point():
    p = Point(48.8584, 2.2945)
    assert haversine_km(p, p) == 0.0


def test_paris_to_london_is_about_344_km():
    paris = Point(48.8566, 2.3522)
    london = Point(51.5074, -0.1278)
    assert haversine_km(paris, london) == pytest.approx(343.5, abs=1.5)


def test_distance_is_symmetric():
    a, b = Point(35.6762, 139.6503), Point(-33.8688, 151.2093)
    assert haversine_km(a, b) == pytest.approx(haversine_km(b, a))


def test_antipodal_points_are_half_circumference():
    d = haversine_km(Point(0, 0), Point(0, 180))
    assert d == pytest.approx(math.pi * 6371.0088, rel=1e-9)


@pytest.mark.parametrize(("lat", "lon"), [(91, 0), (-91, 0), (0, 181), (0, -180.5)])
def test_rejects_out_of_range_coordinates(lat, lon):
    with pytest.raises(ValueError):
        Point(lat, lon)


def test_distance_matrix_is_symmetric_with_zero_diagonal():
    pts = [Point(0, 0), Point(0, 1), Point(1, 1)]
    m = distance_matrix(pts)
    for i in range(3):
        assert m[i][i] == 0.0
        for j in range(3):
            assert m[i][j] == m[j][i]
