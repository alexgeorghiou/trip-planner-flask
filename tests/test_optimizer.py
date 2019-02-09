import itertools
import random

import pytest

from trip_planner.routing.geo import Point, distance_matrix
from trip_planner.routing.optimizer import (
    nearest_neighbour,
    optimize_route,
    path_length,
    two_opt,
)


def line_points(xs):
    return [Point(0.0, x) for x in xs]


def brute_force_best(points, start=0, end=None):
    dist = distance_matrix(points)
    n = len(points)
    middle = [i for i in range(n) if i not in {start, end}]
    best = float("inf")
    for perm in itertools.permutations(middle):
        route = [start, *perm] + ([end] if end is not None else [])
        best = min(best, path_length(route, dist))
    return best


def test_empty_and_single_point():
    assert optimize_route([]).order == []
    plan = optimize_route([Point(1, 1)])
    assert plan.order == [0]
    assert plan.total_km == 0.0


def test_points_on_a_line_are_visited_in_sequence():
    # Shuffled positions along the equator; start pinned at the westernmost.
    pts = line_points([0.0, 0.3, 0.1, 0.4, 0.2])
    plan = optimize_route(pts, start=0)
    assert plan.order == [0, 2, 4, 1, 3]
    assert plan.total_km < plan.original_km
    assert plan.saved_km == pytest.approx(plan.original_km - plan.total_km)


def test_legs_sum_to_total():
    pts = line_points([0.0, 0.3, 0.1, 0.4])
    plan = optimize_route(pts)
    assert sum(plan.legs_km) == pytest.approx(plan.total_km)
    assert len(plan.legs_km) == len(pts) - 1


def test_pinned_end_stays_last():
    pts = line_points([0.0, 0.5, 0.1, 0.2])
    plan = optimize_route(pts, start=0, end=1)
    assert plan.order[0] == 0
    assert plan.order[-1] == 1
    assert sorted(plan.order) == [0, 1, 2, 3]


def test_free_start_can_begin_anywhere():
    # Starting at index 0 (the middle) forces backtracking; a free start avoids it.
    pts = line_points([0.2, 0.0, 0.4])
    pinned = optimize_route(pts, start=0)
    free = optimize_route(pts, start=None)
    assert free.total_km < pinned.total_km
    assert free.order in ([1, 0, 2], [2, 0, 1])


def test_two_opt_untangles_a_crossing():
    # Square corners visited in a crossing order: 0 -> 2 -> 1 -> 3.
    pts = [Point(0, 0), Point(0, 0.01), Point(0.01, 0.01), Point(0.01, 0)]
    dist = distance_matrix(pts)
    crossed = [0, 2, 1, 3]
    fixed = two_opt(crossed, dist)
    assert path_length(fixed, dist) < path_length(crossed, dist)
    assert fixed[0] == 0


def test_nearest_neighbour_visits_every_point_once():
    rng = random.Random(1)
    pts = [Point(rng.uniform(40, 41), rng.uniform(2, 3)) for _ in range(12)]
    order = nearest_neighbour(distance_matrix(pts), 0)
    assert sorted(order) == list(range(12))


@pytest.mark.parametrize("seed", range(8))
def test_close_to_optimal_on_small_random_instances(seed):
    rng = random.Random(seed)
    pts = [Point(rng.uniform(41.35, 41.45), rng.uniform(2.10, 2.22)) for _ in range(7)]
    plan = optimize_route(pts, start=0)
    optimum = brute_force_best(pts, start=0)
    assert plan.total_km <= optimum * 1.05
    assert plan.total_km >= optimum - 1e-9


@pytest.mark.parametrize(("start", "end"), [(5, None), (0, 0), (None, 9)])
def test_invalid_pins_are_rejected(start, end):
    pts = line_points([0.0, 0.1, 0.2])
    with pytest.raises((IndexError, ValueError)):
        optimize_route(pts, start=start, end=end)


def test_never_longer_than_input_order():
    rng = random.Random(42)
    for _ in range(20):
        pts = [Point(rng.uniform(-1, 1), rng.uniform(-1, 1)) for _ in range(rng.randint(3, 15))]
        plan = optimize_route(pts, start=0)
        assert plan.total_km <= plan.original_km + 1e-9
