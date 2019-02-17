"""Application factory."""

from __future__ import annotations

import os
from typing import Any

from flask import Flask

from .config import CONFIGS
from . import models  # noqa: F401  (register tables)
from .extensions import api, db


def create_app(config_name: str | None = None, overrides: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    name = config_name or os.environ.get("FLASK_CONFIG", "development")
    app.config.from_object(CONFIGS[name])
    if overrides:
        app.config.update(overrides)

    db.init_app(app)
    api.init_app(app)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    with app.app_context():
        db.create_all()

    return app
