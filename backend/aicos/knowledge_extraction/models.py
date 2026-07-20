from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..knowledge_intelligence.enums import KnowledgeSourceType, ResourceType, TechnologyStatus
from ..knowledge_intelligence.models import (
    Evidence,
    KnowledgeResource,
    KnowledgeSource,
    KnowledgeVersion,
    TechnologySignal,
)
from ..knowledge_acquisition.models import DiscoveryResult
from .enums import ContentType, ExtractionMode


@dataclass(frozen=True)
class ExtractedTechnology:
    id: str
    name: str
    summary: str = ""
    category: str = ""
    first_seen: datetime | None = None
    status: TechnologyStatus = TechnologyStatus.EMERGING
    importance: int = 5
    confidence_score: float = 0.5
    source_references: list[str] = field(default_factory=list)

    def to_signal(self, evidence_map: dict[str, Evidence]) -> TechnologySignal:
        return TechnologySignal(
            id=self.id,
            name=self.name,
            summary=self.summary,
            category=self.category,
            first_seen=self.first_seen,
            status=self.status,
            importance=self.importance,
            confidence_score=self.confidence_score,
            evidence=[evidence_map[ref] for ref in self.source_references if ref in evidence_map],
        )


@dataclass(frozen=True)
class ExtractedFramework:
    id: str
    name: str
    description: str = ""
    version: str = ""
    language: str = ""
    url: str = ""
    confidence_score: float = 0.5

    def to_resource(self) -> KnowledgeResource:
        return KnowledgeResource(
            id=self.id,
            title=self.name,
            resource_type=ResourceType.DOCUMENTATION,
            url=self.url,
            quality_score=self.confidence_score,
        )


@dataclass(frozen=True)
class ExtractedModel:
    id: str
    name: str
    description: str = ""
    provider: str = ""
    version: str = ""
    url: str = ""
    confidence_score: float = 0.5

    def to_resource(self) -> KnowledgeResource:
        return KnowledgeResource(
            id=self.id,
            title=self.name,
            resource_type=ResourceType.ARTICLE,
            url=self.url,
            quality_score=self.confidence_score,
        )


@dataclass(frozen=True)
class ExtractedTool:
    id: str
    name: str
    description: str = ""
    category: str = ""
    url: str = ""
    confidence_score: float = 0.5

    def to_resource(self) -> KnowledgeResource:
        return KnowledgeResource(
            id=self.id,
            title=self.name,
            resource_type=ResourceType.ARTICLE,
            url=self.url,
            quality_score=self.confidence_score,
        )


@dataclass(frozen=True)
class ExtractedAPI:
    id: str
    name: str
    description: str = ""
    endpoint: str = ""
    version: str = ""
    url: str = ""
    confidence_score: float = 0.5

    def to_resource(self) -> KnowledgeResource:
        return KnowledgeResource(
            id=self.id,
            title=self.name,
            resource_type=ResourceType.DOCUMENTATION,
            url=self.url,
            quality_score=self.confidence_score,
        )


@dataclass(frozen=True)
class ExtractedConcept:
    id: str
    name: str
    description: str = ""
    category: str = ""
    confidence_score: float = 0.5

    def to_signal(self) -> TechnologySignal:
        return TechnologySignal(
            id=self.id,
            name=self.name,
            summary=self.description,
            category=self.category,
            confidence_score=self.confidence_score,
        )


@dataclass(frozen=True)
class ExtractedVersion:
    id: str
    version: str
    created_at: datetime | None = None
    changes: list[str] = field(default_factory=list)

    def to_version(self) -> KnowledgeVersion:
        return KnowledgeVersion(
            id=self.id,
            version=self.version,
            created_at=self.created_at,
            changes=self.changes,
        )


@dataclass(frozen=True)
class ExtractedRelease:
    id: str
    name: str
    version: str
    release_date: datetime | None = None
    description: str = ""
    url: str = ""
    changes: list[str] = field(default_factory=list)

    def to_version(self) -> KnowledgeVersion:
        return KnowledgeVersion(
            id=f"{self.id}_version",
            version=self.version,
            created_at=self.release_date,
            changes=self.changes,
        )


@dataclass(frozen=True)
class ExtractedDependency:
    id: str
    name: str
    version: str = ""
    category: str = ""
    url: str = ""


@dataclass(frozen=True)
class ExtractedExample:
    id: str
    title: str
    description: str = ""
    code: str = ""
    language: str = ""
    url: str = ""

    def to_resource(self) -> KnowledgeResource:
        return KnowledgeResource(
            id=self.id,
            title=self.title,
            resource_type=ResourceType.DOCUMENTATION,
            url=self.url,
        )


@dataclass(frozen=True)
class ExtractedCodeSnippet:
    id: str
    code: str
    language: str = ""
    description: str = ""
    source_url: str = ""

    def to_resource(self) -> KnowledgeResource:
        title = f"Code Snippet ({self.language})" if not self.description else self.description
        return KnowledgeResource(
            id=self.id,
            title=title,
            resource_type=ResourceType.DOCUMENTATION,
            url=self.source_url,
        )


@dataclass(frozen=True)
class ExtractedReference:
    id: str
    source: str
    title: str
    url: str = ""
    published_at: datetime | None = None
    author: str = ""
    confidence: float = 0.5

    def to_evidence(self) -> Evidence:
        return Evidence(
            id=self.id,
            source=self.source,
            title=self.title,
            url=self.url,
            published_at=self.published_at,
            author=self.author,
            confidence=self.confidence,
        )


@dataclass(frozen=True)
class ExtractionContext:
    source_type: KnowledgeSourceType
    source_id: str
    source_name: str
    source_url: str = ""
    content_type: str = ""
    content_size: int = 0
    extracted_at: datetime | None = None
    extraction_mode: str = ""


@dataclass(frozen=True)
class ExtractionStatistics:
    total_entities: int = 0
    technologies: int = 0
    frameworks: int = 0
    models: int = 0
    tools: int = 0
    apis: int = 0
    concepts: int = 0
    versions: int = 0
    releases: int = 0
    dependencies: int = 0
    examples: int = 0
    code_snippets: int = 0
    references: int = 0
    extraction_duration_ms: float = 0.0
    extraction_mode: str = ""
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExtractionRequest:
    content: str
    source_type: KnowledgeSourceType
    source_id: str
    source_name: str
    source_url: str = ""
    content_type: str = ""
    mode: str = ""
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExtractionResult:
    request: ExtractionRequest
    context: ExtractionContext
    technologies: list[ExtractedTechnology] = field(default_factory=list)
    frameworks: list[ExtractedFramework] = field(default_factory=list)
    models: list[ExtractedModel] = field(default_factory=list)
    tools: list[ExtractedTool] = field(default_factory=list)
    apis: list[ExtractedAPI] = field(default_factory=list)
    concepts: list[ExtractedConcept] = field(default_factory=list)
    versions: list[ExtractedVersion] = field(default_factory=list)
    releases: list[ExtractedRelease] = field(default_factory=list)
    dependencies: list[ExtractedDependency] = field(default_factory=list)
    examples: list[ExtractedExample] = field(default_factory=list)
    code_snippets: list[ExtractedCodeSnippet] = field(default_factory=list)
    references: list[ExtractedReference] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    statistics: ExtractionStatistics | None = None

    def to_signals(self) -> list[TechnologySignal]:
        evidence_map = {r.id: r.to_evidence() for r in self.references}
        signals: list[TechnologySignal] = []
        for t in self.technologies:
            signals.append(t.to_signal(evidence_map))
        for c in self.concepts:
            signals.append(c.to_signal())
        return signals

    def to_resources(self) -> list[KnowledgeResource]:
        resources: list[KnowledgeResource] = []
        for f in self.frameworks:
            resources.append(f.to_resource())
        for m in self.models:
            resources.append(m.to_resource())
        for t in self.tools:
            resources.append(t.to_resource())
        for a in self.apis:
            resources.append(a.to_resource())
        for e in self.examples:
            resources.append(e.to_resource())
        for cs in self.code_snippets:
            resources.append(cs.to_resource())
        return resources

    def to_evidence(self) -> list[Evidence]:
        return [r.to_evidence() for r in self.references]

    def to_versions(self) -> list[KnowledgeVersion]:
        versions: list[KnowledgeVersion] = []
        for v in self.versions:
            versions.append(v.to_version())
        for r in self.releases:
            versions.append(r.to_version())
        return versions

    def to_sources(self) -> list[KnowledgeSource]:
        refs = self.references[:]
        source_map: dict[str, KnowledgeSource] = {}
        for r in refs:
            if r.url and r.url not in source_map:
                source_map[r.url] = KnowledgeSource(
                    id=f"src_{r.id}",
                    name=r.source,
                    source_type=KnowledgeSourceType.BLOG,
                    base_url=r.url,
                    credibility_score=r.confidence,
                )
        return list(source_map.values())

    def to_discovery_result(self) -> DiscoveryResult:
        return DiscoveryResult(
            source_type=self.request.source_type,
            sources=self.to_sources(),
            signals=self.to_signals(),
            resources=self.to_resources(),
            events=[],
            trends=[],
            errors=self.errors[:],
        )
