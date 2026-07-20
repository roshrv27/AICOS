"""Search providers.

Abstract :class:`SearchProvider` base class and placeholder
implementations for MCP, Google, and DuckDuckGo search.
No network calls, APIs, or HTTP.
"""

from __future__ import annotations

from abc import abstractmethod
from datetime import datetime

from ...logging import get_logger
from ..models import (
    ProviderHealth,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from .base import Provider


class SearchProvider(Provider):
    @abstractmethod
    def search(self, request: SearchRequest) -> SearchResponse:
        """Execute a search query and return results."""

    @abstractmethod
    def suggest(self, query: str) -> list[str]:
        """Return search suggestion strings for the given query."""


class MCPSearchProvider(SearchProvider):
    def __init__(self, config: dict | None = None) -> None:
        self._config = config or {}
        self._logger = get_logger(__name__)

    @property
    def provider_name(self) -> str:
        return "mcp_search"

    def initialize(self) -> None:
        self._logger.debug("MCPSearchProvider initialized")

    def shutdown(self) -> None:
        self._logger.debug("MCPSearchProvider shutdown")

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_name="mcp_search",
            healthy=True,
            last_check=datetime.now(),
            message="mcp_search provider operational",
        )

    def capabilities(self) -> list[str]:
        return ["search", "suggest"]

    def search(self, request: SearchRequest) -> SearchResponse:
        self._logger.info("mcp_search: %s", request.query)
        return SearchResponse(
            query=request.query,
            results=[
                SearchResult(
                    title=f"MCP Result for {request.query}",
                    url=f"https://mcp.example.com/{request.query}",
                    snippet=f"MCP search result for {request.query}",
                    source="mcp",
                ),
            ],
            total_estimated=1,
        )

    def suggest(self, query: str) -> list[str]:
        return [f"{query} mcp", f"{query} mcp tutorial", f"{query} mcp guide"]


class GoogleSearchProvider(SearchProvider):
    def __init__(self, config: dict | None = None) -> None:
        self._config = config or {}
        self._logger = get_logger(__name__)

    @property
    def provider_name(self) -> str:
        return "google_search"

    def initialize(self) -> None:
        self._logger.debug("GoogleSearchProvider initialized")

    def shutdown(self) -> None:
        self._logger.debug("GoogleSearchProvider shutdown")

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_name="google_search",
            healthy=True,
            last_check=datetime.now(),
            message="google_search provider operational",
        )

    def capabilities(self) -> list[str]:
        return ["search", "suggest"]

    def search(self, request: SearchRequest) -> SearchResponse:
        self._logger.info("google_search: %s", request.query)
        return SearchResponse(
            query=request.query,
            results=[
                SearchResult(
                    title=f"Google Result for {request.query}",
                    url=f"https://google.example.com/{request.query}",
                    snippet=f"Google search result for {request.query}",
                    source="google",
                ),
            ],
            total_estimated=1,
        )

    def suggest(self, query: str) -> list[str]:
        return [f"{query} google", f"{query} tutorial", f"{query} examples"]


class DuckDuckGoSearchProvider(SearchProvider):
    def __init__(self, config: dict | None = None) -> None:
        self._config = config or {}
        self._logger = get_logger(__name__)

    @property
    def provider_name(self) -> str:
        return "duckduckgo_search"

    def initialize(self) -> None:
        self._logger.debug("DuckDuckGoSearchProvider initialized")

    def shutdown(self) -> None:
        self._logger.debug("DuckDuckGoSearchProvider shutdown")

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider_name="duckduckgo_search",
            healthy=True,
            last_check=datetime.now(),
            message="duckduckgo_search provider operational",
        )

    def capabilities(self) -> list[str]:
        return ["search", "suggest"]

    def search(self, request: SearchRequest) -> SearchResponse:
        self._logger.info("duckduckgo_search: %s", request.query)
        return SearchResponse(
            query=request.query,
            results=[
                SearchResult(
                    title=f"DuckDuckGo Result for {request.query}",
                    url=f"https://duckduckgo.example.com/{request.query}",
                    snippet=f"DuckDuckGo search result for {request.query}",
                    source="duckduckgo",
                ),
            ],
            total_estimated=1,
        )

    def suggest(self, query: str) -> list[str]:
        return [f"{query} ddg", f"{query} ddg tutorial", f"{query} ddg wiki"]
