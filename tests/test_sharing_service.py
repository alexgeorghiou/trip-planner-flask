import datetime as dt

import pytest

from trip_planner.errors import DomainError
from trip_planner.extensions import db
from trip_planner.services import sharing

from .factories import make_trip


@pytest.fixture()
def ctx(app):
    with app.app_context():
        yield


def test_tokens_are_unique_and_resolve(ctx):
    trip = make_trip()
    a = sharing.create_share_link(trip, label="family")
    b = sharing.create_share_link(trip)
    assert a.token != b.token and len(a.token) >= 32
    assert sharing.resolve_share_token(a.token) is trip


def test_revoked_and_expired_tokens_do_not_resolve(ctx):
    trip = make_trip()
    link = sharing.create_share_link(trip, expires_in_days=1)
    sharing.revoke_share_link(link)
    assert sharing.resolve_share_token(link.token) is None

    expired = sharing.create_share_link(trip, expires_in_days=1)
    expired.expires_at = dt.datetime(2000, 1, 1)
    db.session.commit()
    assert sharing.resolve_share_token(expired.token) is None


@pytest.mark.parametrize("token", ["", "nope", "x" * 200])
def test_garbage_tokens(ctx, token):
    make_trip()
    assert sharing.resolve_share_token(token) is None


def test_active_link_limit(ctx, monkeypatch):
    monkeypatch.setattr(sharing, "MAX_ACTIVE_LINKS", 2)
    trip = make_trip()
    first = sharing.create_share_link(trip)
    sharing.create_share_link(trip)
    with pytest.raises(DomainError):
        sharing.create_share_link(trip)
    sharing.revoke_share_link(first)
    sharing.create_share_link(trip)  # slot freed


def test_rejects_non_positive_expiry(ctx):
    with pytest.raises(DomainError):
        sharing.create_share_link(make_trip(), expires_in_days=0)
