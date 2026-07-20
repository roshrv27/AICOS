"""Immutable domain models for the knowledge intelligence domain.

All models are frozen dataclasses.  No AI, retrieval, or infrastructure
types appear in this layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .enums import (
    JobType,
    KnowledgeSourceType,
    ResourceType,
    TechnologyStatus,
)


# ---------------------------------------------------------------------------
# Knowledge Source
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KnowledgeSource:
    id: str
    name: str
    source_type: KnowledgeSourceType
    provider: str = ""
    base_url: str = ""
    credibility_score: float = 0.5
    priority: int = 50
    enabled: bool = True
    last_checked: datetime | None = None


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Evidence:
    id: str
    source: str
    title: str
    url: str = ""
    published_at: datetime | None = None
    author: str = ""
    confidence: float = 0.5


# ---------------------------------------------------------------------------
# Technology Signal
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TechnologySignal:
    id: str
    name: str
    summary: str = ""
    category: str = ""
    first_seen: datetime | None = None
    status: TechnologyStatus = TechnologyStatus.EMERGING
    importance: int = 5
    confidence_score: float = 0.5
    evidence: list[Evidence] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Trend Snapshot
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TrendSnapshot:
    technology: str
    adoption_score: float = 0.0
    community_score: float = 0.0
    industry_score: float = 0.0
    job_market_score: float = 0.0
    github_score: float = 0.0
    youtube_score: float = 0.0
    overall_score: float = 0.0
    captured_at: datetime | None = None


# ---------------------------------------------------------------------------
# Knowledge Resource
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KnowledgeResource:
    id: str
    title: str
    resource_type: ResourceType = ResourceType.ARTICLE
    provider: str = ""
    url: str = ""
    language: str = "en"
    estimated_duration: str = ""
    quality_score: float = 0.5
    difficulty: str = "intermediate"
    last_verified: datetime | None = None
    relevant_tracks: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Resource Collection
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResourceCollection:
    technology: str
    resources: list[KnowledgeResource] = field(default_factory=list)
    last_updated: datetime | None = None


# ---------------------------------------------------------------------------
# Technology Lifecycle Event
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TechnologyLifecycleEvent:
    technology: str
    previous_status: TechnologyStatus | None = None
    new_status: TechnologyStatus = TechnologyStatus.EMERGING
    reason: str = ""
    changed_at: datetime | None = None


# ---------------------------------------------------------------------------
# Knowledge Version
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KnowledgeVersion:
    id: str
    version: str = "0.1.0"
    created_at: datetime | None = None
    changes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Discovery Job
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DiscoveryJob:
    id: str
    job_type: JobType = JobType.TECHNOLOGY_DISCOVERY
    target: str = ""
    schedule: str = ""
    enabled: bool = True
    last_run: datetime | None = None
    next_run: datetime | None = None
