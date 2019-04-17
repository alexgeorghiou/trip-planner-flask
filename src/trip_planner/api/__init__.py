"""JSON API blueprints (flask-smorest), documented at /api/docs."""

from __future__ import annotations

from typing import Any

from apispec.ext.marshmallow import MarshmallowPlugin
from apispec.ext.marshmallow.common import resolve_schema_cls
from flask import Flask
from flask_smorest import Api

from .places import blp as places_blp
from .shares import blp as shares_blp
from .stops import blp as stops_blp
from .trips import blp as trips_blp


def schema_name_resolver(schema: Any) -> str:
    """Give partial / excluded variants their own component names instead of warnings."""
    cls = resolve_schema_cls(schema)
    name = cls.__name__.removesuffix("Schema")
    if isinstance(schema, type):
        return name
    if schema.partial:
        name += "Patch"
    if schema.exclude:
        name += "Without" + "".join(f.title() for f in sorted(schema.exclude))
    return name


def create_api(app: Flask) -> Api:
    api = Api(
        app,
        spec_kwargs={
            "marshmallow_plugin": MarshmallowPlugin(schema_name_resolver=schema_name_resolver)
        },
    )
    for blp in (trips_blp, stops_blp, places_blp, shares_blp):
        api.register_blueprint(blp, url_prefix="/api")
    return api
