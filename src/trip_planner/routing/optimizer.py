"""Open-path route ordering: nearest-neighbour construction followed by 2-opt improvement.

A day's itinerary is an *open* path (you don't have to return to the first stop), optionally
with a pinned start (e.g. the hotel) and/or a pinned end (e.g. the train station). This is a
small travelling-salesman variant; for the handful of stops a person visits in a day the
NN + 2-opt heuristic is fast and typically within a few percent of optimal.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from .geo import Point, distance_matrix

Matrix = Sequence[Sequence[float]]

# Trying every start point is O(n) times more work; only do it while that stays cheap.
MULTI_START_LIMIT = 30


@dataclass(frozen=True, slots=True)
class RoutePlan:
    order: list[int]
    total_km: float
    original_km: float
    legs_km: list[float] = field(default_factory=list)

    @property
    def saved_km(self) -> float:
        return max(0.0, self.original_km - self.total_km)


def path_length(order: Sequence[int], dist: Matrix) -> float:
    return sum(dist[a][b] for a, b in zip(order, order[1:], strict=False))


def route_length_km(points: Sequence[Point]) -> float:
    return path_length(range(len(points)), distance_matrix(list(points)))


def nearest_neighbour(dist: Matrix, start: int, end: int | None = None) -> list[int]:
    """Greedy tour: always walk to the closest unvisited point. ``end`` (if any) is kept last."""
    n = len(dist)
    unvisited = set(range(n)) - {start}
    if end is not None and end != start:
        unvisited.discard(end)
    order = [start]
    current = start
    while unvisited:
        nxt = min(unvisited, key=lambda j: (dist[current][j], j))
        unvisited.remove(nxt)
        order.append(nxt)
        current = nxt
    if end is not None and end != start:
        order.append(end)
    return order


def two_opt(
    order: list[int],
    dist: Matrix,
    *,
    fix_start: bool = True,
    fix_end: bool = False,
    max_passes: int = 100,
    epsilon: float = 1e-9,
) -> list[int]:
    """Repeatedly reverse sub-paths while doing so shortens the open path."""
    route = list(order)
    n = len(route)
    if n < 3:
        return route
    first = 1 if fix_start else 0
    last = n - 2 if fix_end else n - 1

    for _ in range(max_passes):
        improved = False
        for i in range(first, last):
            for j in range(i + 1, last + 1):
                a = route[i - 1] if i > 0 else None
                b, c = route[i], route[j]
                d = route[j + 1] if j < n - 1 else None
                before = (dist[a][b] if a is not None else 0.0) + (
                    dist[c][d] if d is not None else 0.0
                )
                after = (dist[a][c] if a is not None else 0.0) + (
                    dist[b][d] if d is not None else 0.0
                )
                if after + epsilon < before:
                    route[i : j + 1] = reversed(route[i : j + 1])
                    improved = True
        if not improved:
            break
    return route


def optimize_order(
    dist: Matrix, *, start: int | None = 0, end: int | None = None
) -> list[int]:
    n = len(dist)
    if n <= 2:
        order = list(range(n))
        if start is not None and n == 2 and start == 1:
            order.reverse()
        return order

    if start is not None:
        candidates = [start]
    elif n <= MULTI_START_LIMIT:
        candidates = [i for i in range(n) if i != end]
    else:
        candidates = [0 if end != 0 else 1]

    best: list[int] | None = None
    best_len = float("inf")
    for s in candidates:
        route = two_opt(
            nearest_neighbour(dist, s, end),
            dist,
            fix_start=start is not None,
            fix_end=end is not None,
        )
        length = path_length(route, dist)
        if length < best_len - 1e-9:
            best, best_len = route, length
    assert best is not None
    return best


def optimize_route(
    points: Sequence[Point], *, start: int | None = 0, end: int | None = None
) -> RoutePlan:
    """Return the improved visiting order for ``points`` as indices into the input sequence.

    ``start``/``end`` pin the first/last stop; pass ``start=None`` to let the optimiser
    choose where the day begins.
    """
    n = len(points)
    if n == 0:
        return RoutePlan(order=[], total_km=0.0, original_km=0.0, legs_km=[])
    for name, idx in (("start", start), ("end", end)):
        if idx is not None and not 0 <= idx < n:
            raise IndexError(f"{name} index {idx} out of range for {n} points")
    if start is not None and end is not None and start == end and n > 1:
        raise ValueError("start and end must differ for an open path")

    dist = distance_matrix(list(points))
    order = optimize_order(dist, start=start, end=end)
    legs = [dist[a][b] for a, b in zip(order, order[1:], strict=False)]
    return RoutePlan(
        order=order,
        total_km=sum(legs),
        original_km=path_length(range(n), dist),
        legs_km=legs,
    )
