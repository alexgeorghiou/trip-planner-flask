"""Domain exceptions, translated to HTTP responses at the edges (API / web)."""


class DomainError(Exception):
    """A request that is well-formed but violates an itinerary rule."""

    status_code = 422

    def __init__(self, message: str, *, field: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.field = field


class ConflictError(DomainError):
    status_code = 409
