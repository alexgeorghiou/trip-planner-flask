"""Extension singletons, initialised inside the app factory."""

from __future__ import annotations

from typing import TYPE_CHECKING

from flask import current_app
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

if TYPE_CHECKING:
    from .geocoding import Geocoder


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


def get_geocoder() -> Geocoder:
    return current_app.extensions["geocoder"]
