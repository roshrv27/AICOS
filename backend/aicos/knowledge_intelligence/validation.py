"""Domain validation for knowledge intelligence entities.

Validators are pure functions with no side effects.  Each raises the
appropriate exception from ``.exceptions``.
"""

from __future__ import annotations

from .enums import JobType, KnowledgeSourceType, ResourceType, TechnologyStatus
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


def validate_sources(sources: list[KnowledgeSource]) -> None:
    seen: set[str] = set()
    for s in sources:
        if not s.id:
            raise SourceValidationError("source id must not be empty")
        if not s.name.strip():
            raise SourceValidationError(f"source name must not be empty (id={s.id})")
        if s.id in seen:
            raise SourceValidationError(f"duplicate source id: {s.id}")
        seen.add(s.id)
        if not 0.0 <= s.credibility_score <= 1.0:
            raise SourceValidationError(
                f"credibility_score must be between 0.0 and 1.0 (source={s.id})"
            )
        if not 0 <= s.priority <= 100:
            raise SourceValidationError(
                f"priority must be between 0 and 100 (source={s.id})"
            )
        if s.source_type not in KnowledgeSourceType.__members__.values():
            raise SourceValidationError(
                f"invalid source_type for source {s.id}: {s.source_type}"
            )


def validate_signals(signals: list[TechnologySignal]) -> None:
    seen: set[str] = set()
    for sig in signals:
        if not sig.id:
            raise SignalValidationError("signal id must not be empty")
        if not sig.name.strip():
            raise SignalValidationError(f"signal name must not be empty (id={sig.id})")
        if not sig.summary.strip():
            raise SignalValidationError(f"signal summary must not be empty (id={sig.id})")
        if sig.id in seen:
            raise SignalValidationError(f"duplicate signal id: {sig.id}")
        seen.add(sig.id)
        if not 0 <= sig.importance <= 10:
            raise SignalValidationError(
                f"importance must be between 0 and 10 (signal={sig.id})"
            )
        if not 0.0 <= sig.confidence_score <= 1.0:
            raise SignalValidationError(
                f"confidence_score must be between 0.0 and 1.0 (signal={sig.id})"
            )
        if sig.status not in TechnologyStatus.__members__.values():
            raise SignalValidationError(
                f"invalid status for signal {sig.id}: {sig.status}"
            )
        if sig.evidence:
            evidence_seen: set[str] = set()
            for ev in sig.evidence:
                if ev.id in evidence_seen:
                    raise SignalValidationError(
                        f"duplicate evidence id {ev.id} in signal {sig.id}"
                    )
                evidence_seen.add(ev.id)


def validate_evidence(evidence_list: list[Evidence]) -> None:
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    for ev in evidence_list:
        if not ev.id:
            raise EvidenceValidationError("evidence id must not be empty")
        if not ev.source.strip():
            raise EvidenceValidationError(
                f"evidence source must not be empty (id={ev.id})"
            )
        if not ev.title.strip():
            raise EvidenceValidationError(
                f"evidence title must not be empty (id={ev.id})"
            )
        if ev.id in seen_ids:
            raise EvidenceValidationError(f"duplicate evidence id: {ev.id}")
        seen_ids.add(ev.id)
        if ev.url:
            if ev.url in seen_urls:
                raise EvidenceValidationError(f"duplicate evidence url: {ev.url}")
            seen_urls.add(ev.url)
        if not 0.0 <= ev.confidence <= 1.0:
            raise EvidenceValidationError(
                f"confidence must be between 0.0 and 1.0 (evidence={ev.id})"
            )


def validate_resources(resources: list[KnowledgeResource]) -> None:
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    for r in resources:
        if not r.id:
            raise ResourceValidationError("resource id must not be empty")
        if not r.title.strip():
            raise ResourceValidationError(f"resource title must not be empty (id={r.id})")
        if r.id in seen_ids:
            raise ResourceValidationError(f"duplicate resource id: {r.id}")
        seen_ids.add(r.id)
        if r.url:
            if r.url in seen_urls:
                raise ResourceValidationError(f"duplicate resource url: {r.url}")
            seen_urls.add(r.url)
        if not 0.0 <= r.quality_score <= 1.0:
            raise ResourceValidationError(
                f"quality_score must be between 0.0 and 1.0 (resource={r.id})"
            )
        if r.resource_type not in ResourceType.__members__.values():
            raise ResourceValidationError(
                f"invalid resource_type for resource {r.id}: {r.resource_type}"
            )


def validate_trends(trends: list[TrendSnapshot]) -> None:
    seen: set[str] = set()
    for t in trends:
        if not t.technology.strip():
            raise TrendValidationError("trend technology must not be empty")
        if t.technology in seen:
            raise TrendValidationError(f"duplicate trend technology: {t.technology}")
        seen.add(t.technology)
        for field_name, val in [
            ("adoption_score", t.adoption_score),
            ("community_score", t.community_score),
            ("industry_score", t.industry_score),
            ("job_market_score", t.job_market_score),
            ("github_score", t.github_score),
            ("youtube_score", t.youtube_score),
            ("overall_score", t.overall_score),
        ]:
            if not 0.0 <= val <= 1.0:
                raise TrendValidationError(
                    f"{field_name} must be between 0.0 and 1.0 "
                    f"(technology={t.technology})"
                )


def validate_versions(versions: list[KnowledgeVersion]) -> None:
    seen: set[str] = set()
    for v in versions:
        if not v.id:
            raise VersionValidationError("version id must not be empty")
        if not v.version.strip():
            raise VersionValidationError(f"version string must not be empty (id={v.id})")
        if v.id in seen:
            raise VersionValidationError(f"duplicate version id: {v.id}")
        seen.add(v.id)


def validate_jobs(jobs: list[DiscoveryJob]) -> None:
    seen: set[str] = set()
    for j in jobs:
        if not j.id:
            raise JobValidationError("job id must not be empty")
        if not j.target.strip():
            raise JobValidationError(f"job target must not be empty (id={j.id})")
        if j.id in seen:
            raise JobValidationError(f"duplicate job id: {j.id}")
        seen.add(j.id)
        if j.job_type not in JobType.__members__.values():
            raise JobValidationError(
                f"invalid job_type for job {j.id}: {j.job_type}"
            )
