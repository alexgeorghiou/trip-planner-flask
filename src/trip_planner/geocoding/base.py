"""Geocoder abstraction shared by the real Nominatim client and the offline fake."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class GeocodingError(RuntimeError):
    """The upstream geocoding service failed or returned something unusable."""


@dataclass(frozen=True, slots=True)
class Place:
    """A search hit: something a traveller can add to a day as a stop."""

    name: str
    display_name: str
    lat: float
    lon: float
    category: str | None = None
    osm_type: str | None = None
    osm_id: int | None = None
    extra: dict[str, str] = field(default_factory=dict)

    @property
    def osm_ref(self) -> str | None:
        if self.osm_type and self.osm_id is not None:
            return f"{self.osm_type[0].upper()}{self.osm_id}"
        return None


class Geocoder(ABC):
    @abstractmethod
    def search(self, query: str, *, limit: int = 5, country_codes: list[str] | None = None) -> list[Place]:
        """Forward geocode free text into candidate places, best match first."""

    def close(self) -> None:  # noqa: B027 - optional hook for clients that hold connections
        """Release any underlying resources."""
