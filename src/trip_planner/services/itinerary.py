"""Trip / day / stop operations that keep the itinerary consistent.

Invariants maintained here:
* a trip has exactly one Day per calendar date in ``[start_date, end_date]``;
* the stops of a day have contiguous positions ``0..n-1``.
"""

from __future__ import annotations

import datetime as dt
import itertools
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from ..errors import ConflictError, DomainError
from ..extensions import db
from ..models import Day, Stop, Trip
from ..routing import Point, RoutePlan, haversine_km, optimize_route

MAX_TRIP_DAYS = 90
MAX_STOPS_PER_DAY = 40

TRIP_FIELDS = ("title", "destination", "start_date", "end_date", "notes")
STOP_FIELDS = (
    "name",
    "address",
    "lat",
    "lon",
    "category",
    "osm_ref",
    "arrival_time",
    "duration_minutes",
    "notes",
)


def daterange(start: dt.date, end: dt.date) -> Iterable[dt.date]:
    for offset in range((end - start).days + 1):
        yield start + dt.timedelta(days=offset)


def _validate_range(start: dt.date, end: dt.date) -> None:
    if end < start:
        raise DomainError("end_date must not be before start_date", field="end_date")
    if (end - start).days + 1 > MAX_TRIP_DAYS:
        raise DomainError(f"trips are limited to {MAX_TRIP_DAYS} days", field="end_date")


# --- trips -----------------------------------------------------------------------------------


def create_trip(data: dict[str, Any]) -> Trip:
    _validate_range(data["start_date"], data["end_date"])
    trip = Trip(**{k: data.get(k) for k in TRIP_FIELDS})
    trip.days = [Day(date=d) for d in daterange(trip.start_date, trip.end_date)]
    db.session.add(trip)
    db.session.commit()
    return trip


def update_trip(trip: Trip, data: dict[str, Any]) -> Trip:
    start = data.get("start_date", trip.start_date)
    end = data.get("end_date", trip.end_date)
    _validate_range(start, end)

    if (start, end) != (trip.start_date, trip.end_date):
        _resize_days(trip, start, end)
    for key in TRIP_FIELDS:
        if key in data:
            setattr(trip, key, data[key])
    db.session.commit()
    return trip


def _resize_days(trip: Trip, start: dt.date, end: dt.date) -> None:
    """Add days for new dates; drop days that fall outside, refusing to lose planned stops."""
    wanted = set(daterange(start, end))
    doomed = [d for d in trip.days if d.date not in wanted]
    busy = [d for d in doomed if d.stops]
    if busy:
        dates = ", ".join(d.date.isoformat() for d in busy)
        raise ConflictError(
            f"cannot shorten trip: stops are planned on {dates}; move or delete them first",
            field="start_date" if busy[0].date < start else "end_date",
        )
    for day in doomed:
        trip.days.remove(day)
    existing = {d.date for d in trip.days}
    for date in sorted(wanted - existing):
        trip.days.append(Day(date=date))
    trip.days.sort(key=lambda d: d.date)


def shift_trip(trip: Trip, new_start: dt.date) -> Trip:
    """Move the whole trip in time, keeping every day's plan attached to its day number."""
    delta = new_start - trip.start_date
    if not delta:
        return trip
    # Re-date in an order that never collides with the (trip_id, date) unique constraint.
    days = sorted(trip.days, key=lambda d: d.date, reverse=delta.days > 0)
    for day in days:
        day.date = day.date + delta
        db.session.flush()
    trip.start_date += delta
    trip.end_date += delta
    db.session.commit()
    return trip


def delete_trip(trip: Trip) -> None:
    db.session.delete(trip)
    db.session.commit()


# --- days ------------------------------------------------------------------------------------


def update_day(day: Day, data: dict[str, Any]) -> Day:
    for key in ("title", "notes"):
        if key in data:
            setattr(day, key, data[key])
    db.session.commit()
    return day


def _renumber(stops: Sequence[Stop]) -> None:
    for i, stop in enumerate(stops):
        stop.position = i


# --- stops -----------------------------------------------------------------------------------


def add_stop(day: Day, data: dict[str, Any], *, position: int | None = None) -> Stop:
    if len(day.stops) >= MAX_STOPS_PER_DAY:
        raise DomainError(f"a day can hold at most {MAX_STOPS_PER_DAY} stops")
    stop = Stop(**{k: data.get(k) for k in STOP_FIELDS})
    stops = list(day.stops)
    index = len(stops) if position is None else max(0, min(position, len(stops)))
    stops.insert(index, stop)
    day.stops[:] = stops
    _renumber(day.stops)
    db.session.commit()
    return stop


def update_stop(stop: Stop, data: dict[str, Any]) -> Stop:
    for key in STOP_FIELDS:
        if key in data:
            setattr(stop, key, data[key])
    db.session.commit()
    return stop


def delete_stop(stop: Stop) -> None:
    day = stop.day
    day.stops.remove(stop)
    _renumber(day.stops)
    db.session.commit()


def reorder_stops(day: Day, stop_ids: Sequence[int]) -> Day:
    current = {s.id: s for s in day.stops}
    if sorted(stop_ids) != sorted(current) or len(set(stop_ids)) != len(stop_ids):
        raise DomainError("stop_ids must list every stop of the day exactly once", field="stop_ids")
    day.stops[:] = [current[i] for i in stop_ids]
    _renumber(day.stops)
    db.session.commit()
    return day


def move_stop(stop: Stop, target: Day, position: int | None = None) -> Stop:
    if target.trip_id != stop.day.trip_id:
        raise DomainError("stops can only move between days of the same trip", field="day_id")
    source = stop.day
    if target is source:
        stops = [s for s in source.stops if s is not stop]
        index = len(stops) if position is None else max(0, min(position, len(stops)))
        stops.insert(index, stop)
        source.stops[:] = stops
        _renumber(source.stops)
        db.session.commit()
        return stop
    if len(target.stops) >= MAX_STOPS_PER_DAY:
        raise DomainError(f"a day can hold at most {MAX_STOPS_PER_DAY} stops")
    source.stops.remove(stop)
    _renumber(source.stops)
    stops = list(target.stops)
    index = len(stops) if position is None else max(0, min(position, len(stops)))
    stops.insert(index, stop)
    target.stops[:] = stops
    _renumber(target.stops)
    db.session.commit()
    return stop


# --- routing ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class DayRoute:
    day: Day
    stops: list[Stop]
    plan: RoutePlan
    applied: bool


def optimize_day(
    day: Day, *, keep_first: bool = True, keep_last: bool = False, apply: bool = True
) -> DayRoute:
    """Compute a shorter visiting order for the day's stops and (optionally) persist it."""
    stops = list(day.stops)
    if keep_last and len(stops) < 2:
        keep_last = False
    plan = optimize_route(
        [Point(s.lat, s.lon) for s in stops],
        start=0 if keep_first and stops else None,
        end=len(stops) - 1 if keep_last else None,
    )
    ordered = [stops[i] for i in plan.order]
    if apply and ordered != stops:
        day.stops[:] = ordered
        _renumber(day.stops)
        db.session.commit()
    return DayRoute(day=day, stops=ordered, plan=plan, applied=apply)


def day_legs_km(day: Day) -> list[float]:
    pts = [Point(s.lat, s.lon) for s in day.stops]
    return [haversine_km(a, b) for a, b in itertools.pairwise(pts)]
