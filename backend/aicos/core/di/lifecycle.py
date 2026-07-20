"""Service lifecycle definitions."""

from enum import StrEnum


class ServiceLifetime(StrEnum):
    """Supported and reserved service lifecycles.

    ``SCOPED`` is intentionally reserved as an extension point; this initial
    in-process container supports only singleton and transient services.
    """

    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"
