"""Share links: unguessable tokens granting read-only access to a single trip."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select

from ..errors import DomainError
from ..extensions import db
from ..models import ShareLink, Trip, utcnow

MAX_ACTIVE_LINKS = 10


def create_share_link(
    trip: Trip, *, label: str | None = None, expires_in_days: int | None = None
) -> ShareLink:
    active = [link for link in trip.share_links if link.is_active()]
    if len(active) >= MAX_ACTIVE_LINKS:
        raise DomainError(f"a trip can have at most {MAX_ACTIVE_LINKS} active share links")
    if expires_in_days is not None and expires_in_days < 1:
        raise DomainError("expires_in_days must be at least 1", field="expires_in_days")
    link = ShareLink(
        label=label,
        expires_at=utcnow() + dt.timedelta(days=expires_in_days) if expires_in_days else None,
    )
    trip.share_links.append(link)
    db.session.commit()
    return link


def revoke_share_link(link: ShareLink) -> ShareLink:
    if link.revoked_at is None:
        link.revoked_at = utcnow()
        db.session.commit()
    return link


def resolve_share_token(token: str) -> Trip | None:
    """Return the shared trip, or ``None`` for unknown, revoked or expired tokens."""
    if not token or len(token) > 64:
        return None
    link = db.session.scalar(select(ShareLink).where(ShareLink.token == token))
    if link is None or not link.is_active():
        return None
    return link.trip
