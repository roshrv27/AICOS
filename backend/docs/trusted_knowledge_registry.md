# Trusted Knowledge Registry

## Architecture

```
Discovery Orchestrator
        │
        ▼
Trusted Knowledge Registry
        │
        ├──────────────────────┐
        ▼                      ▼
  Knowledge Sources      Discovery Policies
        │
        ▼
  Provider Registry
        │
        ▼
  Provider Integrations
        │
        ▼
  Knowledge Acquisition Engine
```

The Trusted Knowledge Registry is the single source of truth that defines
WHAT AICOS should monitor. Providers define HOW to retrieve information.
The registry defines WHERE and WHAT to retrieve.

This milestone does NOT perform crawling, searching, extraction, ranking,
recommendations, or AI reasoning. It only models and manages trusted
knowledge sources.

## Registry Lifecycle

1. Application starts → `register_trusted_sources()` registers registry
   and service as singletons
2. `load_seed_data()` populates registry with ~100 curated sources
3. Application queries registry by type, category, capability, or tag
4. Sources can be enabled/disabled, trust scores updated at runtime
5. Discovery Orchestrator queries registry to determine what to monitor

## Domain Models

### TrustedKnowledgeSource

The core entity representing a single knowledge source to monitor.

| Field | Type | Default | Description |
|---|---|---|---|
| `id` | `str` | — | Unique identifier |
| `name` | `str` | — | Display name |
| `source_type` | `SourceType` | — | Type of source |
| `category` | `Category` | — | AI category |
| `url` | `str` | `""` | Primary URL |
| `display_name` | `str` | `""` | Human-readable name |
| `organization` | `str` | `""` | Parent organization |
| `rss_feed` | `str` | `""` | RSS/Atom feed URL |
| `api_endpoint` | `str` | `""` | API endpoint URL |
| `trust_score` | `float` | `0.5` | Trustworthiness [0, 1] |
| `priority` | `int` | `50` | Monitoring priority |
| `enabled` | `bool` | `True` | Whether to monitor |
| `authentication_type` | `AuthenticationType` | `NONE` | Auth required |
| `refresh_frequency` | `RefreshFrequency` | `DAILY` | How often to check |
| `capabilities` | `frozenset[Capability]` | `∅` | What it provides |
| `tags` | `frozenset[str]` | `∅` | Free-form tags |
| `metadata` | `dict[str, Any]` | `{}` | Extra key-value data |

### Supporting Models

| Model | Purpose |
|---|---|
| `TrustedSourceGroup` | Logical group of source IDs |
| `CapabilityMapping` | Maps source type to capability |
| `DiscoveryPolicy` | Filter/limit rules for discovery |
| `KnowledgeCatalog` | Named collection of sources, groups, policies |

## Seed Catalog

~100 curated sources across 12 source types:

| Category | Count | Examples |
|---|---|---|
| Official Documentation | 18 | OpenAI, Anthropic, Hugging Face, PyTorch |
| GitHub Organizations | 15 | openai, microsoft, pytorch, huggingface |
| YouTube Channels | 15 | OpenAI, Karpathy, DeepLearningAI |
| Research | 7 | arXiv, Semantic Scholar, ACL Anthology |
| Conferences | 10 | NeurIPS, ICML, ICLR, CVPR |
| Blogs | 9 | OpenAI Blog, Google AI Blog |
| Social (X) | 7 | OpenAI, Anthropic, NVIDIA |
| Benchmarks | 5 | LMSYS Arena, MLPerf |
| Package Registries | 5 | PyPI, npm, Docker Hub |
| Hardware Vendors | 7 | NVIDIA, AMD, Apple, Qualcomm |
| News | 1 | AI News |
| Podcasts | 1 | AI Podcast |

## Capability Model

| Capability | Description | Applicable Types |
|---|---|---|
| `DOCUMENTATION` | Official docs | DOCUMENTATION, HARDWARE_VENDOR |
| `RELEASES` | Release notes/changelogs | GITHUB, PACKAGE_REGISTRY |
| `BLOG_POSTS` | Blog articles | BLOG, DOCUMENTATION |
| `VIDEOS` | Video content | YOUTUBE |
| `REPOSITORIES` | Source code repos | GITHUB, PACKAGE_REGISTRY |
| `RESEARCH_PAPERS` | Academic papers | RESEARCH, CONFERENCE |
| `SOCIAL_POSTS` | Social media posts | SOCIAL |
| `BENCHMARKS` | Benchmark data | BENCHMARK |
| `PACKAGES` | Package listings | PACKAGE_REGISTRY |
| `API_REFERENCE` | API docs | DOCUMENTATION |
| `CHANGELOGS` | Change logs | DOCUMENTATION |

## Source Types

12 source types: DOCUMENTATION, GITHUB, YOUTUBE, RESEARCH, BLOG, NEWS,
SOCIAL, PODCAST, CONFERENCE, BENCHMARK, PACKAGE_REGISTRY, HARDWARE_VENDOR

## Categories

13 categories: LLM, AGENTS, RAG, VISION, SPEECH, MULTIMODAL, EDGE_AI,
CLOUD_AI, FRAMEWORK, TOOLING, HARDWARE, SECURITY, BENCHMARK

## Validation

| Rule | Enforcement |
|---|---|
| Unique ID | Registry prevents duplicates |
| Non-empty ID/name | `validate_source()` raises `InvalidSourceError` |
| Trust score `[0, 1]` | Model `__post_init__` raises `ValueError` |
| Priority `>= 0` | `validate_source()` raises `InvalidSourceError` |
| URL format | Must start with `http://` or `https://` |
| Auth type | Must be valid `AuthenticationType` enum member |

## Exception Hierarchy

```
TrustedSourceError
├── DuplicateSourceError   — duplicate ID on registration
├── InvalidTrustScoreError — trust score out of range
├── InvalidSourceError     — validation failure
└── SourceNotFoundError    — lookup failure
```

## DI Registration

```python
from aicos.trusted_sources import register_trusted_sources, 
    TrustedKnowledgeRegistry, TrustedKnowledgeService

register_trusted_sources(container, settings)
registry = container.resolve(TrustedKnowledgeRegistry)
service = container.resolve(TrustedKnowledgeService)
```

Both `TrustedKnowledgeRegistry` and `TrustedKnowledgeService` are
registered as singletons.

## Extension Guide

### Adding a new source
```python
source = TrustedKnowledgeSource(
    id="my-source",
    name="My Source",
    source_type=SourceType.BLOG,
    category=Category.LLM,
    url="https://example.com",
    trust_score=0.85,
    capabilities=frozenset([Capability.BLOG_POSTS]),
    tags=frozenset(["llm", "custom"]),
)
service.register(source)
```

### Adding seed data
Add an entry to `seed_data.py` in the appropriate list, or create a new
list for a new source type, and add the corresponding `_build()` call
in `get_seed_sources()`.

### Custom discovery policies
```python
policy = DiscoveryPolicy(
    id="daily-llm",
    name="Daily LLM Discovery",
    source_type_filter=frozenset([SourceType.BLOG, SourceType.RESEARCH]),
    category_filter=frozenset([Category.LLM]),
    max_results=25,
)
```

## Best Practices

- IDs should be short, kebab-case, and globally unique
- Trust scores should be conservative and reviewed quarterly
- URLs should point to the most specific page possible
- Capabilities should be precise — don't over-claim
- Tags should use consistent taxonomy across sources
- Use `frozenset` for capabilities and tags to ensure immutability
- Never hardcode provider targets — always go through the registry
