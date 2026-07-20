"""Lightweight acquisition models for the knowledge acquisition engine.

These models represent the acquisition layer's own data, separate from
the knowledge intelligence domain models they produce.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ..knowledge_intelligence.enums import KnowledgeSourceType
from ..knowledge_intelligence.models import (
    Evidence,
    KnowledgeResource,
    KnowledgeSource,
    TechnologyLifecycleEvent,
    TechnologySignal,
    TrendSnapshot,
)


@dataclass(frozen=True)
class DiscoveryRequest:
    source_type: KnowledgeSourceType
    target: str = ""
    max_results: int = 10
    config: dict = field(default_factory=dict)


@dataclass(frozen=True)
class DiscoveryResult:
    source_type: KnowledgeSourceType
    sources: list[KnowledgeSource] = field(default_factory=list)
    signals: list[TechnologySignal] = field(default_factory=list)
    resources: list[KnowledgeResource] = field(default_factory=list)
    events: list[TechnologyLifecycleEvent] = field(default_factory=list)
    trends: list[TrendSnapshot] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0.0


@dataclass(frozen=True)
class AdapterHealth:
    adapter_name: str
    healthy: bool = True
    last_check: datetime | None = None
    message: str = ""
    response_time_ms: float = 0.0


@dataclass(frozen=True)
class AcquisitionStatistics:
    total_discoveries: int = 0
    total_refreshes: int = 0
    total_errors: int = 0
    total_sources_found: int = 0
    total_signals_found: int = 0
    total_resources_found: int = 0
    last_acquisition: datetime | None = None
    adapter_stats: dict[str, dict] = field(default_factory=dict)
