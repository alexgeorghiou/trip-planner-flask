"""Days, stops and per-day route optimisation."""

from __future__ import annotations

from typing import Any

from flask.views import MethodView
from flask_smorest import Blueprint

from ..extensions import db
from ..models import Day, Stop
from ..schemas import (
    DaySchema,
    OptimizeArgsSchema,
    ReorderSchema,
    RoutePlanSchema,
    StopCreateSchema,
    StopMoveSchema,
    StopSchema,
)
from ..services import itinerary

blp = Blueprint("itinerary", __name__, description="Edit days and the stops planned on them")


@blp.route("/days/<int:day_id>")
class DayItem(MethodView):
    @blp.response(200, DaySchema)
    def get(self, day_id: int) -> Day:
        """A single day with its stops"""
        return db.get_or_404(Day, day_id)

    @blp.arguments(DaySchema(partial=True))
    @blp.response(200, DaySchema)
    def patch(self, data: dict[str, Any], day_id: int) -> Day:
        """Set a day's title or notes"""
        return itinerary.update_day(db.get_or_404(Day, day_id), data)


@blp.route("/days/<int:day_id>/stops")
class DayStops(MethodView):
    @blp.arguments(StopCreateSchema)
    @blp.response(201, StopSchema)
    def post(self, data: dict[str, Any], day_id: int) -> Stop:
        """Add a stop (appended unless `position` is given)"""
        position = data.pop("position", None)
        return itinerary.add_stop(db.get_or_404(Day, day_id), data, position=position)


@blp.route("/days/<int:day_id>/stops/order")
class DayStopOrder(MethodView):
    @blp.arguments(ReorderSchema)
    @blp.response(200, DaySchema)
    def put(self, data: dict[str, Any], day_id: int) -> Day:
        """Set the visiting order explicitly (e.g. after drag and drop)"""
        return itinerary.reorder_stops(db.get_or_404(Day, day_id), data["stop_ids"])


@blp.route("/days/<int:day_id>/optimize")
class DayOptimize(MethodView):
    @blp.arguments(OptimizeArgsSchema, location="query")
    @blp.response(200, RoutePlanSchema)
    def post(self, args: dict[str, Any], day_id: int) -> dict[str, Any]:
        """Reorder stops to shorten the walking distance (nearest neighbour + 2-opt)"""
        result = itinerary.optimize_day(db.get_or_404(Day, day_id), **args)
        return {
            "day_id": result.day.id,
            "applied": result.applied,
            "total_km": round(result.plan.total_km, 3),
            "original_km": round(result.plan.original_km, 3),
            "saved_km": round(result.plan.saved_km, 3),
            "legs_km": [round(x, 3) for x in result.plan.legs_km],
            "stops": result.stops,
        }


@blp.route("/stops/<int:stop_id>")
class StopItem(MethodView):
    @blp.response(200, StopSchema)
    def get(self, stop_id: int) -> Stop:
        """A single stop"""
        return db.get_or_404(Stop, stop_id)

    @blp.arguments(StopSchema(partial=True))
    @blp.response(200, StopSchema)
    def patch(self, data: dict[str, Any], stop_id: int) -> Stop:
        """Edit a stop's details"""
        return itinerary.update_stop(db.get_or_404(Stop, stop_id), data)

    @blp.response(204)
    def delete(self, stop_id: int) -> None:
        """Remove a stop; the remaining stops are renumbered"""
        itinerary.delete_stop(db.get_or_404(Stop, stop_id))


@blp.route("/stops/<int:stop_id>/move")
class StopMove(MethodView):
    @blp.arguments(StopMoveSchema)
    @blp.response(200, StopSchema)
    def post(self, data: dict[str, Any], stop_id: int) -> Stop:
        """Move a stop to another day of the same trip, or another position"""
        stop = db.get_or_404(Stop, stop_id)
        target = db.get_or_404(Day, data["day_id"])
        return itinerary.move_stop(stop, target, data.get("position"))
