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


class DuckDuckGoIntegration:
    def __init__(self, config: dict | None = None) -> None:
        self._config = config or {}
        self._logger = get_logger("providers.integrations.duckduckgo")
        self._base_url = self._config.get(
            "endpoint", "https://api.duckduckgo.com"
        )
        self._timeout = self._config.get("timeout", 30)
        self._retry_count = self._config.get("retry_count", 3)
        self._user_agent = self._config.get("user_agent", "AICOS/0.1.0")
        self._initialized = False

    @property
    def provider_name(self) -> str:
        return "duckduckgo_search"

    def initialize(self) -> None:
        self._logger.debug("DuckDuckGoIntegration initializing")
        self._initialized = True

    def shutdown(self) -> None:
        self._logger.debug("DuckDuckGoIntegration shutting down")
        self._initialized = False

    def health(self) -> ProviderHealth:
        try:
            self._verify_connection()
            return ProviderHealth(
                provider_name="duckduckgo_search",
                healthy=True,
                last_check=datetime.now(),
                message="duckduckgo_search integration operational",
            )
        except Exception as exc:
            return ProviderHealth(
                provider_name="duckduckgo_search",
                healthy=False,
                last_check=datetime.now(),
                message=str(exc),
            )

    def capabilities(self) -> list[str]:
        return ["search", "suggest"]

    def _verify_connection(self) -> None:
        if not self._initialized:
            raise ProviderUnavailableError("DuckDuckGoIntegration not initialized")

    def search(self, request: SearchRequest) -> SearchResponse:
        start = time.time()
        self._logger.info(
            "provider=duckduckgo_search capability=search query=%s max_results=%d",
            request.query, request.max_results,
        )
        try:
            self._verify_connection()
            results = self._execute_search(request)
            duration = (time.time() - start) * 1000
            self._logger.info(
                "provider=duckduckgo_search capability=search status=success results=%d duration_ms=%.1f",
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
                "provider=duckduckgo_search capability=search status=error duration_ms=%.1f error=%s",
                duration, str(exc),
            )
            raise ProviderExecutionError(
                f"DuckDuckGoProvider search failed: {exc}"
            ) from exc

    def _execute_search(self, request: SearchRequest) -> list[SearchResult]:
        params = urllib.parse.urlencode({
            "q": request.query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1",
        })
        url = f"{self._base_url}/?{params}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": self._user_agent},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                if resp.status != 200:
                    raise ProviderExecutionError(
                        f"DuckDuckGo search returned status {resp.status}"
                    )
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise ProviderUnavailableError(
                f"DuckDuckGo search unavailable: {exc}"
            ) from exc
        except Exception as exc:
            raise ProviderExecutionError(
                f"DuckDuckGo search failed: {exc}"
            ) from exc

        return self._normalize_results(body)

    def _normalize_results(self, body: dict[str, Any]) -> list[SearchResult]:
        results: list[SearchResult] = []
        abstract = body.get("AbstractText", "")
        abstract_url = body.get("AbstractURL", "")
        if abstract:
            results.append(SearchResult(
                title=body.get("Heading", "DuckDuckGo Result"),
                url=abstract_url,
                snippet=abstract,
                source="duckduckgo",
            ))
        for topic in body.get("RelatedTopics", []):
            if "Topics" in topic:
                for sub in topic["Topics"]:
                    self._append_result(results, sub)
            else:
                self._append_result(results, topic)
        return results

    def _append_result(self, results: list[SearchResult], item: dict[str, Any]) -> None:
        text = item.get("Text", "")
        url = item.get("FirstURL", "")
        if text or url:
            results.append(SearchResult(
                title=text.split(" - ")[0] if " - " in text else text,
                url=url,
                snippet=text,
                source="duckduckgo",
            ))

    def suggest(self, query: str) -> list[str]:
        self._logger.info(
            "provider=duckduckgo_search capability=suggest query=%s", query,
        )
        try:
            self._verify_connection()
            return self._execute_suggest(query)
        except Exception as exc:
            self._logger.warning(
                "provider=duckduckgo_search capability=suggest status=error error=%s",
                str(exc),
            )
            return [f"{query} ddg", f"{query} ddg tutorial", f"{query} ddg wiki"]

    def _execute_suggest(self, query: str) -> list[str]:
        params = urllib.parse.urlencode({"q": query})
        url = f"https://duckduckgo.com/ac/?{params}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": self._user_agent},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                if resp.status != 200:
                    raise ProviderExecutionError(
                        f"DuckDuckGo suggest returned status {resp.status}"
                    )
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise ProviderUnavailableError(
                f"DuckDuckGo suggest unavailable: {exc}"
            ) from exc
        except Exception as exc:
            raise ProviderExecutionError(
                f"DuckDuckGo suggest failed: {exc}"
            ) from exc

        if isinstance(body, list):
            return [s.get("phrase", str(s)) for s in body]
        return []
