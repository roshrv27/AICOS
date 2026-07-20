"""Normalization service for the knowledge acquisition engine.

Converts adapter-specific data into validated Knowledge Intelligence
Domain models.  Only normalization — no business decisions, no AI.
"""

from __future__ import annotations

from ..knowledge_intelligence.interfaces import (
    KnowledgeIntelligenceDomainServiceProtocol,
)
from ..logging import get_logger
from .exceptions import NormalizationError
from .models import DiscoveryResult


class NormalizationService:
    def __init__(
        self,
        domain_service: KnowledgeIntelligenceDomainServiceProtocol,
    ) -> None:
        self._domain_service = domain_service
        self._logger = get_logger(__name__)

    def normalize(self, result: DiscoveryResult) -> DiscoveryResult:
        source_count = len(result.sources)
        signal_count = len(result.signals)
        resource_count = len(result.resources)
        event_count = len(result.events)
        trend_count = len(result.trends)

        self._logger.debug(
            "normalizing discovery result: %d sources, %d signals, "
            "%d resources, %d events, %d trends",
            source_count,
            signal_count,
            resource_count,
            event_count,
            trend_count,
        )

        try:
            if result.sources:
                self._domain_service.validate_sources(result.sources)
            if result.signals:
                self._domain_service.validate_signals(result.signals)
            if result.resources:
                self._domain_service.validate_resources(result.resources)
            if result.trends:
                self._domain_service.validate_trends(result.trends)
        except Exception as exc:
            self._logger.warning(
                "normalization failed: %s",
                exc,
            )
            raise NormalizationError(str(exc)) from exc

        self._logger.info(
            "normalization complete: %d sources, %d signals, "
            "%d resources, %d events, %d trends",
            source_count,
            signal_count,
            resource_count,
            event_count,
            trend_count,
        )
        return result
