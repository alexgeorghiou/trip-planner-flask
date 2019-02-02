from __future__ import annotations

import pytest

from trip_planner.app import create_app
from trip_planner.extensions import db


@pytest.fixture()
def app():
    app = create_app("testing")
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
