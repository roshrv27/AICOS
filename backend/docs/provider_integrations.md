# Provider Integrations

## Architecture

```
Provider Registry
        │
 ┌──────┼──────────────────────────────────────┐
 ▼      ▼            ▼           ▼        ▼    ▼
Search  GitHub  OfficialDocs  Research  YouTube Social
        │
        ▼
Normalized Domain Models
```

Integration providers are the real implementation layer below the
placeholder providers in `providers/providers/`. They connect AICOS to
external knowledge sources and normalize all data into domain models
before returning.

No HTTP responses, JSON payloads, provider-specific objects, or SDK
models are ever exposed.

## Supported Providers

| Provider | Class | `provider_name` | Capabilities |
|---|---|---|---|
| MCP Search | `MCPSearchIntegration` | `mcp_search` | search, suggest |
| Google Search | `GoogleSearchIntegration` | `google_search` | search, suggest |
| DuckDuckGo | `DuckDuckGoIntegration` | `duckduckgo_search` | search, suggest |
| GitHub | `GitHubIntegration` | `github` | repository_discovery, release_discovery, topic_search |
| YouTube | `YouTubeIntegration` | `youtube` | video_discovery, channel_discovery, playlist_discovery |
| Arxiv (Research) | `ArxivIntegration` | `research` | paper_discovery, author_lookup, topic_search |
| Official Docs | `OfficialDocsIntegration` | `official_docs` | documentation_lookup, version_discovery, release_notes |

## Search Providers

All search providers implement:

| Method | Input | Returns |
|---|---|---|
| `search(request)` | `SearchRequest` | `SearchResponse` (only) |
| `suggest(query)` | `str` | `list[str]` |
| `health()` | — | `ProviderHealth` |

Return `SearchResponse` only. No raw HTTP responses or JSON.

## Non-Search Providers

### GitHub Integration

| Method | Returns | Domain Type |
|---|---|---|
| `discover_repositories(query)` | `list[KnowledgeSource]` | `GITHUB` |
| `discover_releases(owner, repo)` | `list[KnowledgeSource]` | `GITHUB` |
| `search_topics(query)` | `list[TechnologySignal]` | with `Evidence` |

### YouTube Integration

| Method | Returns | Domain Type |
|---|---|---|
| `discover_videos(query)` | `list[KnowledgeResource]` | `VIDEO` |
| `discover_channels(query)` | `list[KnowledgeSource]` | `YOUTUBE` |
| `discover_playlists(query)` | `list[KnowledgeResource]` | `VIDEO` |

### Arxiv Integration (Research)

| Method | Returns | Domain Type |
|---|---|---|
| `discover_papers(query)` | `list[KnowledgeSource]` | `RESEARCH_PAPER` |
| `author_lookup(author)` | `list[KnowledgeSource]` | `RESEARCH_PAPER` |
| `search_topics(topic)` | `list[TechnologySignal]` | with `Evidence` |

### Official Docs Integration

| Method | Returns | Domain Type |
|---|---|---|
| `lookup_documentation(product, version?)` | `list[KnowledgeSource]` | `OFFICIAL_DOCUMENTATION` |
| `discover_versions(product)` | `list[KnowledgeVersion]` | — |
| `get_release_notes(product, version)` | `list[KnowledgeSource]` | `OFFICIAL_DOCUMENTATION` |

## Trust Policy

`SourceTrustPolicy` provides configurable trust weights for knowledge
sources.

| Source | Default Weight |
|---|---|
| Official Documentation | 1.00 |
| Official GitHub | 0.95 |
| Research | 0.90 |
| Conference | 0.85 |
| Vendor Blogs | 0.80 |
| YouTube | 0.70 |
| Community | 0.60 |
| Reddit | 0.50 |
| X | 0.40 |

Weights are validated to be in `[0.0, 1.0]`. The policy is configurable
at construction and at runtime via `set_weight()`. No ranking or
business decisions are made by the policy — it only exposes trust
metadata.

## Configuration

`ProviderSettings` controls:

| Setting | Default |
|---|---|
| `timeouts` | `default: 30, search: 15, github: 60, youtube: 30, arxiv: 30, docs: 30` |
| `retry_count` | `3` |
| `user_agent` | `"AICOS/0.1.0"` |
| `rate_limits` | `github: 60, youtube: 10000, google: 100` |
| `enabled_providers` | All 7 providers enabled by default |
| `api_endpoints` | Empty dict (uses defaults) |
| `credentials` | Empty dict (no secrets committed) |
| `trust_weights` | Empty dict (uses SourceTrustPolicy defaults) |

## Authentication Strategy

Credentials are never committed to the repository. Each integration
accepts credentials via the `config` dict at construction:

- **Google**: `api_key`, `search_engine_id`
- **GitHub**: `token` (Bearer token)
- **YouTube**: `api_key`
- **MCP/DuckDuckGo/Arxiv/Docs**: No auth required or configurable via config

Credentials are stored in `ProviderSettings.credentials` (dict) and
passed through to each integration at DI registration time. Sensitive
values are never logged.

## Error Handling

All provider errors are translated to the provider exception hierarchy
before leaving the integration:

| External Error | Translated To |
|---|---|
| HTTP 4xx/5xx | `ProviderExecutionError` |
| HTTP 403 (GitHub) | `ProviderUnavailableError` (rate limit) |
| HTTP 404 (GitHub) | `ProviderExecutionError` (not found) |
| HTTP 403 (YouTube) | `ProviderUnavailableError` (quota) |
| DNS / Connection failure | `ProviderUnavailableError` |
| Configuration errors | `ProviderConfigurationError` |
| Any other exception | `ProviderExecutionError` |

No provider-specific exceptions ever leak to the caller.

## Logging

All integrations log:

- `provider` name
- `capability` being used
- `query` or target
- `status` (success/error)
- `results` count
- `duration_ms`
- `error` message on failure

Never logged:
- Credentials, API keys, OAuth tokens
- Cookies
- Sensitive URLs containing tokens

Logger names follow the pattern `aicos.providers.integrations.<provider>`.

## Extension Points

| Point | Mechanism |
|---|---|
| **New provider** | Create class in `integrations/<name>/`, implement protocol, add to `__init__.py` and DI registration |
| **Custom trust weights** | Pass `weights` dict to `SourceTrustPolicy()` |
| **Custom config** | Add fields to `ProviderSettings` |
| **Rate limiting** | Configure via `ProviderSettings.rate_limits` |
| **API endpoints** | Override via `config["endpoint"]` at construction |

## DI Registration

Integration providers are registered alongside placeholder providers
in `providers/__init__.py`:

```python
register_providers(container, settings)
registry = container.resolve(ProviderRegistry)
integration = registry.lookup("github")
```

Each integration is wired with its config subset, timeout, retry count,
and user agent from `ProviderSettings`.
