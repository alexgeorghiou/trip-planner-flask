from __future__ import annotations

import socket

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


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Fail loudly if anything tries to reach the internet (e.g. real Nominatim)."""

    def guard(*args, **kwargs):
        raise RuntimeError("network access is disabled in tests")

    monkeypatch.setattr(socket.socket, "connect", guard)
    monkeypatch.setattr(socket, "create_connection", guard)
