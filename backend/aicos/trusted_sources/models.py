from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .enums import (
    AuthenticationType,
    Capability,
    Category,
    RefreshFrequency,
    SourceType,
)


@dataclass(frozen=True)
class TrustedKnowledgeSource:
    id: str
    name: str
    source_type: SourceType
    category: Category
    url: str = ""
    display_name: str = ""
    organization: str = ""
    rss_feed: str = ""
    api_endpoint: str = ""
    trust_score: float = 0.5
    priority: int = 50
    enabled: bool = True
    authentication_type: AuthenticationType = AuthenticationType.NONE
    refresh_frequency: RefreshFrequency = RefreshFrequency.DAILY
    capabilities: frozenset[Capability] = field(default_factory=lambda: frozenset())
    tags: frozenset[str] = field(default_factory=lambda: frozenset())
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.trust_score <= 1.0:
            raise ValueError(
                f"trust_score must be between 0.0 and 1.0, got {self.trust_score}"
            )


@dataclass(frozen=True)
class TrustedSourceGroup:
    id: str
    name: str
    description: str = ""
    source_ids: frozenset[str] = field(default_factory=lambda: frozenset())


@dataclass(frozen=True)
class CapabilityMapping:
    source_type: SourceType
    capability: Capability
    description: str = ""
    confidence: float = 1.0


@dataclass(frozen=True)
class DiscoveryPolicy:
    id: str
    name: str
    description: str = ""
    source_type_filter: frozenset[SourceType] = field(default_factory=lambda: frozenset())
    category_filter: frozenset[Category] = field(default_factory=lambda: frozenset())
    capability_filter: frozenset[Capability] = field(default_factory=lambda: frozenset())
    max_results: int = 10
    enabled: bool = True


@dataclass(frozen=True)
class KnowledgeCatalog:
    id: str
    name: str
    description: str = ""
    sources: frozenset[str] = field(default_factory=lambda: frozenset())
    groups: frozenset[str] = field(default_factory=lambda: frozenset())
    policies: frozenset[str] = field(default_factory=lambda: frozenset())
    created_at: datetime | None = None
    updated_at: datetime | None = None
