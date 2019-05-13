"""Trips and their days."""

from __future__ import annotations

import json
from typing import Any

from flask import Response
from flask.views import MethodView
from flask_smorest import Blueprint
from sqlalchemy import func, or_, select

from ..extensions import db
from ..models import Trip
from ..schemas import (
    DaySchema,
    TripBaseSchema,
    TripListArgsSchema,
    TripSchema,
    TripShiftSchema,
    TripSummarySchema,
)
from ..services import itinerary
from ..services.export import trip_geojson

blp = Blueprint("trips", __name__, description="Plan trips and browse their days")


@blp.route("/trips")
class TripCollection(MethodView):
    @blp.arguments(TripListArgsSchema, location="query")
    @blp.response(200, TripSummarySchema(many=True))
    @blp.paginate()
    def get(self, args: dict[str, Any], pagination_parameters: Any) -> list[Trip]:
        """List trips, soonest first"""
        stmt = select(Trip)
        if q := args.get("q"):
            like = f"%{q.strip()}%"
            stmt = stmt.where(or_(Trip.title.ilike(like), Trip.destination.ilike(like)))
        pagination_parameters.item_count = db.session.scalar(
            select(func.count()).select_from(stmt.subquery())
        )
        stmt = (
            stmt.order_by(Trip.start_date, Trip.id)
            .offset(pagination_parameters.first_item)
            .limit(pagination_parameters.page_size)
        )
        return list(db.session.scalars(stmt))

    @blp.arguments(TripBaseSchema)
    @blp.response(201, TripSchema)
    def post(self, data: dict[str, Any]) -> Trip:
        """Create a trip; one empty day is generated per date"""
        return itinerary.create_trip(data)


@blp.route("/trips/<int:trip_id>")
class TripItem(MethodView):
    @blp.response(200, TripSchema)
    def get(self, trip_id: int) -> Trip:
        """Full itinerary: days with their ordered stops"""
        return db.get_or_404(Trip, trip_id)

    @blp.arguments(TripBaseSchema(partial=True))
    @blp.response(200, TripSchema)
    def patch(self, data: dict[str, Any], trip_id: int) -> Trip:
        """Update details or change the date range (refuses to drop days with stops)"""
        return itinerary.update_trip(db.get_or_404(Trip, trip_id), data)

    @blp.response(204)
    def delete(self, trip_id: int) -> None:
        """Delete a trip and everything in it"""
        itinerary.delete_trip(db.get_or_404(Trip, trip_id))


@blp.route("/trips/<int:trip_id>/shift")
class TripShift(MethodView):
    @blp.arguments(TripShiftSchema)
    @blp.response(200, TripSchema)
    def post(self, data: dict[str, Any], trip_id: int) -> Trip:
        """Move the whole trip to a new start date, keeping each day's plan"""
        return itinerary.shift_trip(db.get_or_404(Trip, trip_id), data["start_date"])


@blp.route("/trips/<int:trip_id>/days")
class TripDays(MethodView):
    @blp.response(200, DaySchema(many=True))
    def get(self, trip_id: int) -> list[Any]:
        """Days of a trip in date order"""
        return db.get_or_404(Trip, trip_id).days


@blp.route("/trips/<int:trip_id>/geojson")
class TripGeoJSON(MethodView):
    @blp.response(200, content_type="application/geo+json")
    def get(self, trip_id: int) -> Response:
        """Stops and per-day routes as a GeoJSON FeatureCollection"""
        body = json.dumps(trip_geojson(db.get_or_404(Trip, trip_id)))
        return Response(body, mimetype="application/geo+json")
