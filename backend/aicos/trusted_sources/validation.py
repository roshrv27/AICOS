from __future__ import annotations

from .enums import Capability
from .exceptions import InvalidSourceError
from .models import TrustedKnowledgeSource


def validate_source(source: TrustedKnowledgeSource) -> None:
    if not source.id or not source.id.strip():
        raise InvalidSourceError("source id must not be empty")
    if not source.name or not source.name.strip():
        raise InvalidSourceError(f"source name must not be empty (id={source.id})")
    if source.priority < 0:
        raise InvalidSourceError(
            f"priority must be >= 0, got {source.priority}"
        )
    _validate_url(source.url, "url", source.id)
    _validate_url(source.rss_feed, "rss_feed", source.id)
    _validate_url(source.api_endpoint, "api_endpoint", source.id)


def _validate_url(url: str, field: str, source_id: str) -> None:
    if not url:
        return
    if not url.startswith(("http://", "https://")):
        raise InvalidSourceError(
            f"{field} must start with http:// or https:// (id={source_id})"
        )


def validate_source_id(id: str) -> None:
    if not id or not id.strip():
        raise InvalidSourceError("source id must not be empty")


def validate_trust_score(score: float) -> None:
    if not 0.0 <= score <= 1.0:
        raise InvalidSourceError(
            f"trust_score must be between 0.0 and 1.0, got {score}"
        )
