"""Persistence model: Trip 1-* Day 1-* Stop, plus share links for read-only access."""

from __future__ import annotations

import datetime as dt
import secrets

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .extensions import db


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC).replace(tzinfo=None)


class Trip(db.Model):
    __tablename__ = "trips"
    __table_args__ = (CheckConstraint("end_date >= start_date", name="ck_trip_dates"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    destination: Mapped[str | None] = mapped_column(String(200))
    start_date: Mapped[dt.date]
    end_date: Mapped[dt.date]
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    days: Mapped[list[Day]] = relationship(
        back_populates="trip", cascade="all, delete-orphan", order_by="Day.date"
    )
    share_links: Mapped[list[ShareLink]] = relationship(
        back_populates="trip", cascade="all, delete-orphan", order_by="ShareLink.created_at"
    )

    @property
    def length_days(self) -> int:
        return (self.end_date - self.start_date).days + 1

    @property
    def stop_count(self) -> int:
        return sum(len(d.stops) for d in self.days)

    def __repr__(self) -> str:
        return f"<Trip {self.id} {self.title!r}>"


class Day(db.Model):
    __tablename__ = "days"
    __table_args__ = (UniqueConstraint("trip_id", "date", name="uq_day_trip_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"), index=True)
    date: Mapped[dt.date]
    title: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)

    trip: Mapped[Trip] = relationship(back_populates="days")
    stops: Mapped[list[Stop]] = relationship(
        back_populates="day", cascade="all, delete-orphan", order_by="Stop.position"
    )

    @property
    def number(self) -> int:
        """1-based day number within the trip."""
        return (self.date - self.trip.start_date).days + 1

    def __repr__(self) -> str:
        return f"<Day {self.date.isoformat()} trip={self.trip_id}>"


class Stop(db.Model):
    __tablename__ = "stops"
    __table_args__ = (
        CheckConstraint("lat BETWEEN -90 AND 90", name="ck_stop_lat"),
        CheckConstraint("lon BETWEEN -180 AND 180", name="ck_stop_lon"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    day_id: Mapped[int] = mapped_column(ForeignKey("days.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(default=0)
    name: Mapped[str] = mapped_column(String(200))
    address: Mapped[str | None] = mapped_column(String(500))
    lat: Mapped[float]
    lon: Mapped[float]
    category: Mapped[str | None] = mapped_column(String(64))
    osm_ref: Mapped[str | None] = mapped_column(String(32))
    arrival_time: Mapped[dt.time | None]
    duration_minutes: Mapped[int | None]
    notes: Mapped[str | None] = mapped_column(Text)

    day: Mapped[Day] = relationship(back_populates="stops")

    def __repr__(self) -> str:
        return f"<Stop {self.position}:{self.name!r}>"


def new_share_token() -> str:
    return secrets.token_urlsafe(24)


class ShareLink(db.Model):
    __tablename__ = "share_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"), index=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, default=new_share_token)
    label: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[dt.datetime] = mapped_column(default=utcnow)
    expires_at: Mapped[dt.datetime | None]
    revoked_at: Mapped[dt.datetime | None]

    trip: Mapped[Trip] = relationship(back_populates="share_links")

    def is_active(self, now: dt.datetime | None = None) -> bool:
        now = now or utcnow()
        if self.revoked_at is not None:
            return False
        return self.expires_at is None or self.expires_at > now
