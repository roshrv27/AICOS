"""Knowledge intelligence domain service.

``KnowledgeIntelligenceDomainService`` validates domain entities and
enforces business rules without AI, retrieval, or infrastructure
dependencies.
"""

from __future__ import annotations

from ..logging import get_logger
from .exceptions import (
    EvidenceValidationError,
    JobValidationError,
    ResourceValidationError,
    SignalValidationError,
    SourceValidationError,
    TrendValidationError,
    VersionValidationError,
)
from .models import (
    DiscoveryJob,
    Evidence,
    KnowledgeResource,
    KnowledgeSource,
    KnowledgeVersion,
    TechnologySignal,
    TrendSnapshot,
)
from .validation import (
    validate_evidence,
    validate_jobs,
    validate_resources,
    validate_signals,
    validate_sources,
    validate_trends,
    validate_versions,
)


class KnowledgeIntelligenceDomainService:
    def __init__(self) -> None:
        self._logger = get_logger("knowledge_intelligence")

    def validate_sources(self, sources: list[KnowledgeSource]) -> None:
        try:
            validate_sources(sources)
            self._logger.debug(
                "source validation passed",
                extra={"source_count": len(sources)},
            )
        except SourceValidationError:
            self._logger.warning(
                "source validation failed",
                extra={"source_count": len(sources)},
            )
            raise

    def validate_signals(self, signals: list[TechnologySignal]) -> None:
        try:
            validate_signals(signals)
            self._logger.debug(
                "signal validation passed",
                extra={"signal_count": len(signals)},
            )
        except SignalValidationError:
            self._logger.warning(
                "signal validation failed",
                extra={"signal_count": len(signals)},
            )
            raise

    def validate_evidence(self, evidence_list: list[Evidence]) -> None:
        try:
            validate_evidence(evidence_list)
            self._logger.debug(
                "evidence validation passed",
                extra={"evidence_count": len(evidence_list)},
            )
        except EvidenceValidationError:
            self._logger.warning(
                "evidence validation failed",
                extra={"evidence_count": len(evidence_list)},
            )
            raise

    def validate_resources(self, resources: list[KnowledgeResource]) -> None:
        try:
            validate_resources(resources)
            self._logger.debug(
                "resource validation passed",
                extra={"resource_count": len(resources)},
            )
        except ResourceValidationError:
            self._logger.warning(
                "resource validation failed",
                extra={"resource_count": len(resources)},
            )
            raise

    def validate_trends(self, trends: list[TrendSnapshot]) -> None:
        try:
            validate_trends(trends)
            self._logger.debug(
                "trend validation passed",
                extra={"trend_count": len(trends)},
            )
        except TrendValidationError:
            self._logger.warning(
                "trend validation failed",
                extra={"trend_count": len(trends)},
            )
            raise

    def validate_versions(self, versions: list[KnowledgeVersion]) -> None:
        try:
            validate_versions(versions)
            self._logger.debug(
                "version validation passed",
                extra={"version_count": len(versions)},
            )
        except VersionValidationError:
            self._logger.warning(
                "version validation failed",
                extra={"version_count": len(versions)},
            )
            raise

    def validate_jobs(self, jobs: list[DiscoveryJob]) -> None:
        try:
            validate_jobs(jobs)
            self._logger.debug(
                "job validation passed",
                extra={"job_count": len(jobs)},
            )
        except JobValidationError:
            self._logger.warning(
                "job validation failed",
                extra={"job_count": len(jobs)},
            )
            raise
