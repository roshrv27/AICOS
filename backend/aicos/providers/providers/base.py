"""Abstract base for all providers.

Every provider extends :class:`Provider` and implements the lifecycle
methods.  Subclasses provide their own configuration, logging, and
mock data generation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import ProviderHealth


class Provider(ABC):
    @abstractmethod
    def initialize(self) -> None:
        """Initialize the provider (load config, open connections, etc.)."""

    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown the provider (close connections, release resources)."""

    @abstractmethod
    def health(self) -> ProviderHealth:
        """Return the current health status of the provider."""

    @abstractmethod
    def capabilities(self) -> list[str]:
        """Return the list of capabilities this provider supports."""
