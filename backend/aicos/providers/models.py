"""Immutable models for the provider infrastructure.

These models represent provider-level data, separate from acquisition
or domain models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ProviderConfiguration:
    name: str
    provider_type: str
    config: dict = field(default_factory=dict)
    enabled: bool = True


@dataclass(frozen=True)
class ProviderHealth:
    provider_name: str
    healthy: bool = True
    last_check: datetime | None = None
    message: str = ""
    response_time_ms: float = 0.0


@dataclass(frozen=True)
class SearchRequest:
    query: str
    max_results: int = 10
    filters: dict = field(default_factory=dict)


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str = ""
    snippet: str = ""
    source: str = ""
    published_at: datetime | None = None
    relevance_score: float = 0.0


@dataclass(frozen=True)
class SearchResponse:
    query: str
    results: list[SearchResult] = field(default_factory=list)
    total_estimated: int = 0
    duration_ms: float = 0.0


@dataclass(frozen=True)
class ProviderStatistics:
    total_requests: int = 0
    total_errors: int = 0
    average_response_time_ms: float = 0.0
    last_request: datetime | None = None


@dataclass(frozen=True)
class ProviderSettings:
    timeouts: dict[str, int] = field(default_factory=lambda: {
        "default": 30,
        "search": 15,
        "github": 60,
        "youtube": 30,
        "arxiv": 30,
        "docs": 30,
    })
    retry_count: int = 3
    user_agent: str = "AICOS/0.1.0"
    rate_limits: dict[str, int] = field(default_factory=lambda: {
        "github": 60,
        "youtube": 10000,
        "google": 100,
    })
    enabled_providers: list[str] = field(default_factory=lambda: [
        "mcp_search",
        "duckduckgo_search",
        "github",
        "youtube",
        "research",
        "official_docs",
    ])
    api_endpoints: dict[str, str] = field(default_factory=dict)
    credentials: dict[str, Any] = field(default_factory=dict)
    trust_weights: dict[str, float] = field(default_factory=dict)
