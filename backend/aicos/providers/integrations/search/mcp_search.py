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


class MCPSearchIntegration:
    def __init__(self, config: dict | None = None) -> None:
        self._config = config or {}
        self._logger = get_logger("providers.integrations.mcp_search")
        self._base_url = self._config.get("endpoint", "https://mcp.example.com/api")
        self._timeout = self._config.get("timeout", 30)
        self._retry_count = self._config.get("retry_count", 3)
        self._user_agent = self._config.get("user_agent", "AICOS/0.1.0")
        self._initialized = False

    @property
    def provider_name(self) -> str:
        return "mcp_search"

    def initialize(self) -> None:
        self._logger.debug("MCPSearchIntegration initializing")
        self._initialized = True

    def shutdown(self) -> None:
        self._logger.debug("MCPSearchIntegration shutting down")
        self._initialized = False

    def health(self) -> ProviderHealth:
        try:
            self._verify_connection()
            return ProviderHealth(
                provider_name="mcp_search",
                healthy=True,
                last_check=datetime.now(),
                message="mcp_search integration operational",
            )
        except Exception as exc:
            return ProviderHealth(
                provider_name="mcp_search",
                healthy=False,
                last_check=datetime.now(),
                message=str(exc),
            )

    def capabilities(self) -> list[str]:
        return ["search", "suggest"]

    def _verify_connection(self) -> None:
        if not self._initialized:
            raise ProviderUnavailableError("MCPSearchIntegration not initialized")
        endpoint = self._config.get("endpoint", "https://mcp.example.com/api")
        if not endpoint:
            raise ProviderConfigurationError("MCP endpoint not configured")

    def search(self, request: SearchRequest) -> SearchResponse:
        start = time.time()
        self._logger.info(
            "provider=mcp_search capability=search query=%s max_results=%d",
            request.query, request.max_results,
        )
        try:
            self._verify_connection()
            results = self._execute_search(request)
            duration = (time.time() - start) * 1000
            self._logger.info(
                "provider=mcp_search capability=search status=success results=%d duration_ms=%.1f",
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
                "provider=mcp_search capability=search status=error duration_ms=%.1f error=%s",
                duration, str(exc),
            )
            raise ProviderExecutionError(
                f"MCPSearchProvider search failed: {exc}"
            ) from exc

    def _execute_search(self, request: SearchRequest) -> list[SearchResult]:
        params = urllib.parse.urlencode({
            "q": request.query,
            "max": request.max_results,
        })
        url = f"{self._base_url}/search?{params}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": self._user_agent},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                if resp.status != 200:
                    raise ProviderExecutionError(
                        f"MCP search returned status {resp.status}"
                    )
                body = json.loads(resp.read().decode("utf-8"))
        except ProviderExecutionError:
            raise
        except urllib.error.URLError as exc:
            raise ProviderUnavailableError(f"MCP search unavailable: {exc}") from exc
        except Exception as exc:
            raise ProviderExecutionError(f"MCP search failed: {exc}") from exc

        return self._normalize_results(body, request.query)

    def _normalize_results(self, body: dict[str, Any], query: str) -> list[SearchResult]:
        results: list[SearchResult] = []
        raw = body if isinstance(body, list) else body.get("results", body.get("items", []))
        for item in raw:
            published = None
            if item.get("published_at") or item.get("date"):
                try:
                    published = datetime.fromisoformat(
                        item.get("published_at") or item.get("date", "")
                    )
                except (ValueError, TypeError):
                    published = None
            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("url", item.get("link", "")),
                snippet=item.get("snippet", item.get("description", "")),
                source="mcp",
                published_at=published,
                relevance_score=float(item.get("relevance", item.get("score", 0.0))),
            ))
        return results

    def suggest(self, query: str) -> list[str]:
        self._logger.info(
            "provider=mcp_search capability=suggest query=%s", query,
        )
        try:
            self._verify_connection()
            return self._execute_suggest(query)
        except Exception as exc:
            self._logger.warning(
                "provider=mcp_search capability=suggest status=error error=%s",
                str(exc),
            )
            return [f"{query} mcp", f"{query} mcp tutorial", f"{query} mcp guide"]

    def _execute_suggest(self, query: str) -> list[str]:
        params = urllib.parse.urlencode({"q": query})
        url = f"{self._base_url}/suggest?{params}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": self._user_agent},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                if resp.status != 200:
                    raise ProviderExecutionError(
                        f"MCP suggest returned status {resp.status}"
                    )
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise ProviderUnavailableError(f"MCP suggest unavailable: {exc}") from exc
        except Exception as exc:
            raise ProviderExecutionError(f"MCP suggest failed: {exc}") from exc

        if isinstance(body, list):
            return [str(s) for s in body]
        return [str(s) for s in body.get("suggestions", body.get("results", []))]
