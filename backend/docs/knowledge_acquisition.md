# Knowledge Acquisition Engine

## Architecture

```
                    DiscoveryOrchestrator
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
 OfficialDocsAdapter   GitHubAdapter    YouTubeAdapter
        │                   │                   │
        ├──────────────┬────┴──────────────┬────┤
                       ▼                   ▼
                ResearchAdapter       XAdapter
                       │
                       ▼
              NormalizationService
                       │
                       ▼
         ┌─────────────────────────────┐
         │ Knowledge Intelligence      │
         │ Domain Models               │
         └─────────────────────────────┘
```

The acquisition engine discovers knowledge from external sources and
normalizes it into Knowledge Intelligence Domain models.  It does NOT
perform AI, ranking, deduplication, recommendations, or roadmap
generation.

## Discovery Flow

1. `DiscoveryOrchestrator.discover(request)` receives a `DiscoveryRequest`
2. Orchestrator looks up the adapter via `AdapterRegistry.discover(source_type)`
3. Adapter executes `discover(request)` returning a `DiscoveryResult`
4. Orchestrator measures execution duration
5. `NormalizationService.normalize(result)` validates domain models
6. Normalized `DiscoveryResult` is returned to the caller

## Adapter Lifecycle

Each adapter implements three methods:

| Method | Purpose | Returns |
|---|---|---|
| `discover(request)` | Discover new knowledge | `DiscoveryResult` |
| `refresh(request)` | Refresh previously discovered knowledge | `DiscoveryResult` |
| `verify()` | Verify adapter is operational | `AdapterHealth` |

All adapters are structural placeholders.  No network calls, APIs, HTTP,
or scraping.

## Adapters

| Adapter | Source Type | Returns |
|---|---|---|
| `OfficialDocsAdapter` | `OFFICIAL_DOCUMENTATION` | `KnowledgeSource` |
| `GitHubAdapter` | `GITHUB` | `KnowledgeSource`, `TechnologySignal` with `Evidence` |
| `YouTubeAdapter` | `YOUTUBE` | `KnowledgeSource`, `KnowledgeResource` |
| `ResearchAdapter` | `RESEARCH_PAPER` | `KnowledgeSource`, `TechnologySignal` |
| `XAdapter` | `X` | `KnowledgeSource`, `TechnologySignal` with `Evidence` |

## Registry

`AdapterRegistry` maintains a mapping of `KnowledgeSourceType` to
`KnowledgeAdapter`.

| Method | Purpose |
|---|---|
| `register(adapter)` | Register an adapter; raises `AdapterRegistrationError` on duplicate or non-protocol |
| `lookup(source_type)` | Look up adapter; returns `None` if not found |
| `discover(source_type)` | Look up adapter; raises `AdapterRegistrationError` if not found |
| `registered_types` | List of registered source types |
| `registered_adapters` | List of registered adapter instances |
| `count` | Number of registered adapters |

## Normalization

`NormalizationService` validates adapter output against the Knowledge
Intelligence domain:

- Validates `KnowledgeSource` entities via `validate_sources()`
- Validates `TechnologySignal` entities via `validate_signals()`
- Validates `KnowledgeResource` entities via `validate_resources()`
- Validates `TrendSnapshot` entities via `validate_trends()`

Only normalization — no business decisions, no AI.

## Acquisition Models

| Model | Purpose |
|---|---|
| `DiscoveryRequest` | Input to an adapter's discover/refresh methods |
| `DiscoveryResult` | Output from an adapter containing domain models |
| `AdapterHealth` | Result of an adapter verify operation |
| `AcquisitionStatistics` | Statistics tracking across acquisitions |

## Exception Hierarchy

```
KnowledgeAcquisitionError
├── AdapterRegistrationError
├── AdapterExecutionError
├── NormalizationError
└── DiscoveryError
```

## Dependency Injection

```python
from aicos.knowledge_acquisition import register_knowledge_acquisition, DiscoveryOrchestrator

register_knowledge_acquisition(container, settings)
orchestrator = container.resolve(DiscoveryOrchestrator)
```

Registered components (application resolves only `DiscoveryOrchestrator`):

- `NormalizationService` (singleton)
- `AdapterRegistry` (singleton, factory-populated with 5 adapters)
- `DiscoveryOrchestrator` (singleton)

## Logging

Logger name: `aicos.knowledge_acquisition`

Logged events:
- Adapter execution (INFO)
- Adapter failures (WARNING)
- Normalization counts (DEBUG / INFO)
- Adapter verification (INFO)
- Execution duration (via DiscoveryResult.duration_ms)

Credentials, tokens, and secrets are never logged.

## Extension Points

| Point | Mechanism |
|---|---|
| **New data source** | Implement `KnowledgeAdapter` ABC, register via `AdapterRegistry` |
| **Custom normalization** | Implement `NormalizationServiceProtocol` |
| **Custom orchestrator** | Implement `DiscoveryOrchestratorProtocol` |
| **New source type** | Add value to `KnowledgeSourceType` enum |
| **Adapter config** | Pass via `DiscoveryRequest.config` dict |

## Dependency Graph

```
knowledge_acquisition
  ├── knowledge_intelligence (models, enums, interfaces)
  ├── core.di (DI registration)
  ├── settings
  ├── exceptions
  ├── models (acquisition + domain)
  ├── interfaces (protocols)
  ├── adapters/
  │   ├── base (ABC)
  │   ├── official_docs
  │   ├── github
  │   ├── youtube
  │   ├── research
  │   └── x
  ├── registry
  ├── normalizer (depends on domain service protocol)
  ├── orchestrator (depends on registry + normalizer protocol)
  └── __init__ (DI wiring)
```

No HTTP, MCP, AI, RAG, embeddings, vector store, or scheduling
dependencies.
