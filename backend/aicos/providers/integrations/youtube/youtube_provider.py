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
from ....knowledge_intelligence.enums import KnowledgeSourceType, ResourceType
from ....knowledge_intelligence.models import (
    KnowledgeResource,
    KnowledgeSource,
)


class YouTubeIntegration:
    def __init__(self, config: dict | None = None) -> None:
        self._config = config or {}
        self._logger = get_logger("providers.integrations.youtube")
        self._api_key = self._config.get("api_key", "")
        self._base_url = self._config.get(
            "endpoint", "https://www.googleapis.com/youtube/v3"
        )
        self._timeout = self._config.get("timeout", 30)
        self._retry_count = self._config.get("retry_count", 3)
        self._user_agent = self._config.get("user_agent", "AICOS/0.1.0")
        self._initialized = False

    @property
    def provider_name(self) -> str:
        return "youtube"

    def initialize(self) -> None:
        self._logger.debug("YouTubeIntegration initializing")
        self._initialized = True

    def shutdown(self) -> None:
        self._logger.debug("YouTubeIntegration shutting down")
        self._initialized = False

    def health(self) -> ProviderHealth:
        try:
            self._verify_connection()
            return ProviderHealth(
                provider_name="youtube",
                healthy=True,
                last_check=datetime.now(),
                message="youtube integration operational",
            )
        except Exception as exc:
            return ProviderHealth(
                provider_name="youtube",
                healthy=False,
                last_check=datetime.now(),
                message=str(exc),
            )

    def capabilities(self) -> list[str]:
        return ["video_discovery", "channel_discovery", "playlist_discovery"]

    def _verify_connection(self) -> None:
        if not self._initialized:
            raise ProviderUnavailableError("YouTubeIntegration not initialized")

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
                        f"YouTube API returned status {resp.status}"
                    )
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 403:
                raise ProviderUnavailableError(
                    "YouTube API quota exceeded"
                ) from exc
            raise ProviderExecutionError(
                f"YouTube API error {exc.code}: {exc.reason}"
            ) from exc
        except urllib.error.URLError as exc:
            raise ProviderUnavailableError(
                f"YouTube API unavailable: {exc}"
            ) from exc
        except Exception as exc:
            raise ProviderExecutionError(
                f"YouTube request failed: {exc}"
            ) from exc

    def discover_videos(self, query: str) -> list[KnowledgeResource]:
        start = time.time()
        self._logger.info(
            "provider=youtube capability=video_discovery query=%s", query,
        )
        try:
            self._verify_connection()
            params = urllib.parse.urlencode({
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": 10,
                "key": self._api_key,
            })
            url = f"{self._base_url}/search?{params}"
            body = self._request(url)
            resources = self._normalize_videos(body)
            duration = (time.time() - start) * 1000
            self._logger.info(
                "provider=youtube capability=video_discovery status=success results=%d duration_ms=%.1f",
                len(resources), duration,
            )
            return resources
        except (ProviderExecutionError, ProviderUnavailableError, ProviderConfigurationError):
            raise
        except Exception as exc:
            duration = (time.time() - start) * 1000
            self._logger.warning(
                "provider=youtube capability=video_discovery status=error duration_ms=%.1f error=%s",
                duration, str(exc),
            )
            raise ProviderExecutionError(
                f"YouTube video discovery failed: {exc}"
            ) from exc

    def _normalize_videos(self, body: dict[str, Any]) -> list[KnowledgeResource]:
        resources: list[KnowledgeResource] = []
        for item in body.get("items", []):
            snippet = item.get("snippet", {})
            published = None
            if snippet.get("publishedAt"):
                try:
                    published = datetime.fromisoformat(
                        snippet["publishedAt"].replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    published = None
            resources.append(KnowledgeResource(
                id=f"yt_video_{item.get('id', {}).get('videoId', '')}",
                title=snippet.get("title", ""),
                resource_type=ResourceType.VIDEO,
                provider="youtube",
                url=f"https://www.youtube.com/watch?v={item.get('id', {}).get('videoId', '')}",
                language="en",
                quality_score=0.7,
                difficulty="intermediate",
                last_verified=published,
            ))
        return resources

    def discover_channels(self, query: str) -> list[KnowledgeSource]:
        start = time.time()
        self._logger.info(
            "provider=youtube capability=channel_discovery query=%s", query,
        )
        try:
            self._verify_connection()
            params = urllib.parse.urlencode({
                "part": "snippet",
                "q": query,
                "type": "channel",
                "maxResults": 10,
                "key": self._api_key,
            })
            url = f"{self._base_url}/search?{params}"
            body = self._request(url)
            sources = self._normalize_channels(body)
            duration = (time.time() - start) * 1000
            self._logger.info(
                "provider=youtube capability=channel_discovery status=success results=%d duration_ms=%.1f",
                len(sources), duration,
            )
            return sources
        except (ProviderExecutionError, ProviderUnavailableError, ProviderConfigurationError):
            raise
        except Exception as exc:
            duration = (time.time() - start) * 1000
            self._logger.warning(
                "provider=youtube capability=channel_discovery status=error duration_ms=%.1f error=%s",
                duration, str(exc),
            )
            raise ProviderExecutionError(
                f"YouTube channel discovery failed: {exc}"
            ) from exc

    def _normalize_channels(self, body: dict[str, Any]) -> list[KnowledgeSource]:
        sources: list[KnowledgeSource] = []
        for item in body.get("items", []):
            snippet = item.get("snippet", {})
            channel_id = item.get("id", {}).get("channelId", "")
            sources.append(KnowledgeSource(
                id=f"yt_channel_{channel_id}",
                name=snippet.get("title", ""),
                source_type=KnowledgeSourceType.YOUTUBE,
                provider="youtube",
                base_url=f"https://www.youtube.com/channel/{channel_id}",
                credibility_score=0.7,
                priority=50,
                enabled=True,
            ))
        return sources

    def discover_playlists(self, query: str) -> list[KnowledgeResource]:
        start = time.time()
        self._logger.info(
            "provider=youtube capability=playlist_discovery query=%s", query,
        )
        try:
            self._verify_connection()
            params = urllib.parse.urlencode({
                "part": "snippet",
                "q": query,
                "type": "playlist",
                "maxResults": 10,
                "key": self._api_key,
            })
            url = f"{self._base_url}/search?{params}"
            body = self._request(url)
            resources = self._normalize_playlists(body)
            duration = (time.time() - start) * 1000
            self._logger.info(
                "provider=youtube capability=playlist_discovery status=success results=%d duration_ms=%.1f",
                len(resources), duration,
            )
            return resources
        except (ProviderExecutionError, ProviderUnavailableError, ProviderConfigurationError):
            raise
        except Exception as exc:
            duration = (time.time() - start) * 1000
            self._logger.warning(
                "provider=youtube capability=playlist_discovery status=error duration_ms=%.1f error=%s",
                duration, str(exc),
            )
            raise ProviderExecutionError(
                f"YouTube playlist discovery failed: {exc}"
            ) from exc

    def _normalize_playlists(self, body: dict[str, Any]) -> list[KnowledgeResource]:
        resources: list[KnowledgeResource] = []
        for item in body.get("items", []):
            snippet = item.get("snippet", {})
            playlist_id = item.get("id", {}).get("playlistId", "")
            published = None
            if snippet.get("publishedAt"):
                try:
                    published = datetime.fromisoformat(
                        snippet["publishedAt"].replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    published = None
            resources.append(KnowledgeResource(
                id=f"yt_playlist_{playlist_id}",
                title=snippet.get("title", ""),
                resource_type=ResourceType.VIDEO,
                provider="youtube",
                url=f"https://www.youtube.com/playlist?list={playlist_id}",
                language="en",
                quality_score=0.7,
                difficulty="intermediate",
                last_verified=published,
            ))
        return resources
