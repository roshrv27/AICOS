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
from ....knowledge_intelligence.enums import KnowledgeSourceType
from ....knowledge_intelligence.models import (
    KnowledgeSource,
    KnowledgeVersion,
)


class OfficialDocsIntegration:
    def __init__(self, config: dict | None = None) -> None:
        self._config = config or {}
        self._logger = get_logger("providers.integrations.official_docs")
        self._base_url = self._config.get(
            "endpoint", "https://docs.example.com/api"
        )
        self._timeout = self._config.get("timeout", 30)
        self._retry_count = self._config.get("retry_count", 3)
        self._user_agent = self._config.get("user_agent", "AICOS/0.1.0")
        self._initialized = False

    @property
    def provider_name(self) -> str:
        return "official_docs"

    def initialize(self) -> None:
        self._logger.debug("OfficialDocsIntegration initializing")
        self._initialized = True

    def shutdown(self) -> None:
        self._logger.debug("OfficialDocsIntegration shutting down")
        self._initialized = False

    def health(self) -> ProviderHealth:
        try:
            self._verify_connection()
            return ProviderHealth(
                provider_name="official_docs",
                healthy=True,
                last_check=datetime.now(),
                message="official_docs integration operational",
            )
        except Exception as exc:
            return ProviderHealth(
                provider_name="official_docs",
                healthy=False,
                last_check=datetime.now(),
                message=str(exc),
            )

    def capabilities(self) -> list[str]:
        return ["documentation_lookup", "version_discovery", "release_notes"]

    def _verify_connection(self) -> None:
        if not self._initialized:
            raise ProviderUnavailableError("OfficialDocsIntegration not initialized")

    def _request(self, url: str) -> dict[str, Any]:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": self._user_agent},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                if resp.status != 200:
                    raise ProviderExecutionError(
                        f"Docs API returned status {resp.status}"
                    )
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise ProviderExecutionError(
                f"Docs API error {exc.code}: {exc.reason}"
            ) from exc
        except urllib.error.URLError as exc:
            raise ProviderUnavailableError(
                f"Docs API unavailable: {exc}"
            ) from exc
        except Exception as exc:
            raise ProviderExecutionError(
                f"Docs request failed: {exc}"
            ) from exc

    def lookup_documentation(
        self, product: str, version: str | None = None,
    ) -> list[KnowledgeSource]:
        start = time.time()
        self._logger.info(
            "provider=official_docs capability=documentation_lookup product=%s version=%s",
            product, version or "latest",
        )
        try:
            self._verify_connection()
            params: dict[str, str] = {"product": product}
            if version:
                params["version"] = version
            url = f"{self._base_url}/docs?{urllib.parse.urlencode(params)}"
            body = self._request(url)
            sources = self._normalize_documentation(body, product, version)
            duration = (time.time() - start) * 1000
            self._logger.info(
                "provider=official_docs capability=documentation_lookup status=success results=%d duration_ms=%.1f",
                len(sources), duration,
            )
            return sources
        except (ProviderExecutionError, ProviderUnavailableError, ProviderConfigurationError):
            raise
        except Exception as exc:
            duration = (time.time() - start) * 1000
            self._logger.warning(
                "provider=official_docs capability=documentation_lookup status=error duration_ms=%.1f error=%s",
                duration, str(exc),
            )
            raise ProviderExecutionError(
                f"Official docs lookup failed: {exc}"
            ) from exc

    def _normalize_documentation(
        self, body: dict[str, Any], product: str, version: str | None,
    ) -> list[KnowledgeSource]:
        sources: list[KnowledgeSource] = []
        docs_list = body if isinstance(body, list) else body.get("docs", body.get("pages", []))
        for doc in docs_list:
            published = None
            if doc.get("updated_at") or doc.get("last_updated"):
                try:
                    published = datetime.fromisoformat(
                        doc.get("updated_at") or doc.get("last_updated", "")
                    )
                except (ValueError, TypeError):
                    published = None
            sources.append(KnowledgeSource(
                id=f"docs_{product}_{doc.get('id', doc.get('slug', ''))}",
                name=doc.get("title", doc.get("name", "")),
                source_type=KnowledgeSourceType.OFFICIAL_DOCUMENTATION,
                provider="official_docs",
                base_url=doc.get("url", doc.get("link", "")),
                credibility_score=1.0,
                priority=80,
                enabled=True,
                last_checked=published,
            ))
        return sources

    def discover_versions(self, product: str) -> list[KnowledgeVersion]:
        start = time.time()
        self._logger.info(
            "provider=official_docs capability=version_discovery product=%s", product,
        )
        try:
            self._verify_connection()
            url = f"{self._base_url}/versions?{urllib.parse.urlencode({'product': product})}"
            body = self._request(url)
            versions = self._normalize_versions(body, product)
            duration = (time.time() - start) * 1000
            self._logger.info(
                "provider=official_docs capability=version_discovery status=success results=%d duration_ms=%.1f",
                len(versions), duration,
            )
            return versions
        except (ProviderExecutionError, ProviderUnavailableError, ProviderConfigurationError):
            raise
        except Exception as exc:
            duration = (time.time() - start) * 1000
            self._logger.warning(
                "provider=official_docs capability=version_discovery status=error duration_ms=%.1f error=%s",
                duration, str(exc),
            )
            raise ProviderExecutionError(
                f"Official docs version discovery failed: {exc}"
            ) from exc

    def _normalize_versions(
        self, body: dict[str, Any], product: str,
    ) -> list[KnowledgeVersion]:
        versions: list[KnowledgeVersion] = []
        ver_list = body if isinstance(body, list) else body.get("versions", [])
        for ver in ver_list:
            created = None
            if ver.get("release_date") or ver.get("created_at"):
                try:
                    created = datetime.fromisoformat(
                        ver.get("release_date") or ver.get("created_at", "")
                    )
                except (ValueError, TypeError):
                    created = None
            versions.append(KnowledgeVersion(
                id=f"ver_{product}_{ver.get('version', ver.get('id', ''))}",
                version=ver.get("version", ver.get("name", "0.1.0")),
                created_at=created,
                changes=ver.get("changes", ver.get("release_notes", [])),
            ))
        return versions

    def get_release_notes(
        self, product: str, version: str,
    ) -> list[KnowledgeSource]:
        start = time.time()
        self._logger.info(
            "provider=official_docs capability=release_notes product=%s version=%s",
            product, version,
        )
        try:
            self._verify_connection()
            params = urllib.parse.urlencode({
                "product": product,
                "version": version,
            })
            url = f"{self._base_url}/release-notes?{params}"
            body = self._request(url)
            sources = self._normalize_documentation(body, product, version)
            duration = (time.time() - start) * 1000
            self._logger.info(
                "provider=official_docs capability=release_notes status=success results=%d duration_ms=%.1f",
                len(sources), duration,
            )
            return sources
        except (ProviderExecutionError, ProviderUnavailableError, ProviderConfigurationError):
            raise
        except Exception as exc:
            duration = (time.time() - start) * 1000
            self._logger.warning(
                "provider=official_docs capability=release_notes status=error duration_ms=%.1f error=%s",
                duration, str(exc),
            )
            raise ProviderExecutionError(
                f"Official docs release notes failed: {exc}"
            ) from exc
