"""HTML views. Every mutating endpoint returns the smallest fragment HTMX needs to swap."""

from __future__ import annotations

from typing import Any

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from marshmallow import Schema, ValidationError
from sqlalchemy import select

from ..errors import DomainError
from ..extensions import db, get_geocoder
from ..geocoding import GeocodingError
from ..models import Day, ShareLink, Stop, Trip
from ..schemas import ShareLinkCreateSchema, StopCreateSchema, TripBaseSchema
from ..services import itinerary, sharing

bp = Blueprint("web", __name__)


@bp.app_template_global("day_legs")
def day_legs(day: Day) -> list[float]:
    return itinerary.day_legs_km(day)


@bp.app_errorhandler(404)
def not_found(err: Exception) -> Any:
    if request.path.startswith("/api/"):
        # Keep flask-smorest's JSON error body for API clients.
        return current_app.extensions["smorest_api"].handle_http_exception(err)
    return render_template("404.html"), 404


def is_htmx() -> bool:
    return request.headers.get("HX-Request") == "true"


def form_data(schema: Schema) -> dict[str, Any]:
    """Load an HTML form through a marshmallow schema; blank inputs mean "not provided"."""
    raw = {k: v for k, v in request.form.items() if v.strip() != "" and k in schema.fields}
    return schema.load(raw)


def render_day(
    day: Day, *, message: str | None = None, error: str | None = None, status: int = 200
) -> Response:
    html = render_template("_day.html", day=day, editable=True, message=message, error=error)
    resp = make_response(html, status)
    # Let the map refresh its markers for this day.
    resp.headers["HX-Trigger"] = "itinerary-changed"
    return resp


def first_error(err: ValidationError) -> str:
    messages = err.normalized_messages()
    field, problems = next(iter(messages.items()))
    detail = problems[0] if isinstance(problems, list) else str(problems)
    return f"{field}: {detail}" if field != "_schema" else str(detail)


# --- trips -----------------------------------------------------------------------------------


@bp.get("/")
def index() -> str:
    trips = db.session.scalars(select(Trip).order_by(Trip.start_date, Trip.id)).all()
    return render_template("index.html", trips=trips, errors={}, form={})


@bp.post("/trips")
def create_trip() -> Any:
    try:
        trip = itinerary.create_trip(form_data(TripBaseSchema()))
    except ValidationError as err:
        trips = db.session.scalars(select(Trip).order_by(Trip.start_date)).all()
        return render_template(
            "index.html", trips=trips, errors=err.normalized_messages(), form=request.form
        ), 422
    except DomainError as err:
        db.session.rollback()
        trips = db.session.scalars(select(Trip).order_by(Trip.start_date)).all()
        return render_template(
            "index.html",
            trips=trips,
            errors={err.field or "_schema": [err.message]},
            form=request.form,
        ), 422
    target = url_for("web.trip_detail", trip_id=trip.id)
    if is_htmx():
        return Response(status=204, headers={"HX-Redirect": target})
    return redirect(target, code=303)


@bp.get("/trips/<int:trip_id>")
def trip_detail(trip_id: int) -> str:
    trip = db.get_or_404(Trip, trip_id)
    return render_template("trip.html", trip=trip, editable=True)


@bp.post("/trips/<int:trip_id>/delete")
def delete_trip(trip_id: int) -> Any:
    itinerary.delete_trip(db.get_or_404(Trip, trip_id))
    if is_htmx():
        return Response(status=204, headers={"HX-Redirect": url_for("web.index")})
    return redirect(url_for("web.index"), code=303)


@bp.get("/trips/<int:trip_id>/map.json")
def trip_map(trip_id: int) -> dict[str, Any]:
    trip = db.get_or_404(Trip, trip_id)
    return map_payload(trip)


def map_payload(trip: Trip) -> dict[str, Any]:
    return {
        "days": [
            {
                "number": day.number,
                "label": day.title or day.date.strftime("%a %d %b"),
                "stops": [{"name": s.name, "lat": s.lat, "lon": s.lon} for s in day.stops],
            }
            for day in trip.days
        ]
    }


# --- days & stops ----------------------------------------------------------------------------


@bp.get("/days/<int:day_id>/search")
def search_places(day_id: int) -> str:
    day = db.get_or_404(Day, day_id)
    query = request.args.get("q", "").strip()
    places, error = [], None
    if len(query) >= 2:
        try:
            places = get_geocoder().search(query, limit=6)
        except GeocodingError:
            error = "Place search is unavailable right now. Try again in a moment."
    return render_template("_search_results.html", day=day, places=places, query=query, error=error)


@bp.post("/days/<int:day_id>/stops")
def add_stop(day_id: int) -> Response:
    day = db.get_or_404(Day, day_id)
    try:
        data = form_data(StopCreateSchema())
        position = data.pop("position", None)
        stop = itinerary.add_stop(day, data, position=position)
    except ValidationError as err:
        return render_day(day, error=first_error(err), status=422)
    except DomainError as err:
        db.session.rollback()
        return render_day(day, error=err.message, status=err.status_code)
    return render_day(day, message=f"Added {stop.name}.")


@bp.post("/stops/<int:stop_id>/delete")
def delete_stop(stop_id: int) -> Response:
    stop = db.get_or_404(Stop, stop_id)
    day, name = stop.day, stop.name
    itinerary.delete_stop(stop)
    return render_day(day, message=f"Removed {name}.")


@bp.post("/stops/<int:stop_id>/<any(up, down):direction>")
def nudge_stop(stop_id: int, direction: str) -> Response:
    stop = db.get_or_404(Stop, stop_id)
    target = stop.position + (-1 if direction == "up" else 1)
    if 0 <= target < len(stop.day.stops):
        itinerary.move_stop(stop, stop.day, target)
    return render_day(stop.day)


@bp.post("/days/<int:day_id>/optimize")
def optimize_day(day_id: int) -> Response:
    day = db.get_or_404(Day, day_id)
    if len(day.stops) < 3:
        return render_day(day, message="Add at least three stops to optimise the route.")
    result = itinerary.optimize_day(day, keep_first=True, keep_last="keep_last" in request.form)
    saved = result.plan.saved_km
    if saved < 0.01:
        message = f"Already in a good order ({result.plan.total_km:.1f} km)."
    else:
        message = f"Route reordered: {result.plan.total_km:.1f} km, saving {saved:.1f} km."
    return render_day(day, message=message)


# --- sharing ---------------------------------------------------------------------------------


def render_shares(trip: Trip, *, error: str | None = None, status: int = 200) -> tuple[str, int]:
    return render_template("_shares.html", trip=trip, error=error), status


@bp.post("/trips/<int:trip_id>/shares")
def create_share(trip_id: int) -> tuple[str, int]:
    trip = db.get_or_404(Trip, trip_id)
    try:
        sharing.create_share_link(trip, **form_data(ShareLinkCreateSchema()))
    except ValidationError as err:
        return render_shares(trip, error=first_error(err), status=422)
    except DomainError as err:
        db.session.rollback()
        return render_shares(trip, error=err.message, status=err.status_code)
    return render_shares(trip)


@bp.post("/shares/<int:link_id>/revoke")
def revoke_share(link_id: int) -> tuple[str, int]:
    link = db.get_or_404(ShareLink, link_id)
    sharing.revoke_share_link(link)
    return render_shares(link.trip)


@bp.get("/s/<token>")
def shared_trip(token: str) -> Any:
    trip = sharing.resolve_share_token(token)
    if trip is None:
        abort(404)
    resp = make_response(
        render_template("shared.html", trip=trip, editable=False, map_data=map_payload(trip))
    )
    # Shared pages are capability URLs: keep them out of search engines and referrers.
    resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    resp.headers["Referrer-Policy"] = "no-referrer"
    return resp
