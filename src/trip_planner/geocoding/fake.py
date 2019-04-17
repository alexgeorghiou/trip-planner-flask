"""Deterministic in-memory geocoder for tests, demos and offline development."""

from __future__ import annotations

from collections.abc import Iterable

from .base import Geocoder, Place

DEFAULT_GAZETTEER: tuple[Place, ...] = (
    Place(
        "Sagrada Familia",
        "Basílica de la Sagrada Família, Barcelona, Spain",
        41.4036,
        2.1744,
        "tourism",
        "way",
        13243271,
    ),
    Place(
        "Park Güell",
        "Park Güell, Gràcia, Barcelona, Spain",
        41.4145,
        2.1527,
        "leisure",
        "way",
        23624127,
    ),
    Place(
        "Casa Batlló",
        "Casa Batlló, Passeig de Gràcia, Barcelona, Spain",
        41.3916,
        2.1649,
        "tourism",
        "way",
        23826862,
    ),
    Place(
        "La Boqueria",
        "Mercat de la Boqueria, La Rambla, Barcelona, Spain",
        41.3817,
        2.1716,
        "amenity",
        "way",
        4386470,
    ),
    Place(
        "Barceloneta Beach",
        "Platja de la Barceloneta, Barcelona, Spain",
        41.3784,
        2.1925,
        "natural",
        "way",
        95582614,
    ),
    Place(
        "Montjuïc Castle",
        "Castell de Montjuïc, Barcelona, Spain",
        41.3634,
        2.1658,
        "historic",
        "way",
        26011738,
    ),
    Place("Eiffel Tower", "Tour Eiffel, Paris, France", 48.8584, 2.2945, "tourism", "way", 5013364),
    Place(
        "Louvre Museum",
        "Musée du Louvre, Paris, France",
        48.8606,
        2.3376,
        "tourism",
        "relation",
        7515426,
    ),
    Place(
        "Notre-Dame",
        "Cathédrale Notre-Dame de Paris, Paris, France",
        48.8530,
        2.3499,
        "amenity",
        "way",
        201611261,
    ),
    Place("Montmartre", "Montmartre, Paris, France", 48.8867, 2.3431, "place", "node", 26389651),
    Place("Colosseum", "Colosseo, Rome, Italy", 41.8902, 12.4922, "historic", "way", 27047412),
    Place(
        "Trevi Fountain",
        "Fontana di Trevi, Rome, Italy",
        41.9009,
        12.4833,
        "tourism",
        "way",
        32590911,
    ),
    Place("Pantheon", "Pantheon, Rome, Italy", 41.8986, 12.4769, "historic", "way", 25303424),
    Place(
        "Fushimi Inari",
        "Fushimi Inari Taisha, Kyoto, Japan",
        34.9671,
        135.7727,
        "amenity",
        "way",
        116637245,
    ),
    Place("Kinkaku-ji", "Kinkaku-ji, Kyoto, Japan", 35.0394, 135.7292, "amenity", "way", 90447420),
)


class FakeGeocoder(Geocoder):
    """Case-insensitive substring match over a small gazetteer. Records every query it sees."""

    def __init__(self, places: Iterable[Place] = DEFAULT_GAZETTEER) -> None:
        self.places = list(places)
        self.queries: list[str] = []

    def search(
        self, query: str, *, limit: int = 5, country_codes: list[str] | None = None
    ) -> list[Place]:
        self.queries.append(query)
        needle = query.strip().casefold()
        if not needle:
            return []
        hits = [
            p
            for p in self.places
            if needle in p.name.casefold() or needle in p.display_name.casefold()
        ]
        # Name matches rank above matches that only hit the longer display name.
        hits.sort(key=lambda p: (needle not in p.name.casefold(), p.name))
        return hits[:limit]
