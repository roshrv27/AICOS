from __future__ import annotations

import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
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


ARXIV_NS = "http://www.w3.org/2005/Atom"
ARXIV_API = "http://arxiv.org/api/query"


class ArxivIntegration:
    def __init__(self, config: dict | None = None) -> None:
        self._config = config or {}
        self._logger = get_logger("providers.integrations.arxiv")
        self._base_url = self._config.get("endpoint", ARXIV_API)
        self._timeout = self._config.get("timeout", 30)
        self._retry_count = self._config.get("retry_count", 3)
        self._user_agent = self._config.get(
            "user_agent", "AICOS/0.1.0 (mailto:research@aicos.dev)"
        )
        self._initialized = False

    @property
    def provider_name(self) -> str:
        return "research"

    def initialize(self) -> None:
        self._logger.debug("ArxivIntegration initializing")
        self._initialized = True

    def shutdown(self) -> None:
        self._logger.debug("ArxivIntegration shutting down")
        self._initialized = False

    def health(self) -> ProviderHealth:
        try:
            self._verify_connection()
            return ProviderHealth(
                provider_name="research",
                healthy=True,
                last_check=datetime.now(),
                message="arxiv integration operational",
            )
        except Exception as exc:
            return ProviderHealth(
                provider_name="research",
                healthy=False,
                last_check=datetime.now(),
                message=str(exc),
            )

    def capabilities(self) -> list[str]:
        return ["paper_discovery", "author_lookup", "topic_search"]

    def _verify_connection(self) -> None:
        if not self._initialized:
            raise ProviderUnavailableError("ArxivIntegration not initialized")

    def _request(self, url: str) -> str:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": self._user_agent},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                if resp.status != 200:
                    raise ProviderExecutionError(
                        f"Arxiv API returned status {resp.status}"
                    )
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raise ProviderExecutionError(
                f"Arxiv API error {exc.code}: {exc.reason}"
            ) from exc
        except urllib.error.URLError as exc:
            raise ProviderUnavailableError(
                f"Arxiv API unavailable: {exc}"
            ) from exc
        except Exception as exc:
            raise ProviderExecutionError(
                f"Arxiv request failed: {exc}"
            ) from exc

    def discover_papers(self, query: str) -> list[KnowledgeSource]:
        start = time.time()
        self._logger.info(
            "provider=arxiv capability=paper_discovery query=%s", query,
        )
        try:
            self._verify_connection()
            params = urllib.parse.urlencode({
                "search_query": f"all:{query}",
                "max_results": 10,
                "sortBy": "relevance",
                "sortOrder": "descending",
            })
            url = f"{self._base_url}?{params}"
            xml_body = self._request(url)
            sources = self._normalize_papers(xml_body)
            duration = (time.time() - start) * 1000
            self._logger.info(
                "provider=arxiv capability=paper_discovery status=success results=%d duration_ms=%.1f",
                len(sources), duration,
            )
            return sources
        except (ProviderExecutionError, ProviderUnavailableError, ProviderConfigurationError):
            raise
        except Exception as exc:
            duration = (time.time() - start) * 1000
            self._logger.warning(
                "provider=arxiv capability=paper_discovery status=error duration_ms=%.1f error=%s",
                duration, str(exc),
            )
            raise ProviderExecutionError(
                f"Arxiv paper discovery failed: {exc}"
            ) from exc

    def _normalize_papers(self, xml_body: str) -> list[KnowledgeSource]:
        sources: list[KnowledgeSource] = []
        root = ET.fromstring(xml_body)
        for entry in root.findall(f"{{{ARXIV_NS}}}entry"):
            paper_id = entry.find(f"{{{ARXIV_NS}}}id")
            title = entry.find(f"{{{ARXIV_NS}}}title")
            summary = entry.find(f"{{{ARXIV_NS}}}summary")
            published = entry.find(f"{{{ARXIV_NS}}}published")

            published_dt = None
            if published is not None and published.text:
                try:
                    published_dt = datetime.fromisoformat(
                        published.text.replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    published_dt = None

            sources.append(KnowledgeSource(
                id=f"arxiv_{paper_id.text.split('/')[-1] if paper_id is not None and paper_id.text else ''}",
                name=(title.text or "").replace("\n", " ").strip()
                if title is not None else "",
                source_type=KnowledgeSourceType.RESEARCH_PAPER,
                provider="arxiv",
                base_url=paper_id.text if paper_id is not None else "",
                credibility_score=0.9,
                priority=60,
                enabled=True,
                last_checked=published_dt,
            ))
        return sources

    def author_lookup(self, author: str) -> list[KnowledgeSource]:
        start = time.time()
        self._logger.info(
            "provider=arxiv capability=author_lookup author=%s", author,
        )
        try:
            self._verify_connection()
            params = urllib.parse.urlencode({
                "search_query": f"au:{author}",
                "max_results": 10,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            })
            url = f"{self._base_url}?{params}"
            xml_body = self._request(url)
            sources = self._normalize_papers(xml_body)
            duration = (time.time() - start) * 1000
            self._logger.info(
                "provider=arxiv capability=author_lookup status=success results=%d duration_ms=%.1f",
                len(sources), duration,
            )
            return sources
        except (ProviderExecutionError, ProviderUnavailableError, ProviderConfigurationError):
            raise
        except Exception as exc:
            duration = (time.time() - start) * 1000
            self._logger.warning(
                "provider=arxiv capability=author_lookup status=error duration_ms=%.1f error=%s",
                duration, str(exc),
            )
            raise ProviderExecutionError(
                f"Arxiv author lookup failed: {exc}"
            ) from exc

    def search_topics(self, topic: str) -> list[TechnologySignal]:
        start = time.time()
        self._logger.info(
            "provider=arxiv capability=topic_search topic=%s", topic,
        )
        try:
            self._verify_connection()
            params = urllib.parse.urlencode({
                "search_query": f"cat:{topic}",
                "max_results": 10,
                "sortBy": "relevance",
                "sortOrder": "descending",
            })
            url = f"{self._base_url}?{params}"
            xml_body = self._request(url)
            signals = self._normalize_topic_signals(xml_body, topic)
            duration = (time.time() - start) * 1000
            self._logger.info(
                "provider=arxiv capability=topic_search status=success results=%d duration_ms=%.1f",
                len(signals), duration,
            )
            return signals
        except (ProviderExecutionError, ProviderUnavailableError, ProviderConfigurationError):
            raise
        except Exception as exc:
            duration = (time.time() - start) * 1000
            self._logger.warning(
                "provider=arxiv capability=topic_search status=error duration_ms=%.1f error=%s",
                duration, str(exc),
            )
            raise ProviderExecutionError(
                f"Arxiv topic search failed: {exc}"
            ) from exc

    def _normalize_topic_signals(
        self, xml_body: str, topic: str,
    ) -> list[TechnologySignal]:
        signals: list[TechnologySignal] = []
        root = ET.fromstring(xml_body)
        entries = root.findall(f"{{{ARXIV_NS}}}entry")
        paper_count = len(entries)
        if paper_count == 0:
            return signals

        signal = TechnologySignal(
            id=f"arxiv_topic_{topic}",
            name=f"Research activity in {topic}",
            summary=f"Found {paper_count} recent papers on {topic}",
            category="research_topic",
            first_seen=datetime.now(),
            status=TechnologyStatus.EMERGING,
            importance=min(paper_count, 10),
            confidence_score=0.9,
            evidence=[
                Evidence(
                    id=f"arxiv_topic_ev_{topic}",
                    source="arxiv",
                    title=f"Papers in {topic}",
                    url=entry.find(f"{{{ARXIV_NS}}}id").text
                    if entry.find(f"{{{ARXIV_NS}}}id") is not None else "",
                    confidence=0.9,
                )
                for entry in entries[:3]
                if entry.find(f"{{{ARXIV_NS}}}id") is not None
            ],
        )
        signals.append(signal)
        return signals
