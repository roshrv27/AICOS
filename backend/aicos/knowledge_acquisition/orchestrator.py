"""Discovery orchestrator for the knowledge acquisition engine.

Coordinates adapters, invokes discovery, and normalizes results.
No persistence, no ranking, no AI.
"""

from __future__ import annotations

import time

from ..knowledge_intelligence.enums import KnowledgeSourceType
from ..logging import get_logger
from .exceptions import AdapterExecutionError, DiscoveryError
from .interfaces import (
    KnowledgeAdapterProtocol,
    NormalizationServiceProtocol,
)
from .models import AdapterHealth, DiscoveryRequest, DiscoveryResult
from .registry import AdapterRegistry


class DiscoveryOrchestrator:
    def __init__(
        self,
        registry: AdapterRegistry,
        normalizer: NormalizationServiceProtocol,
    ) -> None:
        self._registry = registry
        self._normalizer = normalizer
        self._logger = get_logger(__name__)

    def discover(self, request: DiscoveryRequest) -> DiscoveryResult:
        adapter = self._registry.discover(request.source_type)
        self._logger.info(
            "discovery via %s for %s",
            adapter.name,
            request.target,
        )
        start = time.perf_counter()
        try:
            raw = adapter.discover(request)
        except Exception as exc:
            self._logger.warning(
                "adapter %s discovery failed: %s",
                adapter.name,
                exc,
            )
            raise AdapterExecutionError(
                f"{adapter.name} discovery failed: {exc}"
            ) from exc

        elapsed = (time.perf_counter() - start) * 1000
        result = DiscoveryResult(
            source_type=request.source_type,
            sources=raw.sources,
            signals=raw.signals,
            resources=raw.resources,
            events=raw.events,
            trends=raw.trends,
            errors=raw.errors,
            duration_ms=elapsed,
        )
        return self._normalizer.normalize(result)

    def refresh(self, request: DiscoveryRequest) -> DiscoveryResult:
        adapter = self._registry.discover(request.source_type)
        self._logger.info(
            "refresh via %s for %s",
            adapter.name,
            request.target,
        )
        start = time.perf_counter()
        try:
            raw = adapter.refresh(request)
        except Exception as exc:
            self._logger.warning(
                "adapter %s refresh failed: %s",
                adapter.name,
                exc,
            )
            raise AdapterExecutionError(
                f"{adapter.name} refresh failed: {exc}"
            ) from exc

        elapsed = (time.perf_counter() - start) * 1000
        result = DiscoveryResult(
            source_type=request.source_type,
            sources=raw.sources,
            signals=raw.signals,
            resources=raw.resources,
            events=raw.events,
            trends=raw.trends,
            errors=raw.errors,
            duration_ms=elapsed,
        )
        return self._normalizer.normalize(result)

    def verify_source(self, source_type: KnowledgeSourceType) -> AdapterHealth:
        adapter = self._registry.discover(source_type)
        self._logger.info("verifying adapter %s", adapter.name)
        try:
            return adapter.verify()
        except Exception as exc:
            self._logger.warning(
                "adapter %s verify failed: %s",
                adapter.name,
                exc,
            )
            raise AdapterExecutionError(
                f"{adapter.name} verify failed: {exc}"
            ) from exc

    def verify_all(self) -> list[AdapterHealth]:
        results: list[AdapterHealth] = []
        for adapter in self._registry.registered_adapters:
            try:
                results.append(adapter.verify())
            except Exception as exc:
                self._logger.warning(
                    "adapter %s verify failed: %s",
                    adapter.name,
                    exc,
                )
                results.append(
                    AdapterHealth(
                        adapter_name=adapter.name,
                        healthy=False,
                        message=str(exc),
                    )
                )
        return results
