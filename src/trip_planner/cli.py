"""Flask CLI commands: ``flask --app trip_planner.wsgi <command>``."""

from __future__ import annotations

import datetime as dt

import click
from flask import Flask

from .extensions import db
from .geocoding.fake import DEFAULT_GAZETTEER
from .services import itinerary, sharing

DEMO_DAYS: list[tuple[str, list[str]]] = [
    ("Gaudí day", ["Sagrada Familia", "Casa Batlló", "Park Güell"]),
    ("Old town and the sea", ["Montjuïc Castle", "Barceloneta Beach", "La Boqueria"]),
]


def register_cli(app: Flask) -> None:
    @app.cli.command("init-db")
    def init_db() -> None:
        """Create database tables."""
        db.create_all()
        click.echo("Database initialised.")

    @app.cli.command("seed-demo")
    @click.option(
        "--start",
        type=click.DateTime(["%Y-%m-%d"]),
        default=None,
        help="First day of the demo trip (defaults to two weeks from today).",
    )
    def seed_demo(start: dt.datetime | None) -> None:
        """Create a sample Barcelona trip with stops and a share link."""
        first = start.date() if start else dt.date.today() + dt.timedelta(days=14)
        places = {p.name: p for p in DEFAULT_GAZETTEER}
        trip = itinerary.create_trip(
            {
                "title": "Barcelona long weekend",
                "destination": "Barcelona, Spain",
                "start_date": first,
                "end_date": first + dt.timedelta(days=len(DEMO_DAYS)),
                "notes": "Book Sagrada Familia tickets in advance.",
            }
        )
        for day, (title, names) in zip(trip.days, DEMO_DAYS, strict=False):
            itinerary.update_day(day, {"title": title})
            for name in names:
                p = places[name]
                itinerary.add_stop(
                    day,
                    {
                        "name": p.name,
                        "address": p.display_name,
                        "lat": p.lat,
                        "lon": p.lon,
                        "category": p.category,
                        "osm_ref": p.osm_ref,
                    },
                )
        link = sharing.create_share_link(trip, label="demo")
        click.echo(f"Created trip {trip.id} ({trip.title}); share token: {link.token}")
