from trip_planner.extensions import db
from trip_planner.models import ShareLink, Trip


def test_seed_demo_creates_a_shareable_trip(app):
    result = app.test_cli_runner().invoke(args=["seed-demo", "--start", "2026-09-01"])
    assert result.exit_code == 0, result.output
    assert "share token" in result.output
    with app.app_context():
        trip = db.session.query(Trip).one()
        assert trip.length_days == 3
        assert [len(d.stops) for d in trip.days] == [3, 3, 0]
        assert trip.days[0].title == "Gaudí day"
        assert db.session.query(ShareLink).count() == 1


def test_init_db(app):
    result = app.test_cli_runner().invoke(args=["init-db"])
    assert result.exit_code == 0
    assert "initialised" in result.output
