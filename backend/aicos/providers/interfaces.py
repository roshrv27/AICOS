"""Provider-neutral protocols for the provider infrastructure.

Application code depends **only** on the protocols defined here.
Concrete implementations are wired via DI.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import (
    ProviderHealth,
    SearchRequest,
    SearchResponse,
)


@runtime_checkable
class ProviderProtocol(Protocol):
    def initialize(self) -> None: ...

    def shutdown(self) -> None: ...

    def health(self) -> ProviderHealth: ...

    def capabilities(self) -> list[str]: ...


@runtime_checkable
class SearchProviderProtocol(ProviderProtocol, Protocol):
    def search(self, request: SearchRequest) -> SearchResponse: ...

    def suggest(self, query: str) -> list[str]: ...


@runtime_checkable
class GitHubProviderProtocol(ProviderProtocol, Protocol):
    ...


@runtime_checkable
class YouTubeProviderProtocol(ProviderProtocol, Protocol):
    ...


@runtime_checkable
class ResearchProviderProtocol(ProviderProtocol, Protocol):
    ...


@runtime_checkable
class OfficialDocsProviderProtocol(ProviderProtocol, Protocol):
    ...
