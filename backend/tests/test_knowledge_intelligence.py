"""Tests for the knowledge intelligence domain."""

from __future__ import annotations

from datetime import datetime

import pytest

from aicos.knowledge_intelligence.enums import (
    JobType,
    KnowledgeSourceType,
    ResourceType,
    TechnologyStatus,
)
from aicos.knowledge_intelligence.exceptions import (
    EvidenceValidationError,
    JobValidationError,
    KnowledgeDomainError,
    ResourceValidationError,
    SignalValidationError,
    SourceValidationError,
    TrendValidationError,
    VersionValidationError,
)
from aicos.knowledge_intelligence.interfaces import (
    KnowledgeIntelligenceDomainServiceProtocol,
)
from aicos.knowledge_intelligence.models import (
    DiscoveryJob,
    Evidence,
    KnowledgeResource,
    KnowledgeSource,
    KnowledgeVersion,
    ResourceCollection,
    TechnologyLifecycleEvent,
    TechnologySignal,
    TrendSnapshot,
)
from aicos.knowledge_intelligence.service import (
    KnowledgeIntelligenceDomainService,
)


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------

class TestKnowledgeSourceType:
    def test_values(self) -> None:
        assert list(KnowledgeSourceType) == [
            KnowledgeSourceType.OFFICIAL_DOCUMENTATION,
            KnowledgeSourceType.GITHUB,
            KnowledgeSourceType.YOUTUBE,
            KnowledgeSourceType.X,
            KnowledgeSourceType.RESEARCH_PAPER,
            KnowledgeSourceType.BLOG,
            KnowledgeSourceType.CONFERENCE,
            KnowledgeSourceType.COMPANY,
            KnowledgeSourceType.COMMUNITY,
        ]

    def test_string_access(self) -> None:
        assert KnowledgeSourceType("github") == KnowledgeSourceType.GITHUB
        assert KnowledgeSourceType.OFFICIAL_DOCUMENTATION.value == "official_documentation"


class TestTechnologyStatus:
    def test_values(self) -> None:
        assert list(TechnologyStatus) == [
            TechnologyStatus.EXPERIMENTAL,
            TechnologyStatus.EMERGING,
            TechnologyStatus.GROWING,
            TechnologyStatus.RECOMMENDED,
            TechnologyStatus.INDUSTRY_STANDARD,
            TechnologyStatus.LEGACY,
            TechnologyStatus.DEPRECATED,
        ]

    def test_string_access(self) -> None:
        assert TechnologyStatus("recommended") == TechnologyStatus.RECOMMENDED
        assert TechnologyStatus.DEPRECATED.value == "deprecated"


class TestResourceType:
    def test_values(self) -> None:
        assert list(ResourceType) == [
            ResourceType.DOCUMENTATION,
            ResourceType.VIDEO,
            ResourceType.REPOSITORY,
            ResourceType.COURSE,
            ResourceType.BOOK,
            ResourceType.ARTICLE,
            ResourceType.WORKSHOP,
        ]

    def test_string_access(self) -> None:
        assert ResourceType("workshop") == ResourceType.WORKSHOP
        assert ResourceType.VIDEO.value == "video"


class TestJobType:
    def test_values(self) -> None:
        assert list(JobType) == [
            JobType.TECHNOLOGY_DISCOVERY,
            JobType.RESOURCE_REFRESH,
            JobType.TREND_ANALYSIS,
            JobType.VERIFICATION,
            JobType.KNOWLEDGE_VERSIONING,
        ]

    def test_string_access(self) -> None:
        assert JobType("verification") == JobType.VERIFICATION
        assert JobType.TREND_ANALYSIS.value == "trend_analysis"


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestKnowledgeSource:
    def test_defaults(self) -> None:
        s = KnowledgeSource(
            id="src1",
            name="Python Docs",
            source_type=KnowledgeSourceType.OFFICIAL_DOCUMENTATION,
        )
        assert s.provider == ""
        assert s.base_url == ""
        assert s.credibility_score == 0.5
        assert s.priority == 50
        assert s.enabled is True
        assert s.last_checked is None

    def test_frozen(self) -> None:
        s = KnowledgeSource(id="s1", name="Docs", source_type=KnowledgeSourceType.BLOG)
        with pytest.raises(AttributeError):
            s.name = "new"  # type: ignore[misc]


class TestEvidence:
    def test_defaults(self) -> None:
        e = Evidence(id="ev1", source="Blog", title="Post")
        assert e.url == ""
        assert e.author == ""
        assert e.confidence == 0.5
        assert e.published_at is None

    def test_frozen(self) -> None:
        e = Evidence(id="e1", source="S", title="T")
        with pytest.raises(AttributeError):
            e.title = "new"  # type: ignore[misc]


class TestTechnologySignal:
    def test_defaults(self) -> None:
        sig = TechnologySignal(id="sig1", name="Rust")
        assert sig.summary == ""
        assert sig.status == TechnologyStatus.EMERGING
        assert sig.importance == 5
        assert sig.confidence_score == 0.5
        assert sig.evidence == []
        assert sig.first_seen is None

    def test_frozen(self) -> None:
        sig = TechnologySignal(id="s1", name="Rust")
        with pytest.raises(AttributeError):
            sig.name = "Java"  # type: ignore[misc]


class TestTrendSnapshot:
    def test_defaults(self) -> None:
        t = TrendSnapshot(technology="Python")
        assert t.adoption_score == 0.0
        assert t.overall_score == 0.0
        assert t.captured_at is None

    def test_frozen(self) -> None:
        t = TrendSnapshot(technology="Python")
        with pytest.raises(AttributeError):
            t.technology = "Java"  # type: ignore[misc]


class TestKnowledgeResource:
    def test_defaults(self) -> None:
        r = KnowledgeResource(id="res1", title="Learn Python")
        assert r.resource_type == ResourceType.ARTICLE
        assert r.language == "en"
        assert r.quality_score == 0.5
        assert r.relevant_tracks == []

    def test_frozen(self) -> None:
        r = KnowledgeResource(id="r1", title="Course")
        with pytest.raises(AttributeError):
            r.title = "new"  # type: ignore[misc]


class TestResourceCollection:
    def test_defaults(self) -> None:
        c = ResourceCollection(technology="Python")
        assert c.resources == []
        assert c.last_updated is None

    def test_frozen(self) -> None:
        c = ResourceCollection(technology="Python")
        with pytest.raises(AttributeError):
            c.technology = "Java"  # type: ignore[misc]


class TestTechnologyLifecycleEvent:
    def test_defaults(self) -> None:
        e = TechnologyLifecycleEvent(technology="Rust")
        assert e.previous_status is None
        assert e.new_status == TechnologyStatus.EMERGING
        assert e.reason == ""
        assert e.changed_at is None

    def test_frozen(self) -> None:
        e = TechnologyLifecycleEvent(technology="Rust")
        with pytest.raises(AttributeError):
            e.technology = "Java"  # type: ignore[misc]


class TestKnowledgeVersion:
    def test_defaults(self) -> None:
        v = KnowledgeVersion(id="v1")
        assert v.version == "0.1.0"
        assert v.changes == []
        assert v.created_at is None

    def test_frozen(self) -> None:
        v = KnowledgeVersion(id="v1")
        with pytest.raises(AttributeError):
            v.version = "1.0"  # type: ignore[misc]


class TestDiscoveryJob:
    def test_defaults(self) -> None:
        j = DiscoveryJob(id="j1", job_type=JobType.TECHNOLOGY_DISCOVERY)
        assert j.target == ""
        assert j.schedule == ""
        assert j.enabled is True
        assert j.last_run is None
        assert j.next_run is None

    def test_frozen(self) -> None:
        j = DiscoveryJob(id="j1")
        with pytest.raises(AttributeError):
            j.target = "new"  # type: ignore[misc]

    def test_default_job_type(self) -> None:
        j = DiscoveryJob(id="j1")
        assert j.job_type == JobType.TECHNOLOGY_DISCOVERY


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------

class TestSourceValidation:
    def test_valid_sources(self) -> None:
        sources = [
            KnowledgeSource(id="s1", name="Docs", source_type=KnowledgeSourceType.OFFICIAL_DOCUMENTATION),
            KnowledgeSource(id="s2", name="Blog", source_type=KnowledgeSourceType.BLOG),
        ]
        KnowledgeIntelligenceDomainService().validate_sources(sources)

    def test_empty_id(self) -> None:
        with pytest.raises(SourceValidationError, match="id"):
            KnowledgeIntelligenceDomainService().validate_sources(
                [KnowledgeSource(id="", name="Docs", source_type=KnowledgeSourceType.BLOG)]
            )

    def test_empty_name(self) -> None:
        with pytest.raises(SourceValidationError, match="name"):
            KnowledgeIntelligenceDomainService().validate_sources(
                [KnowledgeSource(id="s1", name="", source_type=KnowledgeSourceType.BLOG)]
            )

    def test_duplicate_id(self) -> None:
        with pytest.raises(SourceValidationError, match="duplicate"):
            KnowledgeIntelligenceDomainService().validate_sources([
                KnowledgeSource(id="s1", name="Docs", source_type=KnowledgeSourceType.BLOG),
                KnowledgeSource(id="s1", name="Blog", source_type=KnowledgeSourceType.BLOG),
            ])

    def test_credibility_score_too_low(self) -> None:
        with pytest.raises(SourceValidationError, match="credibility_score"):
            KnowledgeIntelligenceDomainService().validate_sources(
                [KnowledgeSource(id="s1", name="Docs", source_type=KnowledgeSourceType.BLOG, credibility_score=-0.1)]
            )

    def test_credibility_score_too_high(self) -> None:
        with pytest.raises(SourceValidationError, match="credibility_score"):
            KnowledgeIntelligenceDomainService().validate_sources(
                [KnowledgeSource(id="s1", name="Docs", source_type=KnowledgeSourceType.BLOG, credibility_score=1.1)]
            )

    def test_priority_too_low(self) -> None:
        with pytest.raises(SourceValidationError, match="priority"):
            KnowledgeIntelligenceDomainService().validate_sources(
                [KnowledgeSource(id="s1", name="Docs", source_type=KnowledgeSourceType.BLOG, priority=-1)]
            )

    def test_priority_too_high(self) -> None:
        with pytest.raises(SourceValidationError, match="priority"):
            KnowledgeIntelligenceDomainService().validate_sources(
                [KnowledgeSource(id="s1", name="Docs", source_type=KnowledgeSourceType.BLOG, priority=101)]
            )

    def test_invalid_source_type(self) -> None:
        from aicos.knowledge_intelligence.validation import validate_sources
        s = KnowledgeSource(id="s1", name="X", source_type="invalid")  # type: ignore[arg-type]
        with pytest.raises(SourceValidationError, match="source_type"):
            validate_sources([s])


class TestSignalValidation:
    def test_valid_signals(self) -> None:
        signals = [
            TechnologySignal(id="sig1", name="Rust", summary="Systems language"),
            TechnologySignal(id="sig2", name="Zig", summary="Modern systems language"),
        ]
        KnowledgeIntelligenceDomainService().validate_signals(signals)

    def test_empty_id(self) -> None:
        with pytest.raises(SignalValidationError, match="id"):
            KnowledgeIntelligenceDomainService().validate_signals(
                [TechnologySignal(id="", name="Rust", summary="Lang")]
            )

    def test_empty_name(self) -> None:
        with pytest.raises(SignalValidationError, match="name"):
            KnowledgeIntelligenceDomainService().validate_signals(
                [TechnologySignal(id="sig1", name="", summary="Lang")]
            )

    def test_empty_summary(self) -> None:
        with pytest.raises(SignalValidationError, match="summary"):
            KnowledgeIntelligenceDomainService().validate_signals(
                [TechnologySignal(id="sig1", name="Rust", summary="")]
            )

    def test_duplicate_id(self) -> None:
        with pytest.raises(SignalValidationError, match="duplicate"):
            KnowledgeIntelligenceDomainService().validate_signals([
                TechnologySignal(id="sig1", name="Rust", summary="Lang"),
                TechnologySignal(id="sig1", name="Zig", summary="Lang"),
            ])

    def test_importance_too_low(self) -> None:
        with pytest.raises(SignalValidationError, match="importance"):
            KnowledgeIntelligenceDomainService().validate_signals(
                [TechnologySignal(id="sig1", name="Rust", summary="Lang", importance=-1)]
            )

    def test_importance_too_high(self) -> None:
        with pytest.raises(SignalValidationError, match="importance"):
            KnowledgeIntelligenceDomainService().validate_signals(
                [TechnologySignal(id="sig1", name="Rust", summary="Lang", importance=11)]
            )

    def test_confidence_score_too_low(self) -> None:
        with pytest.raises(SignalValidationError, match="confidence_score"):
            KnowledgeIntelligenceDomainService().validate_signals(
                [TechnologySignal(id="sig1", name="Rust", summary="Lang", confidence_score=-0.1)]
            )

    def test_confidence_score_too_high(self) -> None:
        with pytest.raises(SignalValidationError, match="confidence_score"):
            KnowledgeIntelligenceDomainService().validate_signals(
                [TechnologySignal(id="sig1", name="Rust", summary="Lang", confidence_score=1.1)]
            )

    def test_invalid_status(self) -> None:
        from aicos.knowledge_intelligence.validation import validate_signals
        sig = TechnologySignal(id="sig1", name="Rust", summary="Lang", status="invalid")  # type: ignore[arg-type]
        with pytest.raises(SignalValidationError, match="status"):
            validate_signals([sig])

    def test_duplicate_evidence_in_signal(self) -> None:
        with pytest.raises(SignalValidationError, match="duplicate evidence"):
            KnowledgeIntelligenceDomainService().validate_signals([
                TechnologySignal(
                    id="sig1",
                    name="Rust",
                    summary="Lang",
                    evidence=[
                        Evidence(id="ev1", source="Blog", title="Post"),
                        Evidence(id="ev1", source="Blog", title="Another"),
                    ],
                )
            ])


class TestEvidenceValidation:
    def test_valid_evidence(self) -> None:
        ev_list = [
            Evidence(id="ev1", source="Blog", title="Post"),
            Evidence(id="ev2", source="Paper", title="Research"),
        ]
        KnowledgeIntelligenceDomainService().validate_evidence(ev_list)

    def test_empty_id(self) -> None:
        with pytest.raises(EvidenceValidationError, match="id"):
            KnowledgeIntelligenceDomainService().validate_evidence(
                [Evidence(id="", source="Blog", title="Post")]
            )

    def test_empty_source(self) -> None:
        with pytest.raises(EvidenceValidationError, match="source"):
            KnowledgeIntelligenceDomainService().validate_evidence(
                [Evidence(id="ev1", source="", title="Post")]
            )

    def test_empty_title(self) -> None:
        with pytest.raises(EvidenceValidationError, match="title"):
            KnowledgeIntelligenceDomainService().validate_evidence(
                [Evidence(id="ev1", source="Blog", title="")]
            )

    def test_duplicate_id(self) -> None:
        with pytest.raises(EvidenceValidationError, match="duplicate"):
            KnowledgeIntelligenceDomainService().validate_evidence([
                Evidence(id="ev1", source="Blog", title="Post"),
                Evidence(id="ev1", source="Paper", title="Research"),
            ])

    def test_duplicate_url(self) -> None:
        with pytest.raises(EvidenceValidationError, match="url"):
            KnowledgeIntelligenceDomainService().validate_evidence([
                Evidence(id="ev1", source="Blog", title="Post", url="https://example.com"),
                Evidence(id="ev2", source="Blog", title="Copy", url="https://example.com"),
            ])

    def test_confidence_too_low(self) -> None:
        with pytest.raises(EvidenceValidationError, match="confidence"):
            KnowledgeIntelligenceDomainService().validate_evidence(
                [Evidence(id="ev1", source="Blog", title="Post", confidence=-0.1)]
            )

    def test_confidence_too_high(self) -> None:
        with pytest.raises(EvidenceValidationError, match="confidence"):
            KnowledgeIntelligenceDomainService().validate_evidence(
                [Evidence(id="ev1", source="Blog", title="Post", confidence=1.1)]
            )


class TestResourceValidation:
    def test_valid_resources(self) -> None:
        resources = [
            KnowledgeResource(id="r1", title="Course", resource_type=ResourceType.COURSE),
            KnowledgeResource(id="r2", title="Video", resource_type=ResourceType.VIDEO),
        ]
        KnowledgeIntelligenceDomainService().validate_resources(resources)

    def test_empty_id(self) -> None:
        with pytest.raises(ResourceValidationError, match="id"):
            KnowledgeIntelligenceDomainService().validate_resources(
                [KnowledgeResource(id="", title="Course")]
            )

    def test_empty_title(self) -> None:
        with pytest.raises(ResourceValidationError, match="title"):
            KnowledgeIntelligenceDomainService().validate_resources(
                [KnowledgeResource(id="r1", title="")]
            )

    def test_duplicate_id(self) -> None:
        with pytest.raises(ResourceValidationError, match="duplicate"):
            KnowledgeIntelligenceDomainService().validate_resources([
                KnowledgeResource(id="r1", title="Course"),
                KnowledgeResource(id="r1", title="Video"),
            ])

    def test_duplicate_url(self) -> None:
        with pytest.raises(ResourceValidationError, match="url"):
            KnowledgeIntelligenceDomainService().validate_resources([
                KnowledgeResource(id="r1", title="Course", url="https://example.com"),
                KnowledgeResource(id="r2", title="Video", url="https://example.com"),
            ])

    def test_quality_score_too_low(self) -> None:
        with pytest.raises(ResourceValidationError, match="quality_score"):
            KnowledgeIntelligenceDomainService().validate_resources(
                [KnowledgeResource(id="r1", title="Course", quality_score=-0.1)]
            )

    def test_quality_score_too_high(self) -> None:
        with pytest.raises(ResourceValidationError, match="quality_score"):
            KnowledgeIntelligenceDomainService().validate_resources(
                [KnowledgeResource(id="r1", title="Course", quality_score=1.1)]
            )

    def test_invalid_resource_type(self) -> None:
        from aicos.knowledge_intelligence.validation import validate_resources
        r = KnowledgeResource(id="r1", title="Course", resource_type="invalid")  # type: ignore[arg-type]
        with pytest.raises(ResourceValidationError, match="resource_type"):
            validate_resources([r])


class TestTrendValidation:
    def test_valid_trends(self) -> None:
        trends = [
            TrendSnapshot(technology="Python"),
            TrendSnapshot(technology="Rust"),
        ]
        KnowledgeIntelligenceDomainService().validate_trends(trends)

    def test_empty_technology(self) -> None:
        with pytest.raises(TrendValidationError, match="technology"):
            KnowledgeIntelligenceDomainService().validate_trends(
                [TrendSnapshot(technology="")]
            )

    def test_duplicate_technology(self) -> None:
        with pytest.raises(TrendValidationError, match="duplicate"):
            KnowledgeIntelligenceDomainService().validate_trends([
                TrendSnapshot(technology="Python"),
                TrendSnapshot(technology="Python"),
            ])

    @pytest.mark.parametrize("field", [
        "adoption_score",
        "community_score",
        "industry_score",
        "job_market_score",
        "github_score",
        "youtube_score",
        "overall_score",
    ])
    def test_score_too_low(self, field: str) -> None:
        kwargs = {field: -0.1}
        with pytest.raises(TrendValidationError, match=field):
            KnowledgeIntelligenceDomainService().validate_trends(
                [TrendSnapshot(technology="Python", **kwargs)]  # type: ignore[arg-type]
            )

    @pytest.mark.parametrize("field", [
        "adoption_score",
        "community_score",
        "industry_score",
        "job_market_score",
        "github_score",
        "youtube_score",
        "overall_score",
    ])
    def test_score_too_high(self, field: str) -> None:
        kwargs = {field: 1.1}
        with pytest.raises(TrendValidationError, match=field):
            KnowledgeIntelligenceDomainService().validate_trends(
                [TrendSnapshot(technology="Python", **kwargs)]  # type: ignore[arg-type]
            )


class TestVersionValidation:
    def test_valid_versions(self) -> None:
        versions = [
            KnowledgeVersion(id="v1", version="1.0.0"),
            KnowledgeVersion(id="v2", version="2.0.0"),
        ]
        KnowledgeIntelligenceDomainService().validate_versions(versions)

    def test_empty_id(self) -> None:
        with pytest.raises(VersionValidationError, match="id"):
            KnowledgeIntelligenceDomainService().validate_versions(
                [KnowledgeVersion(id="", version="1.0")]
            )

    def test_empty_version_string(self) -> None:
        with pytest.raises(VersionValidationError, match="version"):
            KnowledgeIntelligenceDomainService().validate_versions(
                [KnowledgeVersion(id="v1", version="")]
            )

    def test_duplicate_id(self) -> None:
        with pytest.raises(VersionValidationError, match="duplicate"):
            KnowledgeIntelligenceDomainService().validate_versions([
                KnowledgeVersion(id="v1", version="1.0"),
                KnowledgeVersion(id="v1", version="2.0"),
            ])


class TestJobValidation:
    def test_valid_jobs(self) -> None:
        jobs = [
            DiscoveryJob(id="j1", target="Python ecosystem", job_type=JobType.TECHNOLOGY_DISCOVERY),
            DiscoveryJob(id="j2", target="Rust news", job_type=JobType.TREND_ANALYSIS),
        ]
        KnowledgeIntelligenceDomainService().validate_jobs(jobs)

    def test_empty_id(self) -> None:
        with pytest.raises(JobValidationError, match="id"):
            KnowledgeIntelligenceDomainService().validate_jobs(
                [DiscoveryJob(id="", target="Python")]
            )

    def test_empty_target(self) -> None:
        with pytest.raises(JobValidationError, match="target"):
            KnowledgeIntelligenceDomainService().validate_jobs(
                [DiscoveryJob(id="j1", target="")]
            )

    def test_duplicate_id(self) -> None:
        with pytest.raises(JobValidationError, match="duplicate"):
            KnowledgeIntelligenceDomainService().validate_jobs([
                DiscoveryJob(id="j1", target="Python"),
                DiscoveryJob(id="j1", target="Rust"),
            ])

    def test_invalid_job_type(self) -> None:
        from aicos.knowledge_intelligence.validation import validate_jobs
        j = DiscoveryJob(id="j1", target="Python", job_type="invalid")  # type: ignore[arg-type]
        with pytest.raises(JobValidationError, match="job_type"):
            validate_jobs([j])


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------

class TestProtocolConformance:
    def test_service_conforms_to_protocol(self) -> None:
        assert isinstance(
            KnowledgeIntelligenceDomainService(),
            KnowledgeIntelligenceDomainServiceProtocol,
        )


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------

class TestExceptionHierarchy:
    def test_base_type(self) -> None:
        assert issubclass(SourceValidationError, KnowledgeDomainError)
        assert issubclass(SignalValidationError, KnowledgeDomainError)
        assert issubclass(EvidenceValidationError, KnowledgeDomainError)
        assert issubclass(ResourceValidationError, KnowledgeDomainError)
        assert issubclass(TrendValidationError, KnowledgeDomainError)
        assert issubclass(VersionValidationError, KnowledgeDomainError)
        assert issubclass(JobValidationError, KnowledgeDomainError)


# ---------------------------------------------------------------------------
# ResourceCollection and TechnologyLifecycleEvent edge cases
# ---------------------------------------------------------------------------

class TestResourceCollectionConstruction:
    def test_with_resources(self) -> None:
        r1 = KnowledgeResource(id="r1", title="Course")
        r2 = KnowledgeResource(id="r2", title="Video")
        c = ResourceCollection(technology="Python", resources=[r1, r2])
        assert len(c.resources) == 2
        assert c.resources[0].title == "Course"

    def test_with_last_updated(self) -> None:
        dt = datetime(2025, 6, 1)
        c = ResourceCollection(technology="Python", last_updated=dt)
        assert c.last_updated == dt


class TestTechnologyLifecycleEventConstruction:
    def test_full_event(self) -> None:
        dt = datetime(2025, 6, 1)
        e = TechnologyLifecycleEvent(
            technology="Rust",
            previous_status=TechnologyStatus.EMERGING,
            new_status=TechnologyStatus.GROWING,
            reason="Widespread adoption",
            changed_at=dt,
        )
        assert e.previous_status == TechnologyStatus.EMERGING
        assert e.new_status == TechnologyStatus.GROWING
        assert e.reason == "Widespread adoption"
        assert e.changed_at == dt


# ---------------------------------------------------------------------------
# Signal with evidence via service
# ---------------------------------------------------------------------------

class TestSignalWithEvidence:
    def test_signal_with_valid_evidence(self) -> None:
        sig = TechnologySignal(
            id="sig1",
            name="Rust",
            summary="Growing systems language",
            evidence=[
                Evidence(id="ev1", source="Blog", title="Rust is great"),
                Evidence(id="ev2", source="Paper", title="Rust analysis"),
            ],
        )
        KnowledgeIntelligenceDomainService().validate_signals([sig])

    def test_signal_with_evidence_confidence_via_validate_evidence(self) -> None:
        with pytest.raises(EvidenceValidationError, match="confidence"):
            KnowledgeIntelligenceDomainService().validate_evidence([
                Evidence(id="ev1", source="Blog", title="Post", confidence=1.5),
            ])


# ---------------------------------------------------------------------------
# DI registration
# ---------------------------------------------------------------------------

class TestDependencyInjectionRegistration:
    def test_register_function_exists(self) -> None:
        from aicos.knowledge_intelligence import register_knowledge_intelligence
        assert callable(register_knowledge_intelligence)
