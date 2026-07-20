"""YouTube provider.

Placeholder implementation that returns mock health data.
No network calls, APIs, or HTTP.
"""

from __future__ import annotations

from datetime import datetime

from ...logging import get_logger
from ..models import ProviderHealth
from .base import Provider


class YouTubeProvider(Provider):
    def __init__(self, config: dict | None = None) -> None:
        self._config = config or {}
        self._logger = get_logger(__name__)

    @property
    def provider_name(self) -> str:
        return "youtube"

    def initialize(self) -> None:
        self._logger.debug("YouTubeProvider initialized")

    def shutdown(self) -> None:
        self._logger.debug("YouTubeProvider shutdown")

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_name="youtube",
            healthy=True,
            last_check=datetime.now(),
            message="youtube provider operational",
        )

    def capabilities(self) -> list[str]:
        return ["video_search", "channel_lookup", "trending"]
