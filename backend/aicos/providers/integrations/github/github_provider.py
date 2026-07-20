from __future__ import annotations

import time
import urllib.request
import urllib.parse
import json
from datetime import datetime
from typing import Any

from ....logging import get_logger
from ...exceptions import (
    ProviderConfigurationError,
    ProviderExecutionError,
    ProviderUnavailableError,
)
from ...models import ProviderHealth
from ....knowledge_intelligence.enums import KnowledgeSourceType, TechnologyStatus
from ....knowledge_intelligence.models import (
    Evidence,
    KnowledgeSource,
    TechnologySignal,
)


class GitHubIntegration:
    def __init__(self, config: dict | None = None) -> None:
        self._config = config or {}
        self._logger = get_logger("providers.integrations.github")
        self._token = self._config.get("token", "")
        self._base_url = self._config.get(
            "endpoint", "https://api.github.com"
        )
        self._timeout = self._config.get("timeout", 60)
        self._retry_count = self._config.get("retry_count", 3)
        self._user_agent = self._config.get("user_agent", "AICOS/0.1.0")
        self._initialized = False

    @property
    def provider_name(self) -> str:
        return "github"

    def initialize(self) -> None:
        self._logger.debug("GitHubIntegration initializing")
        self._initialized = True

    def shutdown(self) -> None:
        self._logger.debug("GitHubIntegration shutting down")
        self._initialized = False

    def health(self) -> ProviderHealth:
        try:
            self._verify_connection()
            return ProviderHealth(
                provider_name="github",
                healthy=True,
                last_check=datetime.now(),
                message="github integration operational",
            )
        except Exception as exc:
            return ProviderHealth(
                provider_name="github",
                healthy=False,
                last_check=datetime.now(),
                message=str(exc),
            )

    def capabilities(self) -> list[str]:
        return ["repository_discovery", "release_discovery", "topic_search"]

    def _verify_connection(self) -> None:
        if not self._initialized:
            raise ProviderUnavailableError("GitHubIntegration not initialized")

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "User-Agent": self._user_agent,
            "Accept": "application/vnd.github.v3+json",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _request(self, url: str) -> dict[str, Any]:
        req = urllib.request.Request(
            url,
            headers=self._build_headers(),
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                if resp.status != 200:
                    raise ProviderExecutionError(
                        f"GitHub API returned status {resp.status}"
                    )
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 403:
                raise ProviderUnavailableError(
                    "GitHub API rate limit exceeded"
                ) from exc
            if exc.code == 404:
                raise ProviderExecutionError(
                    f"GitHub resource not found: {url}"
                ) from exc
            raise ProviderExecutionError(
                f"GitHub API error {exc.code}: {exc.reason}"
            ) from exc
        except urllib.error.URLError as exc:
            raise ProviderUnavailableError(
                f"GitHub API unavailable: {exc}"
            ) from exc
        except Exception as exc:
            raise ProviderExecutionError(
                f"GitHub request failed: {exc}"
            ) from exc

    def discover_repositories(self, query: str) -> list[KnowledgeSource]:
        start = time.time()
        self._logger.info(
            "provider=github capability=repository_discovery query=%s", query,
        )
        try:
            self._verify_connection()
            params = urllib.parse.urlencode({
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": 10,
            })
            url = f"{self._base_url}/search/repositories?{params}"
            body = self._request(url)
            sources = self._normalize_repositories(body, query)
            duration = (time.time() - start) * 1000
            self._logger.info(
                "provider=github capability=repository_discovery status=success results=%d duration_ms=%.1f",
                len(sources), duration,
            )
            return sources
        except (ProviderExecutionError, ProviderUnavailableError, ProviderConfigurationError):
            raise
        except Exception as exc:
            duration = (time.time() - start) * 1000
            self._logger.warning(
                "provider=github capability=repository_discovery status=error duration_ms=%.1f error=%s",
                duration, str(exc),
            )
            raise ProviderExecutionError(
                f"GitHub repository discovery failed: {exc}"
            ) from exc

    def _normalize_repositories(
        self, body: dict[str, Any], query: str,
    ) -> list[KnowledgeSource]:
        sources: list[KnowledgeSource] = []
        for repo in body.get("items", []):
            sources.append(KnowledgeSource(
                id=f"github_repo_{repo.get('id', '')}",
                name=repo.get("full_name", repo.get("name", "")),
                source_type=KnowledgeSourceType.GITHUB,
                provider="github",
                base_url=repo.get("html_url", ""),
                credibility_score=min(
                    repo.get("stargazers_count", 0) / 100000, 1.0
                ),
                priority=min(repo.get("stargazers_count", 0) // 100, 100),
                enabled=True,
                last_checked=datetime.now(),
            ))
        return sources

    def discover_releases(self, owner: str, repo: str) -> list[KnowledgeSource]:
        start = time.time()
        self._logger.info(
            "provider=github capability=release_discovery owner=%s repo=%s",
            owner, repo,
        )
        try:
            self._verify_connection()
            url = f"{self._base_url}/repos/{owner}/{repo}/releases?per_page=10"
            body = self._request(url)
            sources = self._normalize_releases(body, owner, repo)
            duration = (time.time() - start) * 1000
            self._logger.info(
                "provider=github capability=release_discovery status=success results=%d duration_ms=%.1f",
                len(sources), duration,
            )
            return sources
        except (ProviderExecutionError, ProviderUnavailableError, ProviderConfigurationError):
            raise
        except Exception as exc:
            duration = (time.time() - start) * 1000
            self._logger.warning(
                "provider=github capability=release_discovery status=error duration_ms=%.1f error=%s",
                duration, str(exc),
            )
            raise ProviderExecutionError(
                f"GitHub release discovery failed: {exc}"
            ) from exc

    def _normalize_releases(
        self, body: list[dict[str, Any]], owner: str, repo: str,
    ) -> list[KnowledgeSource]:
        sources: list[KnowledgeSource] = []
        if isinstance(body, dict):
            body = [body]
        for release in body:
            published = None
            if release.get("published_at"):
                try:
                    published = datetime.fromisoformat(
                        release["published_at"].replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    published = None
            sources.append(KnowledgeSource(
                id=f"github_release_{release.get('id', '')}",
                name=release.get("tag_name", release.get("name", "")),
                source_type=KnowledgeSourceType.GITHUB,
                provider="github",
                base_url=release.get("html_url", ""),
                credibility_score=0.95,
                priority=70,
                enabled=True,
                last_checked=datetime.now(),
            ))
        return sources

    def search_topics(self, query: str) -> list[TechnologySignal]:
        start = time.time()
        self._logger.info(
            "provider=github capability=topic_search query=%s", query,
        )
        try:
            self._verify_connection()
            params = urllib.parse.urlencode({
                "q": query,
                "per_page": 10,
            })
            url = f"{self._base_url}/search/topics?{params}"
            body = self._request(url)
            signals = self._normalize_topics(body)
            duration = (time.time() - start) * 1000
            self._logger.info(
                "provider=github capability=topic_search status=success results=%d duration_ms=%.1f",
                len(signals), duration,
            )
            return signals
        except (ProviderExecutionError, ProviderUnavailableError, ProviderConfigurationError):
            raise
        except Exception as exc:
            duration = (time.time() - start) * 1000
            self._logger.warning(
                "provider=github capability=topic_search status=error duration_ms=%.1f error=%s",
                duration, str(exc),
            )
            raise ProviderExecutionError(
                f"GitHub topic search failed: {exc}"
            ) from exc

    def _normalize_topics(self, body: dict[str, Any]) -> list[TechnologySignal]:
        signals: list[TechnologySignal] = []
        for topic in body.get("items", []):
            signals.append(TechnologySignal(
                id=f"github_topic_{topic.get('name', '')}",
                name=topic.get("name", ""),
                summary=topic.get("description", ""),
                category="github_topic",
                first_seen=datetime.now(),
                status=TechnologyStatus.EMERGING,
                importance=min(topic.get("score", 0), 10),
                confidence_score=min(
                    topic.get("score", 0) / 100, 1.0
                ),
                evidence=[
                    Evidence(
                        id=f"github_topic_ev_{topic.get('name', '')}",
                        source="github",
                        title=topic.get("name", ""),
                        url=topic.get("url", ""),
                        confidence=min(topic.get("score", 0) / 100, 1.0),
                    ),
                ],
            ))
        return signals
