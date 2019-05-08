"""Configuration objects selected by the app factory."""

from __future__ import annotations

import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///trip_planner.sqlite3")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Convenient for local runs; containers create tables once via `flask init-db` instead,
    # so several gunicorn workers don't race each other on startup.
    AUTO_CREATE_TABLES = os.environ.get("AUTO_CREATE_TABLES", "1") == "1"

    # flask-smorest / OpenAPI
    API_TITLE = "Trip Planner API"
    API_VERSION = "v1"
    OPENAPI_VERSION = "3.0.3"
    OPENAPI_URL_PREFIX = "/api"
    OPENAPI_JSON_PATH = "openapi.json"
    OPENAPI_SWAGGER_UI_PATH = "/docs"
    OPENAPI_SWAGGER_UI_URL = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/"

    # Geocoding: "nominatim" for the real HTTP client, "fake" for an offline in-memory gazetteer.
    GEOCODER = os.environ.get("GEOCODER", "nominatim")
    NOMINATIM_URL = os.environ.get("NOMINATIM_URL", "https://nominatim.openstreetmap.org")
    # Nominatim's usage policy requires an identifying User-Agent with a contact address.
    NOMINATIM_USER_AGENT = os.environ.get(
        "NOMINATIM_USER_AGENT", "trip-planner-flask/0.1 (self-hosted)"
    )
    NOMINATIM_EMAIL = os.environ.get("NOMINATIM_EMAIL")
    NOMINATIM_TIMEOUT = float(os.environ.get("NOMINATIM_TIMEOUT", "5"))
    GEOCODER_CACHE_SIZE = int(os.environ.get("GEOCODER_CACHE_SIZE", "256"))


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    GEOCODER = "fake"
    SECRET_KEY = "test"


class ProductionConfig(Config):
    pass


CONFIGS: dict[str, type[Config]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
