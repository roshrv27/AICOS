"""Abstract base for knowledge adapters.

Every adapter extends :class:`KnowledgeAdapter` and implements the five
methods required by the adapter contract.  Subclasses provide their own
configuration, logging, and mock data generation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ...knowledge_intelligence.enums import KnowledgeSourceType
from ..models import AdapterHealth, DiscoveryRequest, DiscoveryResult


class KnowledgeAdapter(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique adapter name."""

    @abstractmethod
    def supported_source(self) -> KnowledgeSourceType:
        """The knowledge source type this adapter handles."""

    @abstractmethod
    def discover(self, request: DiscoveryRequest) -> DiscoveryResult:
        """Discover new knowledge matching the request."""

    @abstractmethod
    def refresh(self, request: DiscoveryRequest) -> DiscoveryResult:
        """Refresh previously discovered knowledge."""

    @abstractmethod
    def verify(self) -> AdapterHealth:
        """Verify the adapter is operational."""
