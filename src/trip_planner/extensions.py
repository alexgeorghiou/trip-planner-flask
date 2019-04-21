"""Extension singletons, initialised inside the app factory."""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING, Any

from flask import current_app
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase

if TYPE_CHECKING:
    from .geocoding import Geocoder


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


def get_geocoder() -> Geocoder:
    return current_app.extensions["geocoder"]


@event.listens_for(Engine, "connect")
def _sqlite_foreign_keys(dbapi_connection: Any, _record: Any) -> None:
    """SQLite ignores ON DELETE CASCADE unless foreign keys are switched on per connection."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
