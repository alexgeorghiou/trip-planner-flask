"""Place search proxied through the configured geocoder."""

from __future__ import annotations

from typing import Any

from flask.views import MethodView
from flask_smorest import Blueprint, abort

from ..extensions import get_geocoder
from ..geocoding import GeocodingError, Place
from ..schemas import PlaceSchema, PlaceSearchArgsSchema

blp = Blueprint("places", __name__, description="Search OpenStreetMap places to add as stops")


@blp.route("/places/search")
class PlaceSearch(MethodView):
    @blp.arguments(PlaceSearchArgsSchema, location="query")
    @blp.response(200, PlaceSchema(many=True))
    @blp.alt_response(502, description="Upstream geocoder failed")
    def get(self, args: dict[str, Any]) -> list[Place]:
        """Free-text place search"""
        countries = args["country"].split(",") if args.get("country") else None
        try:
            return get_geocoder().search(args["q"], limit=args["limit"], country_codes=countries)
        except GeocodingError as exc:
            abort(502, message=str(exc))
