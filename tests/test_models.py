import datetime as dt

from trip_planner.extensions import db
from trip_planner.models import Day, ShareLink, Stop, Trip


def test_cascade_and_ordering(app):
    with app.app_context():
        trip = Trip(title="Barcelona", start_date=dt.date(2026, 5, 1), end_date=dt.date(2026, 5, 3))
        d2 = Day(date=dt.date(2026, 5, 2))
        d1 = Day(date=dt.date(2026, 5, 1))
        trip.days.extend([d2, d1])
        d1.stops.extend(
            [
                Stop(name="B", lat=41.4, lon=2.17, position=1),
                Stop(name="A", lat=41.4, lon=2.17, position=0),
            ]
        )
        db.session.add(trip)
        db.session.commit()
        db.session.expire_all()

        trip = db.session.get(Trip, trip.id)
        assert [d.date.day for d in trip.days] == [1, 2]
        assert [s.name for s in trip.days[0].stops] == ["A", "B"]
        assert trip.days[1].number == 2
        assert trip.length_days == 3
        assert trip.stop_count == 2

        db.session.delete(trip)
        db.session.commit()
        assert db.session.query(Stop).count() == 0


def test_share_link_activity():
    now = dt.datetime(2026, 1, 1, 12)
    link = ShareLink(token="t")
    assert link.is_active(now)
    link.expires_at = now - dt.timedelta(seconds=1)
    assert not link.is_active(now)
    link.expires_at = None
    link.revoked_at = now
    assert not link.is_active(now)


def test_database_level_cascade(app):
    """Deleting with a bulk statement bypasses the ORM, so this relies on SQLite FK enforcement."""
    from sqlalchemy import delete

    with app.app_context():
        trip = Trip(title="x", start_date=dt.date(2026, 1, 1), end_date=dt.date(2026, 1, 1))
        trip.days.append(Day(date=dt.date(2026, 1, 1)))
        db.session.add(trip)
        db.session.commit()
        db.session.execute(delete(Trip))
        db.session.commit()
        assert db.session.query(Day).count() == 0
