"""Research provider.

Placeholder implementation that returns mock health data.
No network calls, APIs, or HTTP.
"""

from __future__ import annotations

from datetime import datetime

from ...logging import get_logger
from ..models import ProviderHealth
from .base import Provider


class ResearchProvider(Provider):
    def __init__(self, config: dict | None = None) -> None:
        self._config = config or {}
        self._logger = get_logger(__name__)

    @property
    def provider_name(self) -> str:
        return "research"

    def initialize(self) -> None:
        self._logger.debug("ResearchProvider initialized")

    def shutdown(self) -> None:
        self._logger.debug("ResearchProvider shutdown")

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_name="research",
            healthy=True,
            last_check=datetime.now(),
            message="research provider operational",
        )

    def capabilities(self) -> list[str]:
        return ["paper_search", "citation_lookup", "author_search"]
