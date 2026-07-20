from __future__ import annotations

import pytest

from aicos.trusted_sources.enums import (
    AuthenticationType,
    Capability,
    Category,
    RefreshFrequency,
    SourceType,
)
from aicos.trusted_sources.exceptions import (
    DuplicateSourceError,
    InvalidSourceError,
    InvalidTrustScoreError,
    SourceNotFoundError,
    TrustedSourceError,
)
from aicos.trusted_sources.models import (
    CapabilityMapping,
    DiscoveryPolicy,
    KnowledgeCatalog,
    TrustedKnowledgeSource,
    TrustedSourceGroup,
)
from aicos.trusted_sources.registry import TrustedKnowledgeRegistry
from aicos.trusted_sources.seed_data import get_seed_sources
from aicos.trusted_sources.service import TrustedKnowledgeService
from aicos.trusted_sources import register_trusted_sources
from aicos.trusted_sources.validation import (
    validate_source,
    validate_source_id,
    validate_trust_score,
)


def _make_source(
    source_id: str = "test-source",
    name: str = "Test Source",
    source_type: SourceType = SourceType.DOCUMENTATION,
    category: Category = Category.LLM,
    trust_score: float = 0.9,
    priority: int = 50,
    enabled: bool = True,
    **kwargs,
) -> TrustedKnowledgeSource:
    return TrustedKnowledgeSource(
        id=source_id,
        name=name,
        source_type=source_type,
        category=category,
        trust_score=trust_score,
        priority=priority,
        enabled=enabled,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TestEnums:
    def test_source_type_values(self) -> None:
        assert SourceType.DOCUMENTATION.value == "documentation"
        assert SourceType.GITHUB.value == "github"
        assert SourceType.YOUTUBE.value == "youtube"
        assert SourceType.RESEARCH.value == "research"
        assert SourceType.BLOG.value == "blog"
        assert SourceType.NEWS.value == "news"
        assert SourceType.SOCIAL.value == "social"
        assert SourceType.PODCAST.value == "podcast"
        assert SourceType.CONFERENCE.value == "conference"
        assert SourceType.BENCHMARK.value == "benchmark"
        assert SourceType.PACKAGE_REGISTRY.value == "package_registry"
        assert SourceType.HARDWARE_VENDOR.value == "hardware_vendor"

    def test_category_values(self) -> None:
        assert Category.LLM.value == "llm"
        assert Category.AGENTS.value == "agents"
        assert Category.RAG.value == "rag"
        assert Category.VISION.value == "vision"
        assert Category.SPEECH.value == "speech"
        assert Category.MULTIMODAL.value == "multimodal"
        assert Category.EDGE_AI.value == "edge_ai"
        assert Category.CLOUD_AI.value == "cloud_ai"
        assert Category.FRAMEWORK.value == "framework"
        assert Category.TOOLING.value == "tooling"
        assert Category.HARDWARE.value == "hardware"
        assert Category.SECURITY.value == "security"
        assert Category.BENCHMARK.value == "benchmark"

    def test_capability_values(self) -> None:
        assert Capability.DOCUMENTATION.value == "documentation"
        assert Capability.RELEASES.value == "releases"
        assert Capability.BLOG_POSTS.value == "blog_posts"
        assert Capability.VIDEOS.value == "videos"
        assert Capability.REPOSITORIES.value == "repositories"
        assert Capability.RESEARCH_PAPERS.value == "research_papers"
        assert Capability.SOCIAL_POSTS.value == "social_posts"
        assert Capability.BENCHMARKS.value == "benchmarks"
        assert Capability.PACKAGES.value == "packages"
        assert Capability.API_REFERENCE.value == "api_reference"
        assert Capability.CHANGELOGS.value == "changelogs"

    def test_auth_type_values(self) -> None:
        assert AuthenticationType.NONE.value == "none"
        assert AuthenticationType.API_KEY.value == "api_key"
        assert AuthenticationType.OAUTH.value == "oauth"
        assert AuthenticationType.BEARER.value == "bearer"

    def test_refresh_frequency_values(self) -> None:
        assert RefreshFrequency.REALTIME.value == "realtime"
        assert RefreshFrequency.HOURLY.value == "hourly"
        assert RefreshFrequency.DAILY.value == "daily"
        assert RefreshFrequency.WEEKLY.value == "weekly"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class TestTrustedKnowledgeSource:
    def test_create_minimal(self) -> None:
        s = TrustedKnowledgeSource(id="src1", name="Source 1", source_type=SourceType.BLOG, category=Category.LLM)
        assert s.id == "src1"
        assert s.name == "Source 1"
        assert s.trust_score == 0.5
        assert s.priority == 50
        assert s.enabled is True
        assert s.authentication_type == AuthenticationType.NONE
        assert s.refresh_frequency == RefreshFrequency.DAILY

    def test_create_full(self) -> None:
        caps = frozenset([Capability.DOCUMENTATION, Capability.RELEASES])
        tags = frozenset(["llm", "api"])
        s = TrustedKnowledgeSource(
            id="full",
            name="Full Source",
            source_type=SourceType.GITHUB,
            category=Category.TOOLING,
            url="https://github.com/org",
            display_name="Full Display",
            organization="Test Org",
            rss_feed="https://feed.url",
            api_endpoint="https://api.endpoint",
            trust_score=0.95,
            priority=80,
            enabled=False,
            authentication_type=AuthenticationType.BEARER,
            refresh_frequency=RefreshFrequency.HOURLY,
            capabilities=caps,
            tags=tags,
            metadata={"key": "value"},
        )
        assert s.url == "https://github.com/org"
        assert s.display_name == "Full Display"
        assert s.trust_score == 0.95
        assert s.capabilities == caps
        assert s.tags == tags

    def test_frozen(self) -> None:
        s = _make_source()
        with pytest.raises(AttributeError):
            s.name = "New Name"  # type: ignore[misc]

    def test_invalid_trust_score_low(self) -> None:
        with pytest.raises(ValueError, match="trust_score"):
            _make_source(trust_score=-0.1)

    def test_invalid_trust_score_high(self) -> None:
        with pytest.raises(ValueError, match="trust_score"):
            _make_source(trust_score=1.5)


class TestOtherModels:
    def test_trusted_source_group(self) -> None:
        g = TrustedSourceGroup(id="grp1", name="Group 1", description="A group", source_ids=frozenset(["a", "b"]))
        assert g.id == "grp1"
        assert "a" in g.source_ids

    def test_capability_mapping(self) -> None:
        m = CapabilityMapping(source_type=SourceType.GITHUB, capability=Capability.REPOSITORIES, description="Repos")
        assert m.source_type == SourceType.GITHUB
        assert m.confidence == 1.0

    def test_discovery_policy(self) -> None:
        caps = frozenset([Capability.RESEARCH_PAPERS])
        p = DiscoveryPolicy(id="pol1", name="Research", capability_filter=caps, max_results=50)
        assert p.id == "pol1"
        assert p.max_results == 50
        assert p.enabled is True

    def test_knowledge_catalog(self) -> None:
        c = KnowledgeCatalog(id="cat1", name="Catalog 1", sources=frozenset(["src1"]))
        assert c.id == "cat1"
        assert c.created_at is None


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestValidation:
    def test_validate_source_valid(self) -> None:
        s = _make_source()
        validate_source(s)

    def test_validate_source_empty_id(self) -> None:
        with pytest.raises(InvalidSourceError, match="id must not be empty"):
            validate_source(_make_source(source_id=""))

    def test_validate_source_empty_name(self) -> None:
        with pytest.raises(InvalidSourceError, match="name must not be empty"):
            validate_source(_make_source(name=""))

    def test_validate_source_negative_priority(self) -> None:
        with pytest.raises(InvalidSourceError, match="priority"):
            validate_source(_make_source(priority=-1))

    def test_validate_source_bad_url(self) -> None:
        with pytest.raises(InvalidSourceError, match="url must start with"):
            validate_source(_make_source(url="ftp://bad.url"))

    def test_validate_source_bad_rss_feed(self) -> None:
        with pytest.raises(InvalidSourceError, match="rss_feed must start with"):
            validate_source(_make_source(rss_feed="ftp://bad.feed"))

    def test_validate_source_bad_api_endpoint(self) -> None:
        with pytest.raises(InvalidSourceError, match="api_endpoint must start with"):
            validate_source(_make_source(api_endpoint="ftp://bad.api"))

    def test_validate_source_empty_url_ok(self) -> None:
        validate_source(_make_source(url=""))

    def test_validate_source_id_valid(self) -> None:
        validate_source_id("valid-id")

    def test_validate_source_id_empty(self) -> None:
        with pytest.raises(InvalidSourceError):
            validate_source_id("")

    def test_validate_trust_score_valid(self) -> None:
        validate_trust_score(0.5)

    def test_validate_trust_score_invalid(self) -> None:
        with pytest.raises(InvalidSourceError):
            validate_trust_score(-0.1)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class TestRegistry:
    @pytest.fixture
    def registry(self) -> TrustedKnowledgeRegistry:
        return TrustedKnowledgeRegistry()

    def test_register_and_lookup(self, registry: TrustedKnowledgeRegistry) -> None:
        s = _make_source()
        registry.register_source(s)
        found = registry.lookup("test-source")
        assert found.id == "test-source"

    def test_register_duplicate_raises(self, registry: TrustedKnowledgeRegistry) -> None:
        s = _make_source()
        registry.register_source(s)
        with pytest.raises(DuplicateSourceError, match="already registered"):
            registry.register_source(s)

    def test_register_duplicate_different_name(self, registry: TrustedKnowledgeRegistry) -> None:
        s1 = _make_source(source_id="dup")
        s2 = _make_source(source_id="dup", name="Other")
        registry.register_source(s1)
        with pytest.raises(DuplicateSourceError):
            registry.register_source(s2)

    def test_lookup_not_found_raises(self, registry: TrustedKnowledgeRegistry) -> None:
        with pytest.raises(SourceNotFoundError, match="not found"):
            registry.lookup("nonexistent")

    def test_remove_source(self, registry: TrustedKnowledgeRegistry) -> None:
        s = _make_source()
        registry.register_source(s)
        registry.remove_source("test-source")
        assert registry.lookup_by_type(SourceType.DOCUMENTATION) == []

    def test_remove_not_found_raises(self, registry: TrustedKnowledgeRegistry) -> None:
        with pytest.raises(SourceNotFoundError):
            registry.remove_source("nonexistent")

    def test_lookup_by_type(self, registry: TrustedKnowledgeRegistry) -> None:
        registry.register_source(_make_source(source_id="a", source_type=SourceType.GITHUB))
        registry.register_source(_make_source(source_id="b", source_type=SourceType.GITHUB))
        registry.register_source(_make_source(source_id="c", source_type=SourceType.YOUTUBE))
        results = registry.lookup_by_type(SourceType.GITHUB)
        assert len(results) == 2

    def test_lookup_by_category(self, registry: TrustedKnowledgeRegistry) -> None:
        registry.register_source(_make_source(source_id="a", category=Category.LLM))
        registry.register_source(_make_source(source_id="b", category=Category.LLM))
        registry.register_source(_make_source(source_id="c", category=Category.AGENTS))
        results = registry.lookup_by_category(Category.LLM)
        assert len(results) == 2

    def test_lookup_by_capability(self, registry: TrustedKnowledgeRegistry) -> None:
        caps_a = frozenset([Capability.DOCUMENTATION, Capability.RELEASES])
        caps_b = frozenset([Capability.RELEASES])
        registry.register_source(_make_source(source_id="a", capabilities=caps_a))
        registry.register_source(_make_source(source_id="b", capabilities=caps_b))
        results = registry.lookup_by_capability(Capability.DOCUMENTATION)
        assert len(results) == 1

    def test_lookup_by_tag(self, registry: TrustedKnowledgeRegistry) -> None:
        registry.register_source(_make_source(source_id="a", tags=frozenset(["llm"])))
        registry.register_source(_make_source(source_id="b", tags=frozenset(["rag"])))
        registry.register_source(_make_source(source_id="c", tags=frozenset(["llm", "api"])))
        results = registry.lookup_by_tag("llm")
        assert len(results) == 2

    def test_lookup_enabled(self, registry: TrustedKnowledgeRegistry) -> None:
        registry.register_source(_make_source(source_id="a", enabled=True))
        registry.register_source(_make_source(source_id="b", enabled=False))
        registry.register_source(_make_source(source_id="c", enabled=True))
        results = registry.lookup_enabled()
        assert len(results) == 2

    def test_discover(self, registry: TrustedKnowledgeRegistry) -> None:
        s = _make_source(source_id="disc")
        registry.register_source(s)
        found = registry.discover("disc")
        assert found.id == "disc"

    def test_discover_not_found_raises(self, registry: TrustedKnowledgeRegistry) -> None:
        with pytest.raises(SourceNotFoundError):
            registry.discover("bad")

    def test_statistics_empty(self, registry: TrustedKnowledgeRegistry) -> None:
        stats = registry.statistics()
        assert stats["total"] == 0
        assert stats["enabled"] == 0

    def test_statistics_with_sources(self, registry: TrustedKnowledgeRegistry) -> None:
        registry.register_source(_make_source(source_id="a", source_type=SourceType.GITHUB, enabled=True))
        registry.register_source(_make_source(source_id="b", source_type=SourceType.YOUTUBE, enabled=False))
        registry.register_source(_make_source(source_id="c", source_type=SourceType.GITHUB, enabled=True))
        stats = registry.statistics()
        assert stats["total"] == 3
        assert stats["enabled"] == 2
        assert stats["by_type"]["github"] == 2
        assert stats["by_type"]["youtube"] == 1

    def test_register_invalid_source_raises(self, registry: TrustedKnowledgeRegistry) -> None:
        with pytest.raises(InvalidSourceError):
            registry.register_source(_make_source(source_id="", name=""))


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class TestService:
    @pytest.fixture
    def registry(self) -> TrustedKnowledgeRegistry:
        return TrustedKnowledgeRegistry()

    @pytest.fixture
    def service(self, registry: TrustedKnowledgeRegistry) -> TrustedKnowledgeService:
        return TrustedKnowledgeService(registry)

    def test_load_seed_data(self, service: TrustedKnowledgeService) -> None:
        count = service.load_seed_data()
        assert count > 50
        stats = service.statistics()
        assert stats["total"] == count

    def test_load_seed_data_idempotent(self, service: TrustedKnowledgeService) -> None:
        first = service.load_seed_data()
        assert first > 0
        second = service.load_seed_data()
        assert second == 0

    def test_register(self, service: TrustedKnowledgeService) -> None:
        s = _make_source(source_id="new-source")
        service.register(s)
        found = service.lookup("new-source")
        assert found.name == "Test Source"

    def test_remove(self, service: TrustedKnowledgeService) -> None:
        service.register(_make_source(source_id="to-remove"))
        service.remove("to-remove")
        with pytest.raises(SourceNotFoundError):
            service.lookup("to-remove")

    def test_enable(self, service: TrustedKnowledgeService) -> None:
        service.register(_make_source(source_id="dis", enabled=False))
        service.enable("dis")
        assert service.lookup("dis").enabled is True

    def test_enable_already_enabled(self, service: TrustedKnowledgeService) -> None:
        service.register(_make_source(source_id="en", enabled=True))
        service.enable("en")
        assert service.lookup("en").enabled is True

    def test_disable(self, service: TrustedKnowledgeService) -> None:
        service.register(_make_source(source_id="en2", enabled=True))
        service.disable("en2")
        assert service.lookup("en2").enabled is False

    def test_disable_already_disabled(self, service: TrustedKnowledgeService) -> None:
        service.register(_make_source(source_id="dis2", enabled=False))
        service.disable("dis2")
        assert service.lookup("dis2").enabled is False

    def test_update_trust_score(self, service: TrustedKnowledgeService) -> None:
        service.register(_make_source(source_id="score-test", trust_score=0.5))
        updated = service.update_trust_score("score-test", 0.95)
        assert updated.trust_score == 0.95
        assert service.lookup("score-test").trust_score == 0.95

    def test_update_trust_score_invalid(self, service: TrustedKnowledgeService) -> None:
        service.register(_make_source(source_id="bad-score"))
        with pytest.raises(InvalidSourceError):
            service.update_trust_score("bad-score", 2.0)

    def test_find_sources_all_enabled(self, service: TrustedKnowledgeService) -> None:
        service.register(_make_source(source_id="a", enabled=True))
        service.register(_make_source(source_id="b", enabled=False))
        results = service.find_sources()
        assert len(results) == 1

    def test_find_sources_by_type(self, service: TrustedKnowledgeService) -> None:
        service.register(_make_source(source_id="a", source_type=SourceType.BLOG))
        service.register(_make_source(source_id="b", source_type=SourceType.GITHUB))
        results = service.find_sources(source_type=SourceType.BLOG)
        assert len(results) == 1

    def test_find_sources_by_category(self, service: TrustedKnowledgeService) -> None:
        service.register(_make_source(source_id="a", category=Category.TOOLING))
        service.register(_make_source(source_id="b", category=Category.LLM))
        results = service.find_sources(category=Category.TOOLING)
        assert len(results) == 1

    def test_find_sources_by_capability(self, service: TrustedKnowledgeService) -> None:
        caps = frozenset([Capability.DOCUMENTATION])
        service.register(_make_source(source_id="a", capabilities=caps))
        service.register(_make_source(source_id="b"))
        results = service.find_sources(capability=Capability.DOCUMENTATION)
        assert len(results) == 1

    def test_find_sources_by_tag(self, service: TrustedKnowledgeService) -> None:
        service.register(_make_source(source_id="a", tags=frozenset(["llm"])))
        service.register(_make_source(source_id="b", tags=frozenset(["rag"])))
        results = service.find_sources(tag="llm")
        assert len(results) == 1

    def test_find_sources_disabled_include(self, service: TrustedKnowledgeService) -> None:
        service.register(_make_source(source_id="a", enabled=True))
        service.register(_make_source(source_id="b", enabled=False))
        results = service.find_sources(enabled_only=False)
        assert len(results) == 2

    def test_find_by_capability(self, service: TrustedKnowledgeService) -> None:
        caps = frozenset([Capability.VIDEOS])
        service.register(_make_source(source_id="a", capabilities=caps))
        results = service.find_by_capability(Capability.VIDEOS)
        assert len(results) == 1

    def test_find_by_category(self, service: TrustedKnowledgeService) -> None:
        service.register(_make_source(source_id="a", category=Category.AGENTS))
        results = service.find_by_category(Category.AGENTS)
        assert len(results) == 1

    def test_find_by_tags(self, service: TrustedKnowledgeService) -> None:
        service.register(_make_source(source_id="a", tags=frozenset(["llm", "api"])))
        service.register(_make_source(source_id="b", tags=frozenset(["llm"])))
        results = service.find_by_tags(["llm", "api"])
        assert len(results) == 1

    def test_statistics(self, service: TrustedKnowledgeService) -> None:
        service.register(_make_source(source_id="a"))
        stats = service.statistics()
        assert stats["total"] == 1


# ---------------------------------------------------------------------------
# Seed Data
# ---------------------------------------------------------------------------

class TestSeedData:
    def test_get_seed_sources_returns_list(self) -> None:
        sources = get_seed_sources()
        assert isinstance(sources, list)
        assert len(sources) > 0

    def test_seed_sources_have_unique_ids(self) -> None:
        sources = get_seed_sources()
        ids = [s.id for s in sources]
        assert len(ids) == len(set(ids))

    def test_seed_sources_all_valid(self) -> None:
        for s in get_seed_sources():
            validate_source(s)

    def test_seed_sources_all_source_types(self) -> None:
        sources = get_seed_sources()
        types = {s.source_type for s in sources}
        for st in SourceType:
            assert st in types, f"missing source type: {st}"

    def test_seed_categories(self) -> None:
        sources = get_seed_sources()
        for s in sources:
            assert isinstance(s.category, Category), f"source {s.id}: invalid category {s.category}"

    def test_seed_trust_scores_in_range(self) -> None:
        for s in get_seed_sources():
            assert 0.0 <= s.trust_score <= 1.0, f"source {s.id}: trust_score {s.trust_score} out of range"


# ---------------------------------------------------------------------------
# DI Registration
# ---------------------------------------------------------------------------

class TestDIRegistration:
    def test_register_trusted_sources(self) -> None:
        from aicos.core.di import Container
        from aicos.settings import Settings
        container = Container()
        settings = Settings()
        register_trusted_sources(container, settings)
        registry = container.resolve(TrustedKnowledgeRegistry)
        assert isinstance(registry, TrustedKnowledgeRegistry)
        service = container.resolve(TrustedKnowledgeService)
        assert isinstance(service, TrustedKnowledgeService)


# ---------------------------------------------------------------------------
# Exception Hierarchy
# ---------------------------------------------------------------------------

class TestExceptionHierarchy:
    def test_all_inherit_base(self) -> None:
        assert issubclass(DuplicateSourceError, TrustedSourceError)
        assert issubclass(InvalidTrustScoreError, TrustedSourceError)
        assert issubclass(InvalidSourceError, TrustedSourceError)
        assert issubclass(SourceNotFoundError, TrustedSourceError)

    def test_base_catch(self) -> None:
        registry = TrustedKnowledgeRegistry()
        with pytest.raises(TrustedSourceError):
            registry.lookup("nonexistent")
