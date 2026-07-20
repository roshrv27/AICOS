"""Official documentation provider.

Placeholder implementation that returns mock health data.
No network calls, APIs, or HTTP.
"""

from __future__ import annotations

from datetime import datetime

from ...logging import get_logger
from ..models import ProviderHealth
from .base import Provider


class OfficialDocsProvider(Provider):
    def __init__(self, config: dict | None = None) -> None:
        self._config = config or {}
        self._logger = get_logger(__name__)

    @property
    def provider_name(self) -> str:
        return "official_docs"

    def initialize(self) -> None:
        self._logger.debug("OfficialDocsProvider initialized")

    def shutdown(self) -> None:
        self._logger.debug("OfficialDocsProvider shutdown")

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_name="official_docs",
            healthy=True,
            last_check=datetime.now(),
            message="official_docs provider operational",
        )

    def capabilities(self) -> list[str]:
        return ["doc_search", "version_lookup", "api_reference"]
