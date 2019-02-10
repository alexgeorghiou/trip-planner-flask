"""Place search behind a small interface so the HTTP provider can be swapped or faked."""

from .base import Geocoder, GeocodingError, Place
from .fake import FakeGeocoder

__all__ = ["FakeGeocoder", "Geocoder", "GeocodingError", "Place"]
