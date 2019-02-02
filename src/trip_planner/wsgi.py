"""WSGI entrypoint: ``gunicorn trip_planner.wsgi:app``."""

from .app import create_app

app = create_app(None)
