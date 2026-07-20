# Knowledge Intelligence Domain

## Architecture

```
Application
      │
      ▼
KnowledgeIntelligenceDomainService
      │
      ▼
  ┌──────────────────────────────────────────┐
  │  Domain Models (pure data)               │
  │  Enums                                   │
  │  Validation (pure functions)             │
  │  Exceptions                              │
  └──────────────────────────────────────────┘
```

No AI, retrieval, or infrastructure dependencies.

## Domain Models

| Entity | Fields | Purpose |
|---|---|---|
| `KnowledgeSource` | id, name, source_type, provider, base_url, credibility_score, priority, enabled, last_checked | A tracked knowledge origin |
| `TechnologySignal` | id, name, summary, category, first_seen, status, importance, confidence_score, evidence | A newly discovered technology |
| `Evidence` | id, source, title, url, published_at, author, confidence | Supporting evidence for a signal |
| `TrendSnapshot` | technology, adoption_score, community_score, industry_score, job_market_score, github_score, youtube_score, overall_score, captured_at | Technology popularity measurement |
| `KnowledgeResource` | id, title, resource_type, provider, url, language, estimated_duration, quality_score, difficulty, last_verified, relevant_tracks | A curated learning resource |
| `ResourceCollection` | technology, resources, last_updated | Grouped resources by technology |
| `TechnologyLifecycleEvent` | technology, previous_status, new_status, reason, changed_at | Lifecycle transition record |
| `KnowledgeVersion` | id, version, created_at, changes | Repository version snapshot |
| `DiscoveryJob` | id, job_type, target, schedule, enabled, last_run, next_run | Future acquisition job definition |

## Entity Relationships

```
KnowledgeSource (independent, tracked origins)

TechnologySignal
  └── evidence: list[Evidence]

Evidence (can be shared across signals or standalone)

TrendSnapshot (independent, per-technology measurement)

KnowledgeResource
  ├── resource_type: ResourceType
  └── relevant_tracks: list[str]

ResourceCollection
  ├── technology → TrendSnapshot.technology
  └── resources: list[KnowledgeResource]

TechnologyLifecycleEvent
  ├── technology → TrendSnapshot.technology
  ├── previous_status: TechnologyStatus
  └── new_status: TechnologyStatus

KnowledgeVersion (independent, tracks repo state)

DiscoveryJob (independent, defines acquisition schedule)
```

## Enums

| Enum | Values |
|---|---|
| `KnowledgeSourceType` | official_documentation, github, youtube, x, research_paper, blog, conference, company, community |
| `TechnologyStatus` | experimental, emerging, growing, recommended, industry_standard, legacy, deprecated |
| `ResourceType` | documentation, video, repository, course, book, article, workshop |
| `JobType` | technology_discovery, resource_refresh, trend_analysis, verification, knowledge_versioning |

## Knowledge Lifecycle

```
TechnologySignal (discovery)
      │
      ▼
TrendSnapshot (measurement cycle)
      │
      ▼
TechnologyLifecycleEvent (status transitions)
      │
      ▼
KnowledgeResource (curated learning content)
      │
      ▼
ResourceCollection (organized by technology)
```

- Signals are discovered and promoted through `TechnologyStatus` stages.
- Trends are captured periodically as `TrendSnapshot` records.
- Lifecycle events track each status transition with reasoning.
- Resources are curated into collections per technology.

## Validation Rules

| Validator | Rules |
|---|---|
| `validate_sources()` | Non-empty id/name; no duplicate ids; credibility_score ∈ [0,1]; priority ∈ [0,100]; valid source_type enum |
| `validate_signals()` | Non-empty id/name/summary; no duplicate ids; importance ∈ [0,10]; confidence_score ∈ [0,1]; valid status enum; no duplicate evidence ids within signal |
| `validate_evidence()` | Non-empty id/source/title; no duplicate ids; no duplicate urls; confidence ∈ [0,1] |
| `validate_resources()` | Non-empty id/title; no duplicate ids; no duplicate urls; quality_score ∈ [0,1]; valid resource_type enum |
| `validate_trends()` | Non-empty technology; no duplicate technologies; all scores ∈ [0,1] |
| `validate_versions()` | Non-empty id; non-empty version string; no duplicate ids |
| `validate_jobs()` | Non-empty id/target; no duplicate ids; valid job_type enum |

## Domain Service

`KnowledgeIntelligenceDomainService` provides seven validation methods:

| Method | Validates | Raises |
|---|---|---|
| `validate_sources()` | list[KnowledgeSource] | `SourceValidationError` |
| `validate_signals()` | list[TechnologySignal] | `SignalValidationError` |
| `validate_evidence()` | list[Evidence] | `EvidenceValidationError` |
| `validate_resources()` | list[KnowledgeResource] | `ResourceValidationError` |
| `validate_trends()` | list[TrendSnapshot] | `TrendValidationError` |
| `validate_versions()` | list[KnowledgeVersion] | `VersionValidationError` |
| `validate_jobs()` | list[DiscoveryJob] | `JobValidationError` |

## Exception Hierarchy

```
KnowledgeDomainError
├── SourceValidationError
├── SignalValidationError
├── EvidenceValidationError
├── ResourceValidationError
├── TrendValidationError
├── VersionValidationError
└── JobValidationError
```

## Dependency Injection

```python
from aicos.knowledge_intelligence import register_knowledge_intelligence, KnowledgeIntelligenceDomainService

register_knowledge_intelligence(container, settings)
service = container.resolve(KnowledgeIntelligenceDomainService)
```

## Logging

Logger name: `aicos.knowledge_intelligence`

Logged at `DEBUG` on validation success, `WARNING` on validation failure:
- source_count
- signal_count
- evidence_count
- resource_count
- trend_count
- version_count
- job_count

Entity details and URLs are never logged.

## Extension Points

- **New model**: add a frozen dataclass to `models.py`
- **New enum**: add to `enums.py`
- **New validation**: add a pure function to `validation.py`, expose via `KnowledgeIntelligenceDomainService`
- **Custom service**: implement `KnowledgeIntelligenceDomainServiceProtocol`
- **New source type**: add value to `KnowledgeSourceType`
- **New job type**: add value to `JobType`

## Dependency Graph

```
knowledge_intelligence
  ├── enums
  ├── models (depends on enums)
  ├── exceptions
  ├── validation (depends on enums, models, exceptions)
  ├── interfaces (depends on models)
  ├── service (depends on logging, exceptions, models, validation)
  └── __init__ (depends on core.di, settings, service)
```

No external service dependencies. Pure domain layer.
