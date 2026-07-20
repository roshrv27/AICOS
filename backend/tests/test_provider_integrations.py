from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from datetime import datetime
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from aicos.providers.exceptions import (
    ProviderConfigurationError,
    ProviderExecutionError,
    ProviderUnavailableError,
)
from aicos.providers.integrations import (
    ArxivIntegration,
    DuckDuckGoIntegration,
    GitHubIntegration,
    GoogleSearchIntegration,
    MCPSearchIntegration,
    OfficialDocsIntegration,
    SourceTrustPolicy,
    YouTubeIntegration,
)
from aicos.providers.integrations.trust import SourceTrustPolicy
from aicos.providers.models import (
    ProviderHealth,
    ProviderSettings,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from aicos.knowledge_intelligence.models import (
    KnowledgeSource,
    KnowledgeVersion,
    TechnologySignal,
    KnowledgeResource,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_urlopen(status: int = 200, data: str = "{}", headers: dict | None = None):
    """Return a mock ``urlopen`` that returns the given status and data."""
    bio = BytesIO(data.encode("utf-8"))
    cm = MagicMock()
    cm.__enter__.return_value = cm
    cm.status = status
    cm.read.return_value = bio.read()
    if headers:
        cm.headers = headers
    else:
        cm.headers = {}
    return cm


ARXIV_XML = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2201.00001</id>
    <title>Test Paper Title</title>
    <summary>This is a test abstract</summary>
    <published>2023-01-15T00:00:00Z</published>
  </entry>
</feed>"""

GITHUB_REPOS = {
    "items": [
        {
            "id": 12345,
            "full_name": "test/repo",
            "name": "repo",
            "html_url": "https://github.com/test/repo",
            "stargazers_count": 5000,
            "description": "A test repo",
        }
    ]
}

GITHUB_RELEASES = [
    {
        "id": 67890,
        "tag_name": "v1.0.0",
        "name": "Version 1.0.0",
        "html_url": "https://github.com/test/repo/releases/v1.0.0",
        "published_at": "2023-06-01T00:00:00Z",
    }
]

GITHUB_TOPICS = {
    "items": [
        {
            "name": "machine-learning",
            "description": "ML topic",
            "url": "https://github.com/topics/machine-learning",
            "score": 95,
        }
    ]
}

YOUTUBE_RESPONSE = {
    "items": [
        {
            "id": {"videoId": "abc123", "channelId": "chan456", "playlistId": "pl789"},
            "snippet": {
                "title": "Test Video",
                "publishedAt": "2023-06-15T00:00:00Z",
            },
        }
    ]
}

DOCS_RESPONSE = {
    "docs": [
        {
            "id": "getting-started",
            "title": "Getting Started",
            "url": "https://docs.example.com/getting-started",
            "updated_at": "2023-06-01T00:00:00Z",
        }
    ],
    "versions": [
        {
            "version": "1.0.0",
            "release_date": "2023-06-01T00:00:00Z",
            "changes": ["Initial release"],
        }
    ],
}

DDG_RESPONSE = json.dumps({
    "AbstractText": "Test result",
    "AbstractURL": "https://example.com",
    "Heading": "Test",
    "RelatedTopics": [],
})

DDG_SUGGEST = json.dumps([{"phrase": "test query"}])

MCP_SEARCH = json.dumps({
    "results": [
        {
            "title": "MCP Result",
            "url": "https://mcp.example.com/result",
            "snippet": "A result from MCP",
            "relevance": 0.95,
        }
    ]
})

MCP_SUGGEST = json.dumps(["test mcp", "test mcp tutorial"])

GOOGLE_SEARCH = json.dumps({
    "items": [
        {
            "title": "Google Result",
            "link": "https://google.example.com/result",
            "snippet": "A result from Google",
            "pagemap": {
                "metatags": [
                    {"article:published_time": "2023-06-01T00:00:00Z"}
                ]
            },
        }
    ]
})

GOOGLE_SUGGEST = json.dumps(["python", ["test google", "test tutorial"]])


# ---------------------------------------------------------------------------
# SourceTrustPolicy
# ---------------------------------------------------------------------------

class TestSourceTrustPolicy:
    def test_default_weights(self) -> None:
        p = SourceTrustPolicy()
        assert p.get_weight("OFFICIAL_DOCUMENTATION") == 1.00
        assert p.get_weight("X") == 0.40
        assert p.get_weight("UNKNOWN") == 0.5

    def test_custom_weights(self) -> None:
        p = SourceTrustPolicy(weights={"MY_SOURCE": 0.75})
        assert p.get_weight("MY_SOURCE") == 0.75

    def test_set_weight(self) -> None:
        p = SourceTrustPolicy()
        p.set_weight("X", 0.60)
        assert p.get_weight("X") == 0.60

    def test_set_weight_invalid_raises(self) -> None:
        p = SourceTrustPolicy()
        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            p.set_weight("X", 1.5)

    def test_weights_property_returns_copy(self) -> None:
        p = SourceTrustPolicy()
        w = p.weights
        w["X"] = 1.0
        assert p.get_weight("X") == 0.40

    def test_to_dict(self) -> None:
        p = SourceTrustPolicy()
        d = p.to_dict()
        assert d["OFFICIAL_DOCUMENTATION"] == 1.00
        assert d["X"] == 0.40

    def test_from_dict(self) -> None:
        p = SourceTrustPolicy.from_dict({"MY_SOURCE": 0.88})
        assert p.get_weight("MY_SOURCE") == 0.88

    def test_constructor_validates(self) -> None:
        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            SourceTrustPolicy(weights={"BAD": -0.1})


# ---------------------------------------------------------------------------
# ProviderSettings
# ---------------------------------------------------------------------------

class TestProviderSettings:
    def test_defaults(self) -> None:
        s = ProviderSettings()
        assert s.retry_count == 3
        assert "github" in s.enabled_providers

    def test_custom_timeout(self) -> None:
        s = ProviderSettings(timeouts={"github": 120})
        assert s.timeouts["github"] == 120


# ---------------------------------------------------------------------------
# MCPSearchIntegration
# ---------------------------------------------------------------------------

class TestMCPSearchIntegration:
    @patch("urllib.request.urlopen")
    def test_search(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(data=MCP_SEARCH)
        p = MCPSearchIntegration({"endpoint": "https://mcp.example.com/api"})
        p.initialize()
        resp = p.search(SearchRequest(query="python", max_results=5))
        assert isinstance(resp, SearchResponse)
        assert resp.query == "python"
        assert len(resp.results) == 1
        assert resp.results[0].title == "MCP Result"

    @patch("urllib.request.urlopen")
    def test_suggest(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(data=MCP_SUGGEST)
        p = MCPSearchIntegration()
        p.initialize()
        suggestions = p.suggest("python")
        assert len(suggestions) == 2
        assert suggestions[0] == "test mcp"

    def test_suggest_fallback_on_error(self) -> None:
        p = MCPSearchIntegration()
        p.initialize()
        suggestions = p.suggest("python")
        assert len(suggestions) > 0

    def test_health_healthy(self) -> None:
        p = MCPSearchIntegration()
        p.initialize()
        h = p.health()
        assert h.healthy is True

    def test_health_unhealthy_when_not_initialized(self) -> None:
        p = MCPSearchIntegration()
        h = p.health()
        assert h.healthy is False

    def test_capabilities(self) -> None:
        p = MCPSearchIntegration()
        assert "search" in p.capabilities()

    def test_provider_name(self) -> None:
        p = MCPSearchIntegration()
        assert p.provider_name == "mcp_search"

    def test_initialize_and_shutdown(self) -> None:
        p = MCPSearchIntegration()
        p.initialize()
        p.shutdown()

    @patch("urllib.request.urlopen")
    def test_search_http_error(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(status=500)
        p = MCPSearchIntegration()
        p.initialize()
        with pytest.raises(ProviderExecutionError):
            p.search(SearchRequest(query="test"))

    @patch("urllib.request.urlopen")
    def test_unavailable_error(self, mock_urlopen) -> None:
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("connection refused")
        p = MCPSearchIntegration()
        p.initialize()
        with pytest.raises(ProviderUnavailableError):
            p.search(SearchRequest(query="test"))


# ---------------------------------------------------------------------------
# GoogleSearchIntegration
# ---------------------------------------------------------------------------

class TestGoogleSearchIntegration:
    @patch("urllib.request.urlopen")
    def test_search(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(data=GOOGLE_SEARCH)
        p = GoogleSearchIntegration()
        p.initialize()
        resp = p.search(SearchRequest(query="python"))
        assert len(resp.results) == 1
        assert resp.results[0].source == "google"

    @patch("urllib.request.urlopen")
    def test_suggest(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(data=GOOGLE_SUGGEST)
        p = GoogleSearchIntegration()
        p.initialize()
        suggestions = p.suggest("python")
        assert len(suggestions) == 2

    @patch("urllib.request.urlopen")
    def test_suggest_fallback(self, mock_urlopen) -> None:
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("timeout")
        p = GoogleSearchIntegration()
        p.initialize()
        suggestions = p.suggest("python")
        assert "python google" in suggestions

    def test_health(self) -> None:
        p = GoogleSearchIntegration()
        p.initialize()
        assert p.health().healthy is True

    def test_provider_name(self) -> None:
        assert GoogleSearchIntegration().provider_name == "google_search"

    def test_capabilities(self) -> None:
        assert "search" in GoogleSearchIntegration().capabilities()

    @patch("urllib.request.urlopen")
    def test_search_unavailable(self, mock_urlopen) -> None:
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("timeout")
        p = GoogleSearchIntegration()
        p.initialize()
        with pytest.raises(ProviderUnavailableError):
            p.search(SearchRequest(query="test"))


# ---------------------------------------------------------------------------
# DuckDuckGoIntegration
# ---------------------------------------------------------------------------

class TestDuckDuckGoIntegration:
    @patch("urllib.request.urlopen")
    def test_search(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(data=DDG_RESPONSE)
        p = DuckDuckGoIntegration()
        p.initialize()
        resp = p.search(SearchRequest(query="python"))
        assert len(resp.results) >= 1
        assert resp.results[0].source == "duckduckgo"

    @patch("urllib.request.urlopen")
    def test_suggest(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(data=DDG_SUGGEST)
        p = DuckDuckGoIntegration()
        p.initialize()
        suggestions = p.suggest("python")
        assert len(suggestions) == 1

    @patch("urllib.request.urlopen")
    def test_suggest_fallback(self, mock_urlopen) -> None:
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("timeout")
        p = DuckDuckGoIntegration()
        p.initialize()
        suggestions = p.suggest("python")
        assert "python ddg" in suggestions

    def test_health(self) -> None:
        p = DuckDuckGoIntegration()
        p.initialize()
        assert p.health().healthy is True

    def test_provider_name(self) -> None:
        assert DuckDuckGoIntegration().provider_name == "duckduckgo_search"

    @patch("urllib.request.urlopen")
    def test_search_http_error(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(status=500)
        p = DuckDuckGoIntegration()
        p.initialize()
        with pytest.raises(ProviderExecutionError):
            p.search(SearchRequest(query="test"))


# ---------------------------------------------------------------------------
# GitHubIntegration
# ---------------------------------------------------------------------------

class TestGitHubIntegration:
    @patch("urllib.request.urlopen")
    def test_discover_repositories(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(data=json.dumps(GITHUB_REPOS))
        p = GitHubIntegration()
        p.initialize()
        sources = p.discover_repositories("python")
        assert len(sources) == 1
        assert sources[0].source_type.value == "github"
        assert "test/repo" in sources[0].name

    @patch("urllib.request.urlopen")
    def test_discover_releases(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(data=json.dumps(GITHUB_RELEASES))
        p = GitHubIntegration()
        p.initialize()
        sources = p.discover_releases("test", "repo")
        assert len(sources) == 1
        assert sources[0].name == "v1.0.0"

    @patch("urllib.request.urlopen")
    def test_search_topics(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(data=json.dumps(GITHUB_TOPICS))
        p = GitHubIntegration()
        p.initialize()
        signals = p.search_topics("ml")
        assert len(signals) == 1
        assert signals[0].name == "machine-learning"

    def test_health(self) -> None:
        p = GitHubIntegration()
        p.initialize()
        assert p.health().healthy is True

    def test_capabilities(self) -> None:
        p = GitHubIntegration()
        caps = p.capabilities()
        assert "repository_discovery" in caps
        assert "release_discovery" in caps
        assert "topic_search" in caps

    def test_provider_name(self) -> None:
        assert GitHubIntegration().provider_name == "github"

    @patch("urllib.request.urlopen")
    def test_http_error_403(self, mock_urlopen) -> None:
        import urllib.error
        exc = urllib.error.HTTPError("url", 403, "Forbidden", {}, None)
        mock_urlopen.side_effect = exc
        p = GitHubIntegration()
        p.initialize()
        with pytest.raises(ProviderUnavailableError, match="rate limit"):
            p.discover_repositories("python")

    @patch("urllib.request.urlopen")
    def test_http_error_404(self, mock_urlopen) -> None:
        import urllib.error
        exc = urllib.error.HTTPError("url", 404, "Not Found", {}, None)
        mock_urlopen.side_effect = exc
        p = GitHubIntegration()
        p.initialize()
        with pytest.raises(ProviderExecutionError, match="not found"):
            p.discover_releases("bad", "repo")

    @patch("urllib.request.urlopen")
    def test_http_error_generic(self, mock_urlopen) -> None:
        import urllib.error
        exc = urllib.error.HTTPError("url", 500, "Server Error", {}, None)
        mock_urlopen.side_effect = exc
        p = GitHubIntegration()
        p.initialize()
        with pytest.raises(ProviderExecutionError, match="500"):
            p.discover_repositories("python")


# ---------------------------------------------------------------------------
# YouTubeIntegration
# ---------------------------------------------------------------------------

class TestYouTubeIntegration:
    @patch("urllib.request.urlopen")
    def test_discover_videos(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(data=json.dumps(YOUTUBE_RESPONSE))
        p = YouTubeIntegration()
        p.initialize()
        resources = p.discover_videos("python")
        assert len(resources) == 1
        assert resources[0].resource_type.value == "video"
        assert "Test Video" in resources[0].title

    @patch("urllib.request.urlopen")
    def test_discover_channels(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(data=json.dumps(YOUTUBE_RESPONSE))
        p = YouTubeIntegration()
        p.initialize()
        sources = p.discover_channels("python")
        assert len(sources) == 1
        assert sources[0].source_type.value == "youtube"

    @patch("urllib.request.urlopen")
    def test_discover_playlists(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(data=json.dumps(YOUTUBE_RESPONSE))
        p = YouTubeIntegration()
        p.initialize()
        resources = p.discover_playlists("python")
        assert len(resources) == 1
        assert "playlist" in resources[0].url

    def test_health(self) -> None:
        p = YouTubeIntegration()
        p.initialize()
        assert p.health().healthy is True

    def test_capabilities(self) -> None:
        p = YouTubeIntegration()
        caps = p.capabilities()
        assert "video_discovery" in caps
        assert "channel_discovery" in caps
        assert "playlist_discovery" in caps

    def test_provider_name(self) -> None:
        assert YouTubeIntegration().provider_name == "youtube"

    @patch("urllib.request.urlopen")
    def test_quota_error(self, mock_urlopen) -> None:
        import urllib.error
        exc = urllib.error.HTTPError("url", 403, "Quota Exceeded", {}, None)
        mock_urlopen.side_effect = exc
        p = YouTubeIntegration()
        p.initialize()
        with pytest.raises(ProviderUnavailableError, match="quota"):
            p.discover_videos("python")

    @patch("urllib.request.urlopen")
    def test_unavailable(self, mock_urlopen) -> None:
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("down")
        p = YouTubeIntegration()
        p.initialize()
        with pytest.raises(ProviderUnavailableError):
            p.discover_videos("python")


# ---------------------------------------------------------------------------
# ArxivIntegration
# ---------------------------------------------------------------------------

class TestArxivIntegration:
    @patch("urllib.request.urlopen")
    def test_discover_papers(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(data=ARXIV_XML)
        p = ArxivIntegration()
        p.initialize()
        sources = p.discover_papers("machine learning")
        assert len(sources) == 1
        assert sources[0].source_type.value == "research_paper"

    @patch("urllib.request.urlopen")
    def test_author_lookup(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(data=ARXIV_XML)
        p = ArxivIntegration()
        p.initialize()
        sources = p.author_lookup("Smith")
        assert len(sources) == 1

    @patch("urllib.request.urlopen")
    def test_search_topics(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(data=ARXIV_XML)
        p = ArxivIntegration()
        p.initialize()
        signals = p.search_topics("cs.AI")
        assert len(signals) == 1
        assert isinstance(signals[0], TechnologySignal)

    def test_health(self) -> None:
        p = ArxivIntegration()
        p.initialize()
        assert p.health().healthy is True

    def test_capabilities(self) -> None:
        p = ArxivIntegration()
        caps = p.capabilities()
        assert "paper_discovery" in caps
        assert "author_lookup" in caps
        assert "topic_search" in caps

    def test_provider_name(self) -> None:
        assert ArxivIntegration().provider_name == "research"

    @patch("urllib.request.urlopen")
    def test_http_error(self, mock_urlopen) -> None:
        import urllib.error
        exc = urllib.error.HTTPError("url", 500, "Error", {}, None)
        mock_urlopen.side_effect = exc
        p = ArxivIntegration()
        p.initialize()
        with pytest.raises(ProviderExecutionError):
            p.discover_papers("test")

    def test_search_topics_empty(self) -> None:
        empty_xml = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
</feed>"""
        with patch("urllib.request.urlopen") as mock:
            mock.return_value = _mock_urlopen(data=empty_xml)
            p = ArxivIntegration()
            p.initialize()
            signals = p.search_topics("unknown")
            assert len(signals) == 0


# ---------------------------------------------------------------------------
# OfficialDocsIntegration
# ---------------------------------------------------------------------------

class TestOfficialDocsIntegration:
    @patch("urllib.request.urlopen")
    def test_lookup_documentation(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(data=json.dumps(DOCS_RESPONSE))
        p = OfficialDocsIntegration()
        p.initialize()
        sources = p.lookup_documentation("python")
        assert len(sources) == 1
        assert sources[0].source_type.value == "official_documentation"
        assert sources[0].credibility_score == 1.0

    @patch("urllib.request.urlopen")
    def test_discover_versions(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(data=json.dumps(DOCS_RESPONSE))
        p = OfficialDocsIntegration()
        p.initialize()
        versions = p.discover_versions("python")
        assert len(versions) == 1
        assert isinstance(versions[0], KnowledgeVersion)
        assert versions[0].version == "1.0.0"

    @patch("urllib.request.urlopen")
    def test_get_release_notes(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(data=json.dumps(DOCS_RESPONSE))
        p = OfficialDocsIntegration()
        p.initialize()
        sources = p.get_release_notes("python", "3.12")
        assert len(sources) == 1

    def test_health(self) -> None:
        p = OfficialDocsIntegration()
        p.initialize()
        assert p.health().healthy is True

    def test_capabilities(self) -> None:
        p = OfficialDocsIntegration()
        caps = p.capabilities()
        assert "documentation_lookup" in caps
        assert "version_discovery" in caps
        assert "release_notes" in caps

    def test_provider_name(self) -> None:
        assert OfficialDocsIntegration().provider_name == "official_docs"

    @patch("urllib.request.urlopen")
    def test_http_error(self, mock_urlopen) -> None:
        import urllib.error
        exc = urllib.error.HTTPError("url", 500, "Error", {}, None)
        mock_urlopen.side_effect = exc
        p = OfficialDocsIntegration()
        p.initialize()
        with pytest.raises(ProviderExecutionError):
            p.lookup_documentation("test")

    @patch("urllib.request.urlopen")
    def test_unavailable(self, mock_urlopen) -> None:
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("down")
        p = OfficialDocsIntegration()
        p.initialize()
        with pytest.raises(ProviderUnavailableError):
            p.lookup_documentation("test")


# ---------------------------------------------------------------------------
# Lifecycle tests for all integrations
# ---------------------------------------------------------------------------

class TestAllIntegrationsLifecycle:
    @pytest.mark.parametrize("cls", [
        MCPSearchIntegration,
        GoogleSearchIntegration,
        DuckDuckGoIntegration,
        GitHubIntegration,
        YouTubeIntegration,
        ArxivIntegration,
        OfficialDocsIntegration,
    ])
    def test_initialize_and_shutdown(self, cls) -> None:
        p = cls()
        p.initialize()
        p.shutdown()

    @pytest.mark.parametrize("cls", [
        MCPSearchIntegration,
        GoogleSearchIntegration,
        DuckDuckGoIntegration,
        GitHubIntegration,
        YouTubeIntegration,
        ArxivIntegration,
        OfficialDocsIntegration,
    ])
    def test_health_before_initialize(self, cls) -> None:
        p = cls()
        h = p.health()
        assert h.healthy is False

    @pytest.mark.parametrize("cls,expected", [
        (MCPSearchIntegration, "mcp_search"),
        (GoogleSearchIntegration, "google_search"),
        (DuckDuckGoIntegration, "duckduckgo_search"),
        (GitHubIntegration, "github"),
        (YouTubeIntegration, "youtube"),
        (ArxivIntegration, "research"),
        (OfficialDocsIntegration, "official_docs"),
    ])
    def test_provider_name(self, cls, expected) -> None:
        assert cls().provider_name == expected

    @pytest.mark.parametrize("cls", [
        MCPSearchIntegration,
        GoogleSearchIntegration,
        DuckDuckGoIntegration,
        GitHubIntegration,
        YouTubeIntegration,
        ArxivIntegration,
        OfficialDocsIntegration,
    ])
    def test_capabilities_is_list_of_strings(self, cls) -> None:
        caps = cls().capabilities()
        assert isinstance(caps, list)
        assert len(caps) > 0
        assert all(isinstance(c, str) for c in caps)

    @pytest.mark.parametrize("cls,method,args", [
        (MCPSearchIntegration, "search", [SearchRequest(query="test")]),
        (GoogleSearchIntegration, "search", [SearchRequest(query="test")]),
        (DuckDuckGoIntegration, "search", [SearchRequest(query="test")]),
        (GitHubIntegration, "discover_repositories", ["test"]),
        (YouTubeIntegration, "discover_videos", ["test"]),
        (ArxivIntegration, "discover_papers", ["test"]),
        (OfficialDocsIntegration, "lookup_documentation", ["test"]),
    ])
    def test_not_initialized_raises(self, cls, method, args) -> None:
        p = cls()
        with pytest.raises(ProviderUnavailableError, match="not initialized"):
            getattr(p, method)(*args)


# ---------------------------------------------------------------------------
# Edge case / additional coverage tests
# ---------------------------------------------------------------------------

class TestMCPSearchEdgeCases:
    def test_config_error_on_empty_endpoint(self) -> None:
        p = MCPSearchIntegration(config={"endpoint": ""})
        p.initialize()
        with pytest.raises(ProviderConfigurationError, match="endpoint"):
            p.search(SearchRequest(query="test"))

    def test_search_catch_all_exception(self) -> None:
        p = MCPSearchIntegration()
        p.initialize()
        with patch.object(p, "_execute_search", side_effect=RuntimeError("unexpected")):
            with pytest.raises(ProviderExecutionError):
                p.search(SearchRequest(query="test"))

    @patch("urllib.request.urlopen")
    def test_suggest_non_200(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(status=500)
        p = MCPSearchIntegration()
        p.initialize()
        suggestions = p.suggest("test")
        assert "test mcp" in suggestions

    @patch("urllib.request.urlopen")
    def test_suggest_dict_body(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(
            data=json.dumps({"suggestions": ["a", "b"]})
        )
        p = MCPSearchIntegration()
        p.initialize()
        suggestions = p.suggest("test")
        assert len(suggestions) == 2

    def test_normalize_date_parse_error(self) -> None:
        p = MCPSearchIntegration()
        body = {"results": [{"title": "T", "published_at": "bad-date"}]}
        results = p._normalize_results(body, "test")
        assert len(results) == 1
        assert results[0].published_at is None

    @patch("urllib.request.urlopen")
    def test_execute_search_non_200(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(status=500)
        p = MCPSearchIntegration()
        p.initialize()
        with pytest.raises(ProviderExecutionError):
            p.search(SearchRequest(query="test"))

    @patch("urllib.request.urlopen")
    def test_execute_search_generic_exception(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = ValueError("bad json")
        p = MCPSearchIntegration()
        p.initialize()
        with pytest.raises(ProviderExecutionError):
            p.search(SearchRequest(query="test"))


class TestGoogleSearchEdgeCases:
    def test_search_catch_all(self) -> None:
        p = GoogleSearchIntegration()
        p.initialize()
        with patch.object(p, "_execute_search", side_effect=RuntimeError("boom")):
            with pytest.raises(ProviderExecutionError):
                p.search(SearchRequest(query="test"))

    @patch("urllib.request.urlopen")
    def test_suggest_urlerror(self, mock_urlopen) -> None:
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("fail")
        p = GoogleSearchIntegration()
        p.initialize()
        suggestions = p.suggest("test")
        assert "test google" in suggestions

    @patch("urllib.request.urlopen")
    def test_execute_search_non_200(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(status=500)
        p = GoogleSearchIntegration()
        p.initialize()
        with pytest.raises(ProviderExecutionError):
            p.search(SearchRequest(query="test"))

    @patch("urllib.request.urlopen")
    def test_execute_search_generic(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = ValueError("bad")
        p = GoogleSearchIntegration()
        p.initialize()
        with pytest.raises(ProviderExecutionError):
            p.search(SearchRequest(query="test"))

    @patch("urllib.request.urlopen")
    def test_suggest_non_200(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(status=500)
        p = GoogleSearchIntegration()
        p.initialize()
        suggestions = p.suggest("test")
        assert "test google" in suggestions

    @patch("urllib.request.urlopen")
    def test_suggest_generic(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = ValueError("bad")
        p = GoogleSearchIntegration()
        p.initialize()
        suggestions = p.suggest("test")
        assert "test google" in suggestions

    @patch("urllib.request.urlopen")
    def test_suggest_empty_results(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(data=json.dumps(["test", []]))
        p = GoogleSearchIntegration()
        p.initialize()
        suggestions = p.suggest("test")
        assert len(suggestions) == 0

    def test_normalize_bad_date(self) -> None:
        p = GoogleSearchIntegration()
        body = {
            "items": [{
                "title": "T", "link": "https://ex.com",
                "snippet": "S",
                "pagemap": {"metatags": [{"article:published_time": "bad"}]},
            }]
        }
        results = p._normalize_results(body)
        assert len(results) == 1
        assert results[0].published_at is None

    @patch("urllib.request.urlopen")
    def test_suggest_dict_body(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(data=json.dumps({"custom": "data"}))
        p = GoogleSearchIntegration()
        p.initialize()
        suggestions = p.suggest("test")
        assert len(suggestions) == 0


class TestDuckDuckGoEdgeCases:
    def test_search_catch_all(self) -> None:
        p = DuckDuckGoIntegration()
        p.initialize()
        with patch.object(p, "_execute_search", side_effect=RuntimeError("boom")):
            with pytest.raises(ProviderExecutionError):
                p.search(SearchRequest(query="test"))

    @patch("urllib.request.urlopen")
    def test_execute_search_non_200(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(status=500)
        p = DuckDuckGoIntegration()
        p.initialize()
        with pytest.raises(ProviderExecutionError):
            p.search(SearchRequest(query="test"))

    @patch("urllib.request.urlopen")
    def test_execute_search_generic(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = ValueError("bad")
        p = DuckDuckGoIntegration()
        p.initialize()
        with pytest.raises(ProviderExecutionError):
            p.search(SearchRequest(query="test"))

    @patch("urllib.request.urlopen")
    def test_suggest_non_200(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(status=500)
        p = DuckDuckGoIntegration()
        p.initialize()
        suggestions = p.suggest("test")
        assert "test ddg" in suggestions

    @patch("urllib.request.urlopen")
    def test_suggest_generic(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = ValueError("bad")
        p = DuckDuckGoIntegration()
        p.initialize()
        suggestions = p.suggest("test")
        assert "test ddg" in suggestions

    @patch("urllib.request.urlopen")
    def test_suggest_empty(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(data=json.dumps([]))
        p = DuckDuckGoIntegration()
        p.initialize()
        suggestions = p.suggest("test")
        assert len(suggestions) == 0

    @patch("urllib.request.urlopen")
    def test_search_normalize_empty(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(
            data=json.dumps({"AbstractText": "", "AbstractURL": "", "RelatedTopics": []})
        )
        p = DuckDuckGoIntegration()
        p.initialize()
        resp = p.search(SearchRequest(query="test"))
        assert len(resp.results) == 0

    @patch("urllib.request.urlopen")
    def test_execute_search_urlerror(self, mock_urlopen) -> None:
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("fail")
        p = DuckDuckGoIntegration()
        p.initialize()
        with pytest.raises(ProviderUnavailableError):
            p.search(SearchRequest(query="test"))

    @patch("urllib.request.urlopen")
    def test_search_related_topics_nested(self, mock_urlopen) -> None:
        data = json.dumps({
            "AbstractText": "",
            "RelatedTopics": [
                {
                    "Text": "Category",
                    "Topics": [
                        {"Text": "Sub Topic 1", "FirstURL": "https://ex.com/1"},
                        {"Text": "Sub Topic 2 - desc", "FirstURL": "https://ex.com/2"},
                    ],
                },
                {"Text": "Regular Topic", "FirstURL": "https://ex.com/3"},
            ],
        })
        mock_urlopen.return_value = _mock_urlopen(data=data)
        p = DuckDuckGoIntegration()
        p.initialize()
        resp = p.search(SearchRequest(query="test"))
        assert len(resp.results) == 3

    @patch("urllib.request.urlopen")
    def test_suggest_dict_body(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(data=json.dumps({"custom": "data"}))
        p = DuckDuckGoIntegration()
        p.initialize()
        suggestions = p.suggest("test")
        assert len(suggestions) == 0


class TestGitHubEdgeCases:
    @patch("urllib.request.urlopen")
    def test_discover_releases_dict_body(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(
            data=json.dumps(GITHUB_RELEASES[0])
        )
        p = GitHubIntegration()
        p.initialize()
        sources = p.discover_releases("test", "repo")
        assert len(sources) == 1

    @patch("urllib.request.urlopen")
    def test_discover_releases_urlerror(self, mock_urlopen) -> None:
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("fail")
        p = GitHubIntegration()
        p.initialize()
        with pytest.raises(ProviderUnavailableError):
            p.discover_releases("test", "repo")

    @patch("urllib.request.urlopen")
    def test_discover_releases_500(self, mock_urlopen) -> None:
        import urllib.error
        exc = urllib.error.HTTPError("url", 500, "Error", {}, None)
        mock_urlopen.side_effect = exc
        p = GitHubIntegration()
        p.initialize()
        with pytest.raises(ProviderExecutionError):
            p.discover_releases("test", "repo")

    @patch("urllib.request.urlopen")
    def test_search_topics_urlerror(self, mock_urlopen) -> None:
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("fail")
        p = GitHubIntegration()
        p.initialize()
        with pytest.raises(ProviderUnavailableError):
            p.search_topics("test")

    def test_discover_repositories_catch_all(self) -> None:
        p = GitHubIntegration()
        p.initialize()
        with patch.object(p, "_request", side_effect=RuntimeError("boom")):
            with pytest.raises(ProviderExecutionError):
                p.discover_repositories("test")

    def test_discover_releases_catch_all(self) -> None:
        p = GitHubIntegration()
        p.initialize()
        with patch.object(p, "_request", side_effect=RuntimeError("boom")):
            with pytest.raises(ProviderExecutionError):
                p.discover_releases("test", "repo")

    def test_search_topics_catch_all(self) -> None:
        p = GitHubIntegration()
        p.initialize()
        with patch.object(p, "_request", side_effect=RuntimeError("boom")):
            with pytest.raises(ProviderExecutionError):
                p.search_topics("test")

    @patch("urllib.request.urlopen")
    def test_with_token_and_request(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(data=json.dumps(GITHUB_REPOS))
        p = GitHubIntegration(config={"token": "ghp_test"})
        p.initialize()
        sources = p.discover_repositories("python")
        assert len(sources) == 1

    @patch("urllib.request.urlopen")
    def test_request_non_200_status(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(status=502)
        p = GitHubIntegration()
        p.initialize()
        with pytest.raises(ProviderExecutionError):
            p.discover_repositories("test")

    @patch("urllib.request.urlopen")
    def test_request_http_error_generic(self, mock_urlopen) -> None:
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "url", 502, "Bad Gateway", {}, BytesIO(b"{}")
        )
        p = GitHubIntegration()
        p.initialize()
        with pytest.raises(ProviderExecutionError, match="502"):
            p.discover_repositories("test")

    @patch("urllib.request.urlopen")
    def test_request_generic_exception(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = ValueError("unexpected")
        p = GitHubIntegration()
        p.initialize()
        with pytest.raises(ProviderExecutionError):
            p.discover_repositories("test")

    @patch("urllib.request.urlopen")
    def test_discover_releases_bad_date(self, mock_urlopen) -> None:
        data = json.dumps([{"id": 1, "tag_name": "v1", "published_at": "bad-date"}])
        mock_urlopen.return_value = _mock_urlopen(data=data)
        p = GitHubIntegration()
        p.initialize()
        sources = p.discover_releases("test", "repo")
        assert len(sources) == 1


class TestYouTubeEdgeCases:
    @patch("urllib.request.urlopen")
    def test_request_http_error(self, mock_urlopen) -> None:
        import urllib.error
        exc = urllib.error.HTTPError("url", 500, "Error", {}, None)
        mock_urlopen.side_effect = exc
        p = YouTubeIntegration()
        p.initialize()
        with pytest.raises(ProviderExecutionError):
            p.discover_videos("test")

    @patch("urllib.request.urlopen")
    def test_request_non_200_status(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(status=500)
        p = YouTubeIntegration()
        p.initialize()
        with pytest.raises(ProviderExecutionError):
            p.discover_videos("test")

    @patch("urllib.request.urlopen")
    def test_request_generic_exception(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = ValueError("unexpected")
        p = YouTubeIntegration()
        p.initialize()
        with pytest.raises(ProviderExecutionError):
            p.discover_videos("test")

    def test_normalize_videos_bad_date(self) -> None:
        p = YouTubeIntegration()
        body = {"items": [{"id": {"videoId": "v1"}, "snippet": {"title": "T", "publishedAt": "bad"}}]}
        resources = p._normalize_videos(body)
        assert len(resources) == 1

    def test_normalize_playlists_bad_date(self) -> None:
        p = YouTubeIntegration()
        body = {"items": [{"id": {"playlistId": "pl1"}, "snippet": {"title": "T", "publishedAt": "bad"}}]}
        resources = p._normalize_playlists(body)
        assert len(resources) == 1

    @patch("urllib.request.urlopen")
    def test_discover_channels_urlerror(self, mock_urlopen) -> None:
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("fail")
        p = YouTubeIntegration()
        p.initialize()
        with pytest.raises(ProviderUnavailableError):
            p.discover_channels("test")

    @patch("urllib.request.urlopen")
    def test_discover_playlists_urlerror(self, mock_urlopen) -> None:
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("fail")
        p = YouTubeIntegration()
        p.initialize()
        with pytest.raises(ProviderUnavailableError):
            p.discover_playlists("test")

    @patch("urllib.request.urlopen")
    def test_discover_playlists_500(self, mock_urlopen) -> None:
        import urllib.error
        exc = urllib.error.HTTPError("url", 500, "Error", {}, None)
        mock_urlopen.side_effect = exc
        p = YouTubeIntegration()
        p.initialize()
        with pytest.raises(ProviderExecutionError):
            p.discover_playlists("test")

    def test_discover_videos_catch_all(self) -> None:
        p = YouTubeIntegration()
        p.initialize()
        with patch.object(p, "_request", side_effect=RuntimeError("boom")):
            with pytest.raises(ProviderExecutionError):
                p.discover_videos("test")

    def test_discover_channels_catch_all(self) -> None:
        p = YouTubeIntegration()
        p.initialize()
        with patch.object(p, "_request", side_effect=RuntimeError("boom")):
            with pytest.raises(ProviderExecutionError):
                p.discover_channels("test")

    def test_discover_playlists_catch_all(self) -> None:
        p = YouTubeIntegration()
        p.initialize()
        with patch.object(p, "_request", side_effect=RuntimeError("boom")):
            with pytest.raises(ProviderExecutionError):
                p.discover_playlists("test")


class TestArxivEdgeCases:
    @patch("urllib.request.urlopen")
    def test_request_http_error(self, mock_urlopen) -> None:
        import urllib.error
        exc = urllib.error.HTTPError("url", 500, "Error", {}, None)
        mock_urlopen.side_effect = exc
        p = ArxivIntegration()
        p.initialize()
        with pytest.raises(ProviderExecutionError):
            p.author_lookup("Smith")

    @patch("urllib.request.urlopen")
    def test_request_generic_exception(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = ValueError("unexpected")
        p = ArxivIntegration()
        p.initialize()
        with pytest.raises(ProviderExecutionError):
            p.discover_papers("test")

    def test_normalize_papers_bad_date(self) -> None:
        p = ArxivIntegration()
        bad_xml = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2201.00001</id>
    <title>Test</title>
    <summary>Abstract</summary>
    <published>not-a-date</published>
  </entry>
</feed>"""
        sources = p._normalize_papers(bad_xml)
        assert len(sources) == 1
        assert sources[0].last_checked is None

    @patch("urllib.request.urlopen")
    def test_author_lookup_urlerror(self, mock_urlopen) -> None:
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("fail")
        p = ArxivIntegration()
        p.initialize()
        with pytest.raises(ProviderUnavailableError):
            p.author_lookup("Smith")

    @patch("urllib.request.urlopen")
    def test_search_topics_urlerror(self, mock_urlopen) -> None:
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("fail")
        p = ArxivIntegration()
        p.initialize()
        with pytest.raises(ProviderUnavailableError):
            p.search_topics("cs.AI")

    @patch("urllib.request.urlopen")
    def test_request_non_200_status(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(status=500)
        p = ArxivIntegration()
        p.initialize()
        with pytest.raises(ProviderExecutionError):
            p.discover_papers("test")

    def test_discover_papers_catch_all(self) -> None:
        p = ArxivIntegration()
        p.initialize()
        with patch.object(p, "_request", side_effect=RuntimeError("boom")):
            with pytest.raises(ProviderExecutionError):
                p.discover_papers("test")

    def test_author_lookup_catch_all(self) -> None:
        p = ArxivIntegration()
        p.initialize()
        with patch.object(p, "_request", side_effect=RuntimeError("boom")):
            with pytest.raises(ProviderExecutionError):
                p.author_lookup("Smith")

    def test_search_topics_catch_all(self) -> None:
        p = ArxivIntegration()
        p.initialize()
        with patch.object(p, "_request", side_effect=RuntimeError("boom")):
            with pytest.raises(ProviderExecutionError):
                p.search_topics("test")


class TestOfficialDocsEdgeCases:
    @patch("urllib.request.urlopen")
    def test_discover_versions_urlerror(self, mock_urlopen) -> None:
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("fail")
        p = OfficialDocsIntegration()
        p.initialize()
        with pytest.raises(ProviderUnavailableError):
            p.discover_versions("test")

    @patch("urllib.request.urlopen")
    def test_release_notes_urlerror(self, mock_urlopen) -> None:
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("fail")
        p = OfficialDocsIntegration()
        p.initialize()
        with pytest.raises(ProviderUnavailableError):
            p.get_release_notes("test", "1.0")

    @patch("urllib.request.urlopen")
    def test_lookup_documentation_list_body(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(
            data=json.dumps([{"id": "doc1", "title": "Doc", "url": "https://ex.com/1"}])
        )
        p = OfficialDocsIntegration()
        p.initialize()
        sources = p.lookup_documentation("test")
        assert len(sources) == 1

    def test_lookup_documentation_catch_all(self) -> None:
        p = OfficialDocsIntegration()
        p.initialize()
        with patch.object(p, "_request", side_effect=RuntimeError("boom")):
            with pytest.raises(ProviderExecutionError):
                p.lookup_documentation("test")

    def test_discover_versions_catch_all(self) -> None:
        p = OfficialDocsIntegration()
        p.initialize()
        with patch.object(p, "_request", side_effect=RuntimeError("boom")):
            with pytest.raises(ProviderExecutionError):
                p.discover_versions("test")

    def test_release_notes_catch_all(self) -> None:
        p = OfficialDocsIntegration()
        p.initialize()
        with patch.object(p, "_request", side_effect=RuntimeError("boom")):
            with pytest.raises(ProviderExecutionError):
                p.get_release_notes("test", "1.0")

    @patch("urllib.request.urlopen")
    def test_lookup_with_version(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(data=json.dumps(DOCS_RESPONSE))
        p = OfficialDocsIntegration()
        p.initialize()
        sources = p.lookup_documentation("python", version="3.12")
        assert len(sources) == 1

    @patch("urllib.request.urlopen")
    def test_request_non_200(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(status=500)
        p = OfficialDocsIntegration()
        p.initialize()
        with pytest.raises(ProviderExecutionError):
            p.lookup_documentation("test")

    @patch("urllib.request.urlopen")
    def test_request_generic_exception(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = ValueError("unexpected")
        p = OfficialDocsIntegration()
        p.initialize()
        with pytest.raises(ProviderExecutionError):
            p.lookup_documentation("test")

    @patch("urllib.request.urlopen")
    def test_lookup_documentation_bad_date(self, mock_urlopen) -> None:
        mock_urlopen.return_value = _mock_urlopen(
            data=json.dumps({"docs": [{"id": "d1", "title": "T", "updated_at": "bad-date"}]})
        )
        p = OfficialDocsIntegration()
        p.initialize()
        sources = p.lookup_documentation("test")
        assert len(sources) == 1
        assert sources[0].last_checked is None

    @patch("urllib.request.urlopen")
    def test_discover_versions_bad_date(self, mock_urlopen) -> None:
        bad_data = json.dumps({
            "versions": [{"version": "1.0", "release_date": "not-a-date"}]
        })
        mock_urlopen.return_value = _mock_urlopen(data=bad_data)
        p = OfficialDocsIntegration()
        p.initialize()
        versions = p.discover_versions("test")
        assert len(versions) == 1
        assert versions[0].created_at is None
