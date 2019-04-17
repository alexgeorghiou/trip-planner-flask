"""marshmallow schemas: request validation and response shapes for the OpenAPI spec."""

from __future__ import annotations

from typing import Any

from flask import url_for
from marshmallow import Schema, ValidationError, fields, validate, validates_schema

Lat = validate.Range(min=-90, max=90)
Lon = validate.Range(min=-180, max=180)


# --- stops -----------------------------------------------------------------------------------


class StopSchema(Schema):
    id = fields.Int(dump_only=True)
    day_id = fields.Int(dump_only=True)
    position = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    address = fields.Str(allow_none=True, validate=validate.Length(max=500))
    lat = fields.Float(required=True, validate=Lat)
    lon = fields.Float(required=True, validate=Lon)
    category = fields.Str(allow_none=True, validate=validate.Length(max=64))
    osm_ref = fields.Str(allow_none=True, validate=validate.Length(max=32))
    arrival_time = fields.Time(allow_none=True)
    duration_minutes = fields.Int(allow_none=True, validate=validate.Range(min=0, max=24 * 60))
    notes = fields.Str(allow_none=True)


class StopCreateSchema(StopSchema):
    position = fields.Int(load_only=True, validate=validate.Range(min=0))


class StopMoveSchema(Schema):
    day_id = fields.Int(required=True)
    position = fields.Int(validate=validate.Range(min=0))


class ReorderSchema(Schema):
    stop_ids = fields.List(fields.Int(), required=True)


# --- days ------------------------------------------------------------------------------------


class DaySchema(Schema):
    id = fields.Int(dump_only=True)
    date = fields.Date(dump_only=True)
    number = fields.Int(dump_only=True)
    title = fields.Str(allow_none=True, validate=validate.Length(max=200))
    notes = fields.Str(allow_none=True)
    stops = fields.List(fields.Nested(StopSchema), dump_only=True)
    distance_km = fields.Method("get_distance_km", dump_only=True)

    def get_distance_km(self, day: Any) -> float:
        from .services.itinerary import day_legs_km

        return round(sum(day_legs_km(day)), 3)


class OptimizeArgsSchema(Schema):
    keep_first = fields.Bool(load_default=True, metadata={"description": "Pin the first stop"})
    keep_last = fields.Bool(load_default=False, metadata={"description": "Pin the last stop"})
    apply = fields.Bool(load_default=True, metadata={"description": "Persist the new order"})


class RoutePlanSchema(Schema):
    day_id = fields.Int()
    applied = fields.Bool()
    total_km = fields.Float()
    original_km = fields.Float()
    saved_km = fields.Float()
    legs_km = fields.List(fields.Float())
    stops = fields.List(fields.Nested(StopSchema))


# --- trips -----------------------------------------------------------------------------------


class TripBaseSchema(Schema):
    id = fields.Int(dump_only=True)
    title = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    destination = fields.Str(allow_none=True, validate=validate.Length(max=200))
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    notes = fields.Str(allow_none=True)
    length_days = fields.Int(dump_only=True)
    stop_count = fields.Int(dump_only=True)

    @validates_schema(skip_on_field_errors=False)
    def check_dates(self, data: dict[str, Any], **_: Any) -> None:
        start, end = data.get("start_date"), data.get("end_date")
        if start and end and end < start:
            raise ValidationError("end_date must not be before start_date", "end_date")


class TripSummarySchema(TripBaseSchema):
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class TripSchema(TripSummarySchema):
    days = fields.List(fields.Nested(DaySchema), dump_only=True)


class TripShiftSchema(Schema):
    start_date = fields.Date(required=True)


class TripListArgsSchema(Schema):
    q = fields.Str(metadata={"description": "Filter by title or destination"})


class SharedTripSchema(Schema):
    """What a share-link holder can see: the plan, without private notes or metadata."""

    title = fields.Str()
    destination = fields.Str(allow_none=True)
    start_date = fields.Date()
    end_date = fields.Date()
    length_days = fields.Int()
    days = fields.List(fields.Nested(DaySchema(exclude=("id",))))


# --- places ----------------------------------------------------------------------------------


class PlaceSearchArgsSchema(Schema):
    q = fields.Str(required=True, validate=validate.Length(min=2, max=200))
    limit = fields.Int(load_default=5, validate=validate.Range(min=1, max=20))
    country = fields.Str(
        metadata={"description": "Comma separated ISO 3166-1 alpha-2 codes, e.g. 'es,fr'"},
        validate=validate.Regexp(r"^[A-Za-z]{2}(,[A-Za-z]{2})*$"),
    )


class PlaceSchema(Schema):
    name = fields.Str()
    display_name = fields.Str()
    lat = fields.Float()
    lon = fields.Float()
    category = fields.Str(allow_none=True)
    osm_ref = fields.Str(allow_none=True)


# --- sharing ---------------------------------------------------------------------------------


class ShareLinkCreateSchema(Schema):
    label = fields.Str(allow_none=True, validate=validate.Length(max=100))
    expires_in_days = fields.Int(allow_none=True, validate=validate.Range(min=1, max=365))


class ShareLinkSchema(Schema):
    id = fields.Int()
    token = fields.Str()
    label = fields.Str(allow_none=True)
    created_at = fields.DateTime()
    expires_at = fields.DateTime(allow_none=True)
    revoked_at = fields.DateTime(allow_none=True)
    active = fields.Method("get_active")
    url = fields.Method("get_url")

    def get_active(self, link: Any) -> bool:
        return link.is_active()

    def get_url(self, link: Any) -> str:
        return url_for("web.shared_trip", token=link.token, _external=True)
