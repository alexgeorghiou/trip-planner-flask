"""Place search behind a small interface so the HTTP provider can be swapped or faked."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .base import Geocoder, GeocodingError, Place
from .cache import CachingGeocoder
from .fake import FakeGeocoder
from .nominatim import NominatimGeocoder

__all__ = [
    "CachingGeocoder",
    "FakeGeocoder",
    "Geocoder",
    "GeocodingError",
    "NominatimGeocoder",
    "Place",
    "build_geocoder",
]


def build_geocoder(config: Mapping[str, Any]) -> Geocoder:
    """Construct the geocoder named by ``config["GEOCODER"]``."""
    kind = str(config.get("GEOCODER", "nominatim")).lower()
    if kind == "fake":
        return FakeGeocoder()
    if kind == "nominatim":
        client = NominatimGeocoder(
            user_agent=config["NOMINATIM_USER_AGENT"],
            base_url=config.get("NOMINATIM_URL", "https://nominatim.openstreetmap.org"),
            email=config.get("NOMINATIM_EMAIL"),
            timeout=float(config.get("NOMINATIM_TIMEOUT", 5.0)),
        )
        return CachingGeocoder(client, maxsize=int(config.get("GEOCODER_CACHE_SIZE", 256)))
    raise ValueError(f"unknown GEOCODER {kind!r}; expected 'nominatim' or 'fake'")
