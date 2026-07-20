"""Tests for the provider infrastructure."""

from __future__ import annotations

from datetime import datetime

import pytest

from aicos.providers.exceptions import (
    ProviderConfigurationError,
    ProviderError,
    ProviderExecutionError,
    ProviderRegistrationError,
    ProviderUnavailableError,
)
from aicos.providers.interfaces import (
    GitHubProviderProtocol,
    OfficialDocsProviderProtocol,
    ProviderProtocol,
    ResearchProviderProtocol,
    SearchProviderProtocol,
    YouTubeProviderProtocol,
)
from aicos.providers.models import (
    ProviderConfiguration,
    ProviderHealth,
    ProviderStatistics,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from aicos.providers.providers import (
    DuckDuckGoSearchProvider,
    GitHubProvider,
    GoogleSearchProvider,
    MCPSearchProvider,
    OfficialDocsProvider,
    Provider,
    ResearchProvider,
    SearchProvider,
    YouTubeProvider,
)
from aicos.providers.providers.base import Provider as ProviderBase
from aicos.providers.registry import ProviderRegistry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def registry() -> ProviderRegistry:
    return ProviderRegistry()


@pytest.fixture
def mcp_search() -> MCPSearchProvider:
    return MCPSearchProvider()


@pytest.fixture
def google_search() -> GoogleSearchProvider:
    return GoogleSearchProvider()


@pytest.fixture
def duckduckgo_search() -> DuckDuckGoSearchProvider:
    return DuckDuckGoSearchProvider()


@pytest.fixture
def github() -> GitHubProvider:
    return GitHubProvider()


@pytest.fixture
def youtube() -> YouTubeProvider:
    return YouTubeProvider()


@pytest.fixture
def research() -> ResearchProvider:
    return ResearchProvider()


@pytest.fixture
def official_docs() -> OfficialDocsProvider:
    return OfficialDocsProvider()


@pytest.fixture
def populated_registry(
    mcp_search: MCPSearchProvider,
    google_search: GoogleSearchProvider,
    duckduckgo_search: DuckDuckGoSearchProvider,
    github: GitHubProvider,
    youtube: YouTubeProvider,
    research: ResearchProvider,
    official_docs: OfficialDocsProvider,
) -> ProviderRegistry:
    reg = ProviderRegistry()
    reg.register(mcp_search)
    reg.register(google_search)
    reg.register(duckduckgo_search)
    reg.register(github)
    reg.register(youtube)
    reg.register(research)
    reg.register(official_docs)
    return reg


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestProviderConfiguration:
    def test_defaults(self) -> None:
        c = ProviderConfiguration(name="test", provider_type="search")
        assert c.config == {}
        assert c.enabled is True

    def test_frozen(self) -> None:
        c = ProviderConfiguration(name="t", provider_type="s")
        with pytest.raises(AttributeError):
            c.name = "new"  # type: ignore[misc]


class TestProviderHealth:
    def test_defaults(self) -> None:
        h = ProviderHealth(provider_name="test")
        assert h.healthy is True
        assert h.message == ""
        assert h.response_time_ms == 0.0

    def test_frozen(self) -> None:
        h = ProviderHealth(provider_name="t")
        with pytest.raises(AttributeError):
            h.healthy = False  # type: ignore[misc]


class TestSearchRequest:
    def test_defaults(self) -> None:
        r = SearchRequest(query="python")
        assert r.max_results == 10
        assert r.filters == {}

    def test_frozen(self) -> None:
        r = SearchRequest(query="q")
        with pytest.raises(AttributeError):
            r.query = "new"  # type: ignore[misc]


class TestSearchResult:
    def test_defaults(self) -> None:
        r = SearchResult(title="Result")
        assert r.url == ""
        assert r.snippet == ""
        assert r.relevance_score == 0.0

    def test_frozen(self) -> None:
        r = SearchResult(title="T")
        with pytest.raises(AttributeError):
            r.title = "new"  # type: ignore[misc]


class TestSearchResponse:
    def test_defaults(self) -> None:
        r = SearchResponse(query="python")
        assert r.results == []
        assert r.total_estimated == 0
        assert r.duration_ms == 0.0

    def test_frozen(self) -> None:
        r = SearchResponse(query="q")
        with pytest.raises(AttributeError):
            r.query = "new"  # type: ignore[misc]


class TestProviderStatistics:
    def test_defaults(self) -> None:
        s = ProviderStatistics()
        assert s.total_requests == 0
        assert s.total_errors == 0

    def test_frozen(self) -> None:
        s = ProviderStatistics()
        with pytest.raises(AttributeError):
            s.total_requests = 1  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Provider contract tests
# ---------------------------------------------------------------------------


class TestBaseProvider:
    def test_base_class_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            ProviderBase()  # type: ignore[abstract]


class TestProviderProtocolConformance:
    def test_mcp_search_conforms(self) -> None:
        assert isinstance(MCPSearchProvider(), ProviderProtocol)
        assert isinstance(MCPSearchProvider(), SearchProviderProtocol)

    def test_google_search_conforms(self) -> None:
        assert isinstance(GoogleSearchProvider(), ProviderProtocol)
        assert isinstance(GoogleSearchProvider(), SearchProviderProtocol)

    def test_duckduckgo_search_conforms(self) -> None:
        assert isinstance(DuckDuckGoSearchProvider(), ProviderProtocol)
        assert isinstance(DuckDuckGoSearchProvider(), SearchProviderProtocol)

    def test_github_conforms(self) -> None:
        assert isinstance(GitHubProvider(), ProviderProtocol)
        assert isinstance(GitHubProvider(), GitHubProviderProtocol)

    def test_youtube_conforms(self) -> None:
        assert isinstance(YouTubeProvider(), ProviderProtocol)
        assert isinstance(YouTubeProvider(), YouTubeProviderProtocol)

    def test_research_conforms(self) -> None:
        assert isinstance(ResearchProvider(), ProviderProtocol)
        assert isinstance(ResearchProvider(), ResearchProviderProtocol)

    def test_official_docs_conforms(self) -> None:
        assert isinstance(OfficialDocsProvider(), ProviderProtocol)
        assert isinstance(OfficialDocsProvider(), OfficialDocsProviderProtocol)


# ---------------------------------------------------------------------------
# Search provider tests
# ---------------------------------------------------------------------------


class TestMCPSearchProvider:
    def test_initialize(self) -> None:
        MCPSearchProvider().initialize()

    def test_shutdown(self) -> None:
        MCPSearchProvider().shutdown()

    def test_health(self) -> None:
        h = MCPSearchProvider().health()
        assert h.provider_name == "mcp_search"
        assert h.healthy is True

    def test_capabilities(self) -> None:
        caps = MCPSearchProvider().capabilities()
        assert "search" in caps
        assert "suggest" in caps

    def test_search(self) -> None:
        req = SearchRequest(query="python")
        resp = MCPSearchProvider().search(req)
        assert len(resp.results) == 1
        assert "MCP" in resp.results[0].title

    def test_suggest(self) -> None:
        suggestions = MCPSearchProvider().suggest("python")
        assert len(suggestions) == 3


class TestGoogleSearchProvider:
    def test_initialize(self) -> None:
        GoogleSearchProvider().initialize()

    def test_shutdown(self) -> None:
        GoogleSearchProvider().shutdown()

    def test_health(self) -> None:
        h = GoogleSearchProvider().health()
        assert h.provider_name == "google_search"
        assert h.healthy is True

    def test_capabilities(self) -> None:
        caps = GoogleSearchProvider().capabilities()
        assert "search" in caps

    def test_search(self) -> None:
        req = SearchRequest(query="python")
        resp = GoogleSearchProvider().search(req)
        assert "Google" in resp.results[0].title

    def test_search_with_config(self) -> None:
        p = GoogleSearchProvider(config={"api_key": "test"})
        req = SearchRequest(query="python")
        resp = p.search(req)
        assert resp.query == "python"

    def test_suggest(self) -> None:
        suggestions = GoogleSearchProvider().suggest("python")
        assert len(suggestions) == 3


class TestDuckDuckGoSearchProvider:
    def test_initialize(self) -> None:
        DuckDuckGoSearchProvider().initialize()

    def test_shutdown(self) -> None:
        DuckDuckGoSearchProvider().shutdown()

    def test_health(self) -> None:
        h = DuckDuckGoSearchProvider().health()
        assert h.provider_name == "duckduckgo_search"
        assert h.healthy is True

    def test_search(self) -> None:
        req = SearchRequest(query="python")
        resp = DuckDuckGoSearchProvider().search(req)
        assert "DuckDuckGo" in resp.results[0].title

    def test_suggest(self) -> None:
        suggestions = DuckDuckGoSearchProvider().suggest("python")
        assert len(suggestions) >= 1


# ---------------------------------------------------------------------------
# Non-search provider tests
# ---------------------------------------------------------------------------


class TestGitHubProvider:
    def test_initialize_and_shutdown(self) -> None:
        p = GitHubProvider()
        p.initialize()
        p.shutdown()

    def test_health(self) -> None:
        h = GitHubProvider().health()
        assert h.provider_name == "github"
        assert h.healthy is True

    def test_capabilities(self) -> None:
        caps = GitHubProvider().capabilities()
        assert "repository_search" in caps


class TestYouTubeProvider:
    def test_initialize_and_shutdown(self) -> None:
        p = YouTubeProvider()
        p.initialize()
        p.shutdown()

    def test_health(self) -> None:
        h = YouTubeProvider().health()
        assert h.provider_name == "youtube"
        assert h.healthy is True

    def test_capabilities(self) -> None:
        caps = YouTubeProvider().capabilities()
        assert "video_search" in caps


class TestResearchProvider:
    def test_initialize_and_shutdown(self) -> None:
        p = ResearchProvider()
        p.initialize()
        p.shutdown()

    def test_health(self) -> None:
        h = ResearchProvider().health()
        assert h.healthy is True

    def test_capabilities(self) -> None:
        caps = ResearchProvider().capabilities()
        assert "paper_search" in caps


class TestOfficialDocsProvider:
    def test_initialize_and_shutdown(self) -> None:
        p = OfficialDocsProvider()
        p.initialize()
        p.shutdown()

    def test_health(self) -> None:
        h = OfficialDocsProvider().health()
        assert h.healthy is True

    def test_capabilities(self) -> None:
        caps = OfficialDocsProvider().capabilities()
        assert "doc_search" in caps


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


class TestProviderRegistry:
    def test_register(self, registry: ProviderRegistry) -> None:
        registry.register(MCPSearchProvider())
        assert registry.count == 1

    def test_lookup(self, registry: ProviderRegistry) -> None:
        p = MCPSearchProvider()
        registry.register(p)
        found = registry.lookup("mcp_search")
        assert found is p

    def test_lookup_missing_returns_none(self, registry: ProviderRegistry) -> None:
        found = registry.lookup("nonexistent")
        assert found is None

    def test_discover(self, registry: ProviderRegistry) -> None:
        p = GitHubProvider()
        registry.register(p)
        found = registry.discover("github")
        assert found is p

    def test_discover_missing_raises(self, registry: ProviderRegistry) -> None:
        with pytest.raises(ProviderRegistrationError, match="no provider registered"):
            registry.discover("nonexistent")

    def test_duplicate_registration_raises(self, registry: ProviderRegistry) -> None:
        registry.register(MCPSearchProvider())
        with pytest.raises(ProviderRegistrationError, match="already registered"):
            registry.register(MCPSearchProvider())

    def test_lookup_by_capability(self, populated_registry: ProviderRegistry) -> None:
        providers = populated_registry.lookup_by_capability("search")
        assert len(providers) == 3
        assert all("search" in p.capabilities() for p in providers)

    def test_lookup_by_capability_no_match(self, registry: ProviderRegistry) -> None:
        providers = registry.lookup_by_capability("nonexistent")
        assert providers == []

    def test_registered_names(self, populated_registry: ProviderRegistry) -> None:
        names = populated_registry.registered_names
        assert "mcp_search" in names
        assert "github" in names
        assert "youtube" in names

    def test_registered_providers(self, populated_registry: ProviderRegistry) -> None:
        providers = populated_registry.registered_providers
        assert len(providers) == 7

    def test_count(self, registry: ProviderRegistry) -> None:
        assert registry.count == 0
        registry.register(MCPSearchProvider())
        assert registry.count == 1

    def test_register_non_protocol_raises(self, registry: ProviderRegistry) -> None:
        with pytest.raises(ProviderRegistrationError, match="does not implement"):
            registry.register("not_a_provider")  # type: ignore[arg-type]

    def test_resolve_name_fallback(self, registry: ProviderRegistry) -> None:
        class NamelessProvider:
            def initialize(self) -> None: pass
            def shutdown(self) -> None: pass
            def health(self) -> ProviderHealth:
                return ProviderHealth(provider_name="nameless")
            def capabilities(self) -> list[str]: return []
        registry.register(NamelessProvider())  # type: ignore[arg-type]
        found = registry.lookup("NamelessProvider")
        assert found is not None


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class TestExceptionHierarchy:
    def test_base_type(self) -> None:
        assert issubclass(ProviderRegistrationError, ProviderError)
        assert issubclass(ProviderExecutionError, ProviderError)
        assert issubclass(ProviderConfigurationError, ProviderError)
        assert issubclass(ProviderUnavailableError, ProviderError)


# ---------------------------------------------------------------------------
# DI registration
# ---------------------------------------------------------------------------


class TestDependencyInjection:
    def test_register_function_exists(self) -> None:
        from aicos.providers import register_providers
        assert callable(register_providers)
