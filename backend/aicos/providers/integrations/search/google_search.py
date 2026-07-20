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
from ...models import ProviderHealth, SearchRequest, SearchResponse, SearchResult


class GoogleSearchIntegration:
    def __init__(self, config: dict | None = None) -> None:
        self._config = config or {}
        self._logger = get_logger("providers.integrations.google_search")
        self._api_key = self._config.get("api_key", "")
        self._search_engine_id = self._config.get("search_engine_id", "")
        self._base_url = self._config.get(
            "endpoint", "https://www.googleapis.com/customsearch/v1"
        )
        self._timeout = self._config.get("timeout", 30)
        self._retry_count = self._config.get("retry_count", 3)
        self._user_agent = self._config.get("user_agent", "AICOS/0.1.0")
        self._initialized = False

    @property
    def provider_name(self) -> str:
        return "google_search"

    def initialize(self) -> None:
        self._logger.debug("GoogleSearchIntegration initializing")
        self._initialized = True

    def shutdown(self) -> None:
        self._logger.debug("GoogleSearchIntegration shutting down")
        self._initialized = False

    def health(self) -> ProviderHealth:
        try:
            self._verify_connection()
            return ProviderHealth(
                provider_name="google_search",
                healthy=True,
                last_check=datetime.now(),
                message="google_search integration operational",
            )
        except Exception as exc:
            return ProviderHealth(
                provider_name="google_search",
                healthy=False,
                last_check=datetime.now(),
                message=str(exc),
            )

    def capabilities(self) -> list[str]:
        return ["search", "suggest"]

    def _verify_connection(self) -> None:
        if not self._initialized:
            raise ProviderUnavailableError("GoogleSearchIntegration not initialized")

    def search(self, request: SearchRequest) -> SearchResponse:
        start = time.time()
        self._logger.info(
            "provider=google_search capability=search query=%s max_results=%d",
            request.query, request.max_results,
        )
        try:
            self._verify_connection()
            results = self._execute_search(request)
            duration = (time.time() - start) * 1000
            self._logger.info(
                "provider=google_search capability=search status=success results=%d duration_ms=%.1f",
                len(results), duration,
            )
            return SearchResponse(
                query=request.query,
                results=results,
                total_estimated=len(results),
                duration_ms=duration,
            )
        except (ProviderExecutionError, ProviderUnavailableError, ProviderConfigurationError):
            raise
        except Exception as exc:
            duration = (time.time() - start) * 1000
            self._logger.warning(
                "provider=google_search capability=search status=error duration_ms=%.1f error=%s",
                duration, str(exc),
            )
            raise ProviderExecutionError(
                f"GoogleSearchProvider search failed: {exc}"
            ) from exc

    def _execute_search(self, request: SearchRequest) -> list[SearchResult]:
        params = urllib.parse.urlencode({
            "key": self._api_key,
            "cx": self._search_engine_id,
            "q": request.query,
            "num": min(request.max_results, 10),
        })
        url = f"{self._base_url}?{params}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": self._user_agent},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                if resp.status != 200:
                    raise ProviderExecutionError(
                        f"Google search returned status {resp.status}"
                    )
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise ProviderUnavailableError(
                f"Google search unavailable: {exc}"
            ) from exc
        except Exception as exc:
            raise ProviderExecutionError(
                f"Google search failed: {exc}"
            ) from exc

        return self._normalize_results(body)

    def _normalize_results(self, body: dict[str, Any]) -> list[SearchResult]:
        results: list[SearchResult] = []
        items = body.get("items", [])
        for item in items:
            published = None
            if item.get("pagemap", {}).get("metatags"):
                mt = item["pagemap"]["metatags"][0]
                date_str = mt.get("article:published_time") or mt.get("date")
                if date_str:
                    try:
                        published = datetime.fromisoformat(date_str)
                    except (ValueError, TypeError):
                        published = None
            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("link", ""),
                snippet=item.get("snippet", ""),
                source="google",
                published_at=published,
                relevance_score=1.0,
            ))
        return results

    def suggest(self, query: str) -> list[str]:
        self._logger.info(
            "provider=google_search capability=suggest query=%s", query,
        )
        try:
            self._verify_connection()
            return self._execute_suggest(query)
        except Exception as exc:
            self._logger.warning(
                "provider=google_search capability=suggest status=error error=%s",
                str(exc),
            )
            return [f"{query} google", f"{query} tutorial", f"{query} examples"]

    def _execute_suggest(self, query: str) -> list[str]:
        params = urllib.parse.urlencode({
            "client": "chrome",
            "q": query,
        })
        url = f"https://suggestqueries.google.com/complete/search?{params}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": self._user_agent},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                if resp.status != 200:
                    raise ProviderExecutionError(
                        f"Google suggest returned status {resp.status}"
                    )
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise ProviderUnavailableError(
                f"Google suggest unavailable: {exc}"
            ) from exc
        except Exception as exc:
            raise ProviderExecutionError(
                f"Google suggest failed: {exc}"
            ) from exc

        if isinstance(body, list) and len(body) > 1:
            return [str(s) for s in body[1]]
        return []
