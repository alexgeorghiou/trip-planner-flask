"""OpenStreetMap Nominatim client.

Nominatim's public instance has a strict usage policy: identify the application with a
meaningful User-Agent, make at most one request per second and cache results. This client
does all three; point ``base_url`` at a self-hosted instance for heavier use.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

import httpx

from .base import Geocoder, GeocodingError, Place


class NominatimGeocoder(Geocoder):
    def __init__(
        self,
        *,
        user_agent: str,
        base_url: str = "https://nominatim.openstreetmap.org",
        email: str | None = None,
        timeout: float = 5.0,
        min_interval: float = 1.0,
        accept_language: str = "en",
        transport: httpx.BaseTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not user_agent or user_agent.lower().startswith(("python-httpx", "python-requests")):
            raise ValueError("Nominatim requires an application-specific User-Agent")
        self.email = email
        self.min_interval = min_interval
        self._clock = clock
        self._sleep = sleep
        self._lock = threading.Lock()
        self._last_request: float | None = None
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            transport=transport,
            headers={"User-Agent": user_agent, "Accept-Language": accept_language},
        )

    def _throttle(self) -> None:
        with self._lock:
            now = self._clock()
            if self._last_request is not None:
                wait = self.min_interval - (now - self._last_request)
                if wait > 0:
                    self._sleep(wait)
                    now += wait
            self._last_request = now

    def search(
        self, query: str, *, limit: int = 5, country_codes: list[str] | None = None
    ) -> list[Place]:
        query = query.strip()
        if not query:
            return []
        params: dict[str, Any] = {
            "q": query,
            "format": "jsonv2",
            "limit": max(1, min(limit, 40)),
            "addressdetails": 0,
        }
        if country_codes:
            params["countrycodes"] = ",".join(c.lower() for c in country_codes)
        if self.email:
            params["email"] = self.email

        self._throttle()
        try:
            resp = self._client.get("/search", params=params)
            resp.raise_for_status()
            payload = resp.json()
        except httpx.HTTPStatusError as exc:
            raise GeocodingError(f"Nominatim returned HTTP {exc.response.status_code}") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise GeocodingError(f"Nominatim request failed: {exc}") from exc

        if not isinstance(payload, list):
            raise GeocodingError("unexpected Nominatim response shape")
        return [p for p in (self._parse(item) for item in payload) if p is not None]

    @staticmethod
    def _parse(item: dict[str, Any]) -> Place | None:
        try:
            lat = float(item["lat"])
            lon = float(item["lon"])
        except (KeyError, TypeError, ValueError):
            return None
        display = str(item.get("display_name", "")).strip()
        name = str(item.get("name") or display.split(",")[0]).strip() or display
        osm_id = item.get("osm_id")
        return Place(
            name=name,
            display_name=display or name,
            lat=lat,
            lon=lon,
            category=item.get("category") or item.get("class"),
            osm_type=item.get("osm_type"),
            osm_id=int(osm_id) if osm_id is not None else None,
            extra={k: str(item[k]) for k in ("type", "place_rank") if k in item},
        )

    def close(self) -> None:
        self._client.close()
