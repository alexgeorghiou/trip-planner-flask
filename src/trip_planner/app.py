"""Application factory."""

from __future__ import annotations

import os
from typing import Any

from flask import Flask, jsonify
from werkzeug.wrappers import Response

from . import models  # noqa: F401  (register tables)
from .api import create_api
from .config import CONFIGS
from .errors import DomainError
from .extensions import db
from .geocoding import Geocoder, build_geocoder


def create_app(
    config_name: str | None = None,
    overrides: dict[str, Any] | None = None,
    *,
    geocoder: Geocoder | None = None,
) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    name = config_name or os.environ.get("FLASK_CONFIG", "development")
    app.config.from_object(CONFIGS[name])
    if overrides:
        app.config.update(overrides)

    db.init_app(app)
    app.extensions["smorest_api"] = create_api(app)
    app.extensions["geocoder"] = geocoder or build_geocoder(app.config)

    register_error_handlers(app)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    with app.app_context():
        db.create_all()

    return app


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(DomainError)
    def handle_domain_error(exc: DomainError) -> tuple[Response, int]:
        db.session.rollback()
        body: dict[str, Any] = {
            "code": exc.status_code,
            "status": "Conflict" if exc.status_code == 409 else "Unprocessable Entity",
            "message": exc.message,
        }
        if exc.field:
            body["errors"] = {"json": {exc.field: [exc.message]}}
        return jsonify(body), exc.status_code
