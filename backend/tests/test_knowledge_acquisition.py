"""Tests for the knowledge acquisition engine."""

from __future__ import annotations

from datetime import datetime

import pytest

from aicos.knowledge_acquisition.adapters import (
    GitHubAdapter,
    KnowledgeAdapter,
    OfficialDocsAdapter,
    ResearchAdapter,
    XAdapter,
    YouTubeAdapter,
)
from aicos.knowledge_acquisition.adapters.base import KnowledgeAdapter as KnowledgeAdapterBase
from aicos.knowledge_acquisition.exceptions import (
    AdapterExecutionError,
    AdapterRegistrationError,
    DiscoveryError,
    KnowledgeAcquisitionError,
    NormalizationError,
)
from aicos.knowledge_acquisition.interfaces import (
    DiscoveryOrchestratorProtocol,
    KnowledgeAdapterProtocol,
    NormalizationServiceProtocol,
)
from aicos.knowledge_acquisition.models import (
    AcquisitionStatistics,
    AdapterHealth,
    DiscoveryRequest,
    DiscoveryResult,
)
from aicos.knowledge_acquisition.normalizer import NormalizationService
from aicos.knowledge_acquisition.orchestrator import DiscoveryOrchestrator
from aicos.knowledge_acquisition.registry import AdapterRegistry
from aicos.knowledge_intelligence.enums import KnowledgeSourceType
from aicos.knowledge_intelligence.models import (
    KnowledgeResource,
    KnowledgeSource,
    TechnologySignal,
    TrendSnapshot,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def registry() -> AdapterRegistry:
    return AdapterRegistry()


@pytest.fixture
def official_docs() -> OfficialDocsAdapter:
    return OfficialDocsAdapter()


@pytest.fixture
def github() -> GitHubAdapter:
    return GitHubAdapter()


@pytest.fixture
def youtube() -> YouTubeAdapter:
    return YouTubeAdapter()


@pytest.fixture
def research() -> ResearchAdapter:
    return ResearchAdapter()


@pytest.fixture
def x_adapter() -> XAdapter:
    return XAdapter()


@pytest.fixture
def populated_registry(
    official_docs: OfficialDocsAdapter,
    github: GitHubAdapter,
    youtube: YouTubeAdapter,
    research: ResearchAdapter,
    x_adapter: XAdapter,
) -> AdapterRegistry:
    reg = AdapterRegistry()
    reg.register(official_docs)
    reg.register(github)
    reg.register(youtube)
    reg.register(research)
    reg.register(x_adapter)
    return reg


# ---------------------------------------------------------------------------
# Acquisition model tests
# ---------------------------------------------------------------------------


class TestDiscoveryRequest:
    def test_defaults(self) -> None:
        r = DiscoveryRequest(source_type=KnowledgeSourceType.GITHUB)
        assert r.target == ""
        assert r.max_results == 10
        assert r.config == {}

    def test_frozen(self) -> None:
        r = DiscoveryRequest(source_type=KnowledgeSourceType.GITHUB)
        with pytest.raises(AttributeError):
            r.target = "new"  # type: ignore[misc]


class TestDiscoveryResult:
    def test_defaults(self) -> None:
        r = DiscoveryResult(source_type=KnowledgeSourceType.GITHUB)
        assert r.sources == []
        assert r.signals == []
        assert r.resources == []
        assert r.errors == []
        assert r.duration_ms == 0.0

    def test_frozen(self) -> None:
        r = DiscoveryResult(source_type=KnowledgeSourceType.GITHUB)
        with pytest.raises(AttributeError):
            r.duration_ms = 1.0  # type: ignore[misc]


class TestAdapterHealth:
    def test_defaults(self) -> None:
        h = AdapterHealth(adapter_name="test")
        assert h.healthy is True
        assert h.message == ""
        assert h.response_time_ms == 0.0

    def test_frozen(self) -> None:
        h = AdapterHealth(adapter_name="test")
        with pytest.raises(AttributeError):
            h.healthy = False  # type: ignore[misc]


class TestAcquisitionStatistics:
    def test_defaults(self) -> None:
        s = AcquisitionStatistics()
        assert s.total_discoveries == 0
        assert s.total_errors == 0
        assert s.adapter_stats == {}

    def test_frozen(self) -> None:
        s = AcquisitionStatistics()
        with pytest.raises(AttributeError):
            s.total_discoveries = 1  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Adapter contract tests
# ---------------------------------------------------------------------------


class TestAdapterContract:
    def test_base_class_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            KnowledgeAdapterBase()  # type: ignore[abstract]

    def test_official_docs_implements_protocol(self) -> None:
        assert isinstance(OfficialDocsAdapter(), KnowledgeAdapterProtocol)

    def test_github_implements_protocol(self) -> None:
        assert isinstance(GitHubAdapter(), KnowledgeAdapterProtocol)

    def test_youtube_implements_protocol(self) -> None:
        assert isinstance(YouTubeAdapter(), KnowledgeAdapterProtocol)

    def test_research_implements_protocol(self) -> None:
        assert isinstance(ResearchAdapter(), KnowledgeAdapterProtocol)

    def test_x_implements_protocol(self) -> None:
        assert isinstance(XAdapter(), KnowledgeAdapterProtocol)


class TestOfficialDocsAdapter:
    def test_name(self) -> None:
        assert OfficialDocsAdapter().name == "official_docs"

    def test_supported_source(self) -> None:
        assert OfficialDocsAdapter().supported_source() == KnowledgeSourceType.OFFICIAL_DOCUMENTATION

    def test_discover_returns_result(self) -> None:
        req = DiscoveryRequest(
            source_type=KnowledgeSourceType.OFFICIAL_DOCUMENTATION,
            target="python",
        )
        result = OfficialDocsAdapter().discover(req)
        assert isinstance(result, DiscoveryResult)
        assert len(result.sources) == 1
        assert result.sources[0].name == "python Documentation"

    def test_discover_with_config(self) -> None:
        adapter = OfficialDocsAdapter(config={"base_url": "https://custom.example.com"})
        req = DiscoveryRequest(
            source_type=KnowledgeSourceType.OFFICIAL_DOCUMENTATION,
            target="python",
        )
        result = adapter.discover(req)
        assert len(result.sources) == 1

    def test_refresh(self) -> None:
        req = DiscoveryRequest(
            source_type=KnowledgeSourceType.OFFICIAL_DOCUMENTATION,
            target="python",
        )
        result = OfficialDocsAdapter().refresh(req)
        assert isinstance(result, DiscoveryResult)

    def test_verify(self) -> None:
        health = OfficialDocsAdapter().verify()
        assert health.adapter_name == "official_docs"
        assert health.healthy is True


class TestGitHubAdapter:
    def test_name(self) -> None:
        assert GitHubAdapter().name == "github"

    def test_supported_source(self) -> None:
        assert GitHubAdapter().supported_source() == KnowledgeSourceType.GITHUB

    def test_discover_returns_signals(self) -> None:
        req = DiscoveryRequest(
            source_type=KnowledgeSourceType.GITHUB,
            target="rust",
        )
        result = GitHubAdapter().discover(req)
        assert len(result.signals) == 1
        assert result.signals[0].name == "rust"

    def test_discover_returns_evidence(self) -> None:
        req = DiscoveryRequest(
            source_type=KnowledgeSourceType.GITHUB,
            target="rust",
        )
        result = GitHubAdapter().discover(req)
        assert len(result.signals[0].evidence) == 1

    def test_verify(self) -> None:
        health = GitHubAdapter().verify()
        assert health.healthy is True


class TestYouTubeAdapter:
    def test_name(self) -> None:
        assert YouTubeAdapter().name == "youtube"

    def test_supported_source(self) -> None:
        assert YouTubeAdapter().supported_source() == KnowledgeSourceType.YOUTUBE

    def test_discover_returns_resources(self) -> None:
        req = DiscoveryRequest(
            source_type=KnowledgeSourceType.YOUTUBE,
            target="python",
        )
        result = YouTubeAdapter().discover(req)
        assert len(result.resources) == 1

    def test_verify(self) -> None:
        health = YouTubeAdapter().verify()
        assert health.healthy is True


class TestResearchAdapter:
    def test_name(self) -> None:
        assert ResearchAdapter().name == "research"

    def test_supported_source(self) -> None:
        assert ResearchAdapter().supported_source() == KnowledgeSourceType.RESEARCH_PAPER

    def test_discover_returns_signals(self) -> None:
        req = DiscoveryRequest(
            source_type=KnowledgeSourceType.RESEARCH_PAPER,
            target="transformers",
        )
        result = ResearchAdapter().discover(req)
        assert len(result.signals) == 1

    def test_refresh(self) -> None:
        req = DiscoveryRequest(
            source_type=KnowledgeSourceType.RESEARCH_PAPER,
            target="transformers",
        )
        result = ResearchAdapter().refresh(req)
        assert isinstance(result, DiscoveryResult)

    def test_verify(self) -> None:
        health = ResearchAdapter().verify()
        assert health.healthy is True


class TestXAdapter:
    def test_name(self) -> None:
        assert XAdapter().name == "x"

    def test_supported_source(self) -> None:
        assert XAdapter().supported_source() == KnowledgeSourceType.X

    def test_discover_returns_signals(self) -> None:
        req = DiscoveryRequest(
            source_type=KnowledgeSourceType.X,
            target="rust",
        )
        result = XAdapter().discover(req)
        assert len(result.signals) == 1
        assert len(result.signals[0].evidence) == 1

    def test_refresh(self) -> None:
        req = DiscoveryRequest(
            source_type=KnowledgeSourceType.X,
            target="rust",
        )
        result = XAdapter().refresh(req)
        assert isinstance(result, DiscoveryResult)

    def test_verify(self) -> None:
        health = XAdapter().verify()
        assert health.healthy is True


class TestYouTubeAdapterExtended:
    def test_refresh(self) -> None:
        req = DiscoveryRequest(
            source_type=KnowledgeSourceType.YOUTUBE,
            target="python",
        )
        result = YouTubeAdapter().refresh(req)
        assert isinstance(result, DiscoveryResult)


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


class TestAdapterRegistry:
    def test_register_adapter(self, registry: AdapterRegistry) -> None:
        adapter = OfficialDocsAdapter()
        registry.register(adapter)
        assert registry.count == 1

    def test_lookup_registered_adapter(self, registry: AdapterRegistry) -> None:
        adapter = GitHubAdapter()
        registry.register(adapter)
        found = registry.lookup(KnowledgeSourceType.GITHUB)
        assert found is adapter

    def test_lookup_missing_returns_none(self, registry: AdapterRegistry) -> None:
        found = registry.lookup(KnowledgeSourceType.GITHUB)
        assert found is None

    def test_discover_registered_adapter(self, registry: AdapterRegistry) -> None:
        adapter = OfficialDocsAdapter()
        registry.register(adapter)
        found = registry.discover(KnowledgeSourceType.OFFICIAL_DOCUMENTATION)
        assert found is adapter

    def test_discover_missing_raises(self, registry: AdapterRegistry) -> None:
        with pytest.raises(AdapterRegistrationError, match="no adapter registered"):
            registry.discover(KnowledgeSourceType.GITHUB)

    def test_duplicate_registration_raises(self, registry: AdapterRegistry) -> None:
        registry.register(OfficialDocsAdapter())
        with pytest.raises(AdapterRegistrationError, match="already registered"):
            registry.register(OfficialDocsAdapter())

    def test_registered_types(self, registry: AdapterRegistry) -> None:
        registry.register(GitHubAdapter())
        registry.register(YouTubeAdapter())
        types = registry.registered_types
        assert KnowledgeSourceType.GITHUB in types
        assert KnowledgeSourceType.YOUTUBE in types
        assert KnowledgeSourceType.X not in types

    def test_registered_adapters(self, registry: AdapterRegistry) -> None:
        a1 = GitHubAdapter()
        a2 = YouTubeAdapter()
        registry.register(a1)
        registry.register(a2)
        adapters = registry.registered_adapters
        assert a1 in adapters
        assert a2 in adapters

    def test_count(self, registry: AdapterRegistry) -> None:
        assert registry.count == 0
        registry.register(OfficialDocsAdapter())
        assert registry.count == 1
        registry.register(GitHubAdapter())
        assert registry.count == 2

    def test_register_non_protocol_raises(self, registry: AdapterRegistry) -> None:
        with pytest.raises(AdapterRegistrationError, match="does not implement"):
            registry.register("not_an_adapter")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Normalizer tests
# ---------------------------------------------------------------------------


class FakeDomainService:
    def validate_sources(self, sources: list) -> None:
        pass

    def validate_signals(self, signals: list) -> None:
        pass

    def validate_resources(self, resources: list) -> None:
        pass

    def validate_trends(self, trends: list) -> None:
        pass

    def validate_versions(self, versions: list) -> None:
        pass

    def validate_jobs(self, jobs: list) -> None:
        pass

    def validate_evidence(self, evidence_list: list) -> None:
        pass


class TestNormalizationService:
    def test_normalize_empty_result(self) -> None:
        svc = NormalizationService(FakeDomainService())
        result = DiscoveryResult(source_type=KnowledgeSourceType.GITHUB)
        normalized = svc.normalize(result)
        assert normalized is result

    def test_normalize_with_sources(self) -> None:
        svc = NormalizationService(FakeDomainService())
        source = KnowledgeSource(
            id="s1",
            name="Test",
            source_type=KnowledgeSourceType.GITHUB,
        )
        result = DiscoveryResult(
            source_type=KnowledgeSourceType.GITHUB,
            sources=[source],
        )
        normalized = svc.normalize(result)
        assert normalized.sources[0].name == "Test"

    def test_normalize_validation_failure_raises(self) -> None:
        class FailingDomainService:
            def validate_sources(self, sources: list) -> None:
                msg = "validation failed"
                raise ValueError(msg)

            def validate_signals(self, signals: list) -> None:
                pass

            def validate_resources(self, resources: list) -> None:
                pass

            def validate_trends(self, trends: list) -> None:
                pass

            def validate_versions(self, versions: list) -> None:
                pass

            def validate_jobs(self, jobs: list) -> None:
                pass

            def validate_evidence(self, evidence_list: list) -> None:
                pass

        svc = NormalizationService(FailingDomainService())
        source = KnowledgeSource(
            id="s1",
            name="Test",
            source_type=KnowledgeSourceType.GITHUB,
        )
        result = DiscoveryResult(
            source_type=KnowledgeSourceType.GITHUB,
            sources=[source],
        )
        with pytest.raises(NormalizationError):
            svc.normalize(result)

    def test_normalize_fails_on_signals(self) -> None:
        class FailOnSignals:
            def validate_sources(self, sources: list) -> None: pass
            def validate_signals(self, signals: list) -> None: raise ValueError("signal fail")
            def validate_resources(self, resources: list) -> None: pass
            def validate_trends(self, trends: list) -> None: pass
            def validate_versions(self, versions: list) -> None: pass
            def validate_jobs(self, jobs: list) -> None: pass
            def validate_evidence(self, evidence_list: list) -> None: pass

        svc = NormalizationService(FailOnSignals())
        result = DiscoveryResult(
            source_type=KnowledgeSourceType.GITHUB,
            signals=[TechnologySignal(id="s1", name="Test", summary="test")],
        )
        with pytest.raises(NormalizationError):
            svc.normalize(result)

    def test_normalize_fails_on_resources(self) -> None:
        class FailOnResources:
            def validate_sources(self, sources: list) -> None: pass
            def validate_signals(self, signals: list) -> None: pass
            def validate_resources(self, resources: list) -> None: raise ValueError("resource fail")
            def validate_trends(self, trends: list) -> None: pass
            def validate_versions(self, versions: list) -> None: pass
            def validate_jobs(self, jobs: list) -> None: pass
            def validate_evidence(self, evidence_list: list) -> None: pass

        svc = NormalizationService(FailOnResources())
        result = DiscoveryResult(
            source_type=KnowledgeSourceType.GITHUB,
            resources=[KnowledgeResource(id="r1", title="Test")],
        )
        with pytest.raises(NormalizationError):
            svc.normalize(result)

    def test_normalize_fails_on_trends(self) -> None:
        class FailOnTrends:
            def validate_sources(self, sources: list) -> None: pass
            def validate_signals(self, signals: list) -> None: pass
            def validate_resources(self, resources: list) -> None: pass
            def validate_trends(self, trends: list) -> None: raise ValueError("trend fail")
            def validate_versions(self, versions: list) -> None: pass
            def validate_jobs(self, jobs: list) -> None: pass
            def validate_evidence(self, evidence_list: list) -> None: pass

        svc = NormalizationService(FailOnTrends())
        result = DiscoveryResult(
            source_type=KnowledgeSourceType.GITHUB,
            trends=[TrendSnapshot(technology="Python")],
        )
        with pytest.raises(NormalizationError):
            svc.normalize(result)

    def test_normalize_service_conforms_to_protocol(self) -> None:
        svc = NormalizationService(FakeDomainService())
        assert isinstance(svc, NormalizationServiceProtocol)


# ---------------------------------------------------------------------------
# Orchestrator tests
# ---------------------------------------------------------------------------


class FakeNormalizer:
    def normalize(self, result: DiscoveryResult) -> DiscoveryResult:
        return result


class TestDiscoveryOrchestrator:
    def test_discover(self, populated_registry: AdapterRegistry) -> None:
        orch = DiscoveryOrchestrator(populated_registry, FakeNormalizer())
        req = DiscoveryRequest(
            source_type=KnowledgeSourceType.GITHUB,
            target="rust",
        )
        result = orch.discover(req)
        assert isinstance(result, DiscoveryResult)
        assert result.source_type == KnowledgeSourceType.GITHUB
        assert result.duration_ms >= 0

    def test_discover_unknown_source_raises(self, registry: AdapterRegistry) -> None:
        orch = DiscoveryOrchestrator(registry, FakeNormalizer())
        req = DiscoveryRequest(
            source_type=KnowledgeSourceType.GITHUB,
            target="rust",
        )
        with pytest.raises(AdapterRegistrationError):
            orch.discover(req)

    def test_refresh(self, populated_registry: AdapterRegistry) -> None:
        orch = DiscoveryOrchestrator(populated_registry, FakeNormalizer())
        req = DiscoveryRequest(
            source_type=KnowledgeSourceType.GITHUB,
            target="rust",
        )
        result = orch.refresh(req)
        assert isinstance(result, DiscoveryResult)

    def test_verify_source(self, populated_registry: AdapterRegistry) -> None:
        orch = DiscoveryOrchestrator(populated_registry, FakeNormalizer())
        health = orch.verify_source(KnowledgeSourceType.GITHUB)
        assert health.adapter_name == "github"
        assert health.healthy is True

    def test_verify_source_unknown_raises(self, registry: AdapterRegistry) -> None:
        orch = DiscoveryOrchestrator(registry, FakeNormalizer())
        with pytest.raises(AdapterRegistrationError):
            orch.verify_source(KnowledgeSourceType.GITHUB)

    def test_verify_all(self, populated_registry: AdapterRegistry) -> None:
        orch = DiscoveryOrchestrator(populated_registry, FakeNormalizer())
        results = orch.verify_all()
        assert len(results) == 5
        assert all(h.healthy for h in results)

    def test_verify_all_empty_registry(self, registry: AdapterRegistry) -> None:
        orch = DiscoveryOrchestrator(registry, FakeNormalizer())
        results = orch.verify_all()
        assert results == []

    def test_discover_handles_adapter_failure(self, populated_registry: AdapterRegistry) -> None:
        class FailingAdapter:
            name = "failing"

            def supported_source(self):
                return KnowledgeSourceType.GITHUB

            def discover(self, request):
                msg = "adapter error"
                raise RuntimeError(msg)

            def refresh(self, request):
                msg = "adapter error"
                raise RuntimeError(msg)

            def verify(self):
                msg = "verify error"
                raise RuntimeError(msg)

        populated_registry._adapters[KnowledgeSourceType.GITHUB] = FailingAdapter()  # type: ignore[assignment]
        orch = DiscoveryOrchestrator(populated_registry, FakeNormalizer())
        req = DiscoveryRequest(
            source_type=KnowledgeSourceType.GITHUB,
            target="rust",
        )
        with pytest.raises(AdapterExecutionError, match="failing"):
            orch.discover(req)

    def test_refresh_handles_adapter_failure(self, populated_registry: AdapterRegistry) -> None:
        class FailingRefreshAdapter:
            name = "failing_refresh"

            def supported_source(self):
                return KnowledgeSourceType.OFFICIAL_DOCUMENTATION

            def discover(self, request):
                return DiscoveryResult(source_type=KnowledgeSourceType.OFFICIAL_DOCUMENTATION)

            def refresh(self, request):
                msg = "refresh error"
                raise RuntimeError(msg)

            def verify(self):
                return AdapterHealth(adapter_name="failing_refresh", healthy=True)

        populated_registry._adapters[KnowledgeSourceType.OFFICIAL_DOCUMENTATION] = FailingRefreshAdapter()  # type: ignore[assignment]
        orch = DiscoveryOrchestrator(populated_registry, FakeNormalizer())
        req = DiscoveryRequest(
            source_type=KnowledgeSourceType.OFFICIAL_DOCUMENTATION,
            target="python",
        )
        with pytest.raises(AdapterExecutionError, match="refresh error"):
            orch.refresh(req)

    def test_verify_source_adapter_failure(self, populated_registry: AdapterRegistry) -> None:
        class FailingVerifyAdapter:
            name = "failing_verify"

            def supported_source(self):
                return KnowledgeSourceType.OFFICIAL_DOCUMENTATION

            def discover(self, request):
                return DiscoveryResult(source_type=KnowledgeSourceType.OFFICIAL_DOCUMENTATION)

            def refresh(self, request):
                return DiscoveryResult(source_type=KnowledgeSourceType.OFFICIAL_DOCUMENTATION)

            def verify(self):
                msg = "verify error"
                raise RuntimeError(msg)

        populated_registry._adapters[KnowledgeSourceType.OFFICIAL_DOCUMENTATION] = FailingVerifyAdapter()  # type: ignore[assignment]
        orch = DiscoveryOrchestrator(populated_registry, FakeNormalizer())
        with pytest.raises(AdapterExecutionError, match="verify error"):
            orch.verify_source(KnowledgeSourceType.OFFICIAL_DOCUMENTATION)

    def test_verify_all_with_failing_adapter(self, populated_registry: AdapterRegistry) -> None:
        class FailingVerifyAdapter:
            name = "failing_v"

            def supported_source(self):
                return KnowledgeSourceType.OFFICIAL_DOCUMENTATION

            def discover(self, request):
                return DiscoveryResult(source_type=KnowledgeSourceType.OFFICIAL_DOCUMENTATION)

            def refresh(self, request):
                return DiscoveryResult(source_type=KnowledgeSourceType.OFFICIAL_DOCUMENTATION)

            def verify(self):
                msg = "fail"
                raise RuntimeError(msg)

        populated_registry._adapters[KnowledgeSourceType.OFFICIAL_DOCUMENTATION] = FailingVerifyAdapter()  # type: ignore[assignment]
        orch = DiscoveryOrchestrator(populated_registry, FakeNormalizer())
        results = orch.verify_all()
        failing = [h for h in results if not h.healthy]
        assert len(failing) == 1
        assert failing[0].adapter_name == "failing_v"

    def test_discover_records_duration(self, populated_registry: AdapterRegistry) -> None:
        orch = DiscoveryOrchestrator(populated_registry, FakeNormalizer())
        req = DiscoveryRequest(
            source_type=KnowledgeSourceType.OFFICIAL_DOCUMENTATION,
            target="python",
        )
        result = orch.discover(req)
        assert result.duration_ms > 0

    def test_orchestrator_conforms_to_protocol(self, populated_registry: AdapterRegistry) -> None:
        orch = DiscoveryOrchestrator(populated_registry, FakeNormalizer())
        assert isinstance(orch, DiscoveryOrchestratorProtocol)


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class TestExceptionHierarchy:
    def test_base_type(self) -> None:
        assert issubclass(AdapterRegistrationError, KnowledgeAcquisitionError)
        assert issubclass(AdapterExecutionError, KnowledgeAcquisitionError)
        assert issubclass(NormalizationError, KnowledgeAcquisitionError)
        assert issubclass(DiscoveryError, KnowledgeAcquisitionError)


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


class TestKnowledgeAdapterProtocol:
    def test_official_docs_conforms(self) -> None:
        assert isinstance(OfficialDocsAdapter(), KnowledgeAdapterProtocol)

    def test_github_conforms(self) -> None:
        assert isinstance(GitHubAdapter(), KnowledgeAdapterProtocol)

    def test_youtube_conforms(self) -> None:
        assert isinstance(YouTubeAdapter(), KnowledgeAdapterProtocol)

    def test_research_conforms(self) -> None:
        assert isinstance(ResearchAdapter(), KnowledgeAdapterProtocol)

    def test_x_conforms(self) -> None:
        assert isinstance(XAdapter(), KnowledgeAdapterProtocol)


# ---------------------------------------------------------------------------
# DI registration
# ---------------------------------------------------------------------------


class TestDependencyInjection:
    def test_register_function_exists(self) -> None:
        from aicos.knowledge_acquisition import register_knowledge_acquisition
        assert callable(register_knowledge_acquisition)
