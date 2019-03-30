"""Share links and the public read-only trip view."""

from __future__ import annotations

from typing import Any

from flask.views import MethodView
from flask_smorest import Blueprint, abort

from ..extensions import db
from ..models import ShareLink, Trip
from ..schemas import SharedTripSchema, ShareLinkCreateSchema, ShareLinkSchema
from ..services import sharing

blp = Blueprint("shares", __name__, description="Share a trip read-only via an unguessable link")


@blp.route("/trips/<int:trip_id>/shares")
class TripShares(MethodView):
    @blp.response(200, ShareLinkSchema(many=True))
    def get(self, trip_id: int) -> list[ShareLink]:
        """All share links of a trip, including revoked ones"""
        return db.get_or_404(Trip, trip_id).share_links

    @blp.arguments(ShareLinkCreateSchema)
    @blp.response(201, ShareLinkSchema)
    def post(self, data: dict[str, Any], trip_id: int) -> ShareLink:
        """Create a share link"""
        return sharing.create_share_link(db.get_or_404(Trip, trip_id), **data)


@blp.route("/shares/<int:link_id>")
class ShareItem(MethodView):
    @blp.response(200, ShareLinkSchema)
    def delete(self, link_id: int) -> ShareLink:
        """Revoke a share link (idempotent)"""
        return sharing.revoke_share_link(db.get_or_404(ShareLink, link_id))


@blp.route("/shared/<token>")
class SharedTrip(MethodView):
    @blp.response(200, SharedTripSchema)
    def get(self, token: str) -> Trip:
        """Read-only itinerary for a share token"""
        trip = sharing.resolve_share_token(token)
        if trip is None:
            abort(404, message="This share link is invalid, expired or has been revoked.")
        return trip
