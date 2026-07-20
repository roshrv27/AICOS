# Provider Infrastructure

## Architecture

```
      ┌──────────────────────────────────────────┐
      │          Knowledge Acquisition Engine     │
      ├──────────────────────────────────────────┤
      │  DiscoveryOrchestrator → Adapters         │
      └──────────────────────┬───────────────────┘
                             │
                             ▼
                    ProviderRegistry
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                   ▼
   SearchProvider       GitHubProvider      YouTubeProvider
          │                                    │
          ├── MCPSearchProvider                 └── YouTubeProvider
          ├── GoogleSearchProvider
          └── DuckDuckGoSearchProvider

          ▼                  ▼                   ▼
   ResearchProvider    OfficialDocsProvider
```

The provider infrastructure is the transport layer below the Knowledge
Acquisition Engine.  Providers encapsulate transport-specific work; they
contain NO business logic.

## Provider Lifecycle

Each provider implements four methods:

| Method    | Purpose                         | Returns            |
|-----------|---------------------------------|--------------------|
| `initialize()`   | Prepare the provider (idempotent) | `None`           |
| `shutdown()`     | Tear down the provider (idempotent) | `None`         |
| `health()`       | Report operational status        | `ProviderHealth`    |
| `capabilities()` | List supported capabilities      | `list[str]`         |

All providers are structural placeholders.  No network calls, APIs, HTTP,
MCP, Google API, GitHub API, YouTube API, scraping, retry, caching, rate
limiting, scheduling, AI, RAG, embeddings, or vector stores.

## Providers

| Provider             | `provider_name`        | Capabilities                                | Protocols                  |
|----------------------|------------------------|---------------------------------------------|----------------------------|
| `MCPSearchProvider`       | `"mcp_search"`          | `search`, `suggest`                          | `ProviderProtocol`, `SearchProviderProtocol` |
| `GoogleSearchProvider`    | `"google_search"`       | `search`, `suggest`                          | `ProviderProtocol`, `SearchProviderProtocol` |
| `DuckDuckGoSearchProvider` | `"duckduckgo_search"` | `search`, `suggest`                          | `ProviderProtocol`, `SearchProviderProtocol` |
| `GitHubProvider`         | `"github"`              | `repo_search`, `trending_repos`              | `ProviderProtocol`, `GitHubProviderProtocol` |
| `YouTubeProvider`        | `"youtube"`             | `video_search`                               | `ProviderProtocol`, `YouTubeProviderProtocol` |
| `ResearchProvider`       | `"research"`            | `paper_search`                               | `ProviderProtocol`, `ResearchProviderProtocol` |
| `OfficialDocsProvider`   | `"official_docs"`       | `doc_search`                                 | `ProviderProtocol`, `OfficialDocsProviderProtocol` |

## Search Provider Methods

Search providers (`MCPSearchProvider`, `GoogleSearchProvider`,
`DuckDuckGoSearchProvider`) additionally implement:

| Method    | Input           | Return           |
|-----------|-----------------|------------------|
| `search(request)`  | `SearchRequest`   | `SearchResponse`   |
| `suggest(query)`   | `str`             | `list[str]`        |

## Registry

`ProviderRegistry` maintains a mapping of provider name to provider
instance.

| Method | Purpose |
|---|---|
| `register(provider)` | Register a provider; raises `ProviderRegistrationError` on duplicate or non-protocol |
| `lookup(name)` | Look up provider by name; returns `None` if not found |
| `discover(name)` | Look up provider by name; raises `ProviderRegistrationError` if not found |
| `lookup_by_capability(capability)` | Find providers with a given capability |
| `registered_names` | List of registered provider names |
| `registered_providers` | List of registered provider instances |
| `count` | Number of registered providers |

Name resolution order:
1. `provider.name` attribute
2. `provider.provider_name` attribute
3. fallback: `type(provider).__name__`

## Models

| Model | Purpose |
|---|---|
| `ProviderConfiguration` | Key-value config with optional validate() |
| `ProviderHealth` | Health status with provider_name, healthy, message, timestamp |
| `SearchRequest` | Input to search: query, max_results, source_filter, config |
| `SearchResult` | Single result: title, url, snippet, source, relevance_score, metadata |
| `SearchResponse` | Collection: query, results, total_estimated, duration_ms |
| `ProviderStatistics` | Provider usage stats: request_count, error_count, avg_duration_ms, last_request |

## Exception Hierarchy

```
ProviderError
├── ProviderRegistrationError
├── ProviderExecutionError
├── ProviderConfigurationError
└── ProviderUnavailableError
```

## Dependency Injection

DI registration in `register_providers(container, settings)`:
- Creates all 7 provider instances
- Registers each with `ProviderRegistry`
- Registers `ProviderRegistry` as singleton
- Registers each provider as singleton with its class as the key (for
  direct resolution; most callers use the registry)

## Dependency Graph

```
providers
  ├── exceptions
  ├── models
  ├── interfaces (protocols)
  ├── providers/
  │   ├── base (ABC)
  │   ├── search (MCPSearchProvider, GoogleSearchProvider, DuckDuckGoSearchProvider)
  │   ├── github (GitHubProvider)
  │   ├── youtube (YouTubeProvider)
  │   ├── research (ResearchProvider)
  │   └── official_docs (OfficialDocsProvider)
  ├── registry
  └── __init__ (DI wiring)
```

No HTTP, MCP, AI, RAG, embeddings, vector store, or scheduling
dependencies.
