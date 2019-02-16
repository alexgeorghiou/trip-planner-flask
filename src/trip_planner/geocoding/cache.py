"""LRU caching decorator around any geocoder (Nominatim asks clients to cache)."""

from __future__ import annotations

import threading
from collections import OrderedDict

from .base import Geocoder, Place

CacheKey = tuple[str, int, tuple[str, ...]]


class CachingGeocoder(Geocoder):
    def __init__(self, inner: Geocoder, maxsize: int = 256) -> None:
        self.inner = inner
        self.maxsize = maxsize
        self._cache: OrderedDict[CacheKey, list[Place]] = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def search(self, query: str, *, limit: int = 5, country_codes: list[str] | None = None) -> list[Place]:
        key: CacheKey = (
            " ".join(query.casefold().split()),
            limit,
            tuple(sorted(c.lower() for c in country_codes or [])),
        )
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self.hits += 1
                return list(self._cache[key])
        result = self.inner.search(query, limit=limit, country_codes=country_codes)
        with self._lock:
            self.misses += 1
            self._cache[key] = list(result)
            while len(self._cache) > self.maxsize:
                self._cache.popitem(last=False)
        return result

    def close(self) -> None:
        self.inner.close()
