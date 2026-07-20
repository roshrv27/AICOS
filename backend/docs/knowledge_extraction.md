# Knowledge Extraction Engine

## Architecture

```
Trusted Knowledge Registry
        │
        ▼
Provider Integrations
        │
        ▼
Knowledge Acquisition Engine
        │
        ▼
Knowledge Extraction Engine    ← Phase 10G
        │
        ▼
Knowledge Intelligence Domain
```

The Knowledge Extraction Engine transforms raw external content into
structured Knowledge Intelligence Domain objects. It is the layer
responsible for **understanding content** — converting text into typed,
validated entities.

## Extraction Pipeline

```
Raw Content (str)
       │
       ▼
ExtractionRequest
       │
       ▼
KnowledgeExtractionService.extract()
       │
       ├── RULE_BASED mode → _extract_rules()
       │      │
       │      ▼
       │   ExtractionRegistry.discover(content_type)
       │      │
       │      ▼
       │   Extractor.extract(request)
       │      │
       │      ▼
       │   ExtractionResult (with Extracted* entities)
       │
       └── LLM_ASSISTED mode → _extract_llm()
              │
              ▼
           ModelRouter.generate(ModelRequest)
              │
              ▼
           _build_result() → ExtractionResult
              │
              ▼
           ExtractionResult (with Extracted* entities)
       │
       ▼
   validate_extraction_result()
       │
       ▼
   ExtractionResult.to_discovery_result()
       │
       ▼
   DiscoveryResult (TechnologySignal, KnowledgeResource, Evidence, ...)
```

## Extraction Models

All extraction models are frozen dataclasses in `models.py`.

### Extracted Entities

| Model | Fields | Domain Conversion |
|---|---|---|
| `ExtractedTechnology` | id, name, summary, category, status, importance, confidence | → `TechnologySignal` |
| `ExtractedFramework` | id, name, description, version, language, url | → `KnowledgeResource` |
| `ExtractedModel` | id, name, description, provider, version, url | → `KnowledgeResource` |
| `ExtractedTool` | id, name, description, category, url | → `KnowledgeResource` |
| `ExtractedAPI` | id, name, description, endpoint, version, url | → `KnowledgeResource` |
| `ExtractedConcept` | id, name, description, category, confidence | → `TechnologySignal` |
| `ExtractedVersion` | id, version, created_at, changes | → `KnowledgeVersion` |
| `ExtractedRelease` | id, name, version, release_date, description, url, changes | → `KnowledgeVersion` |
| `ExtractedDependency` | id, name, version, category, url | — |
| `ExtractedExample` | id, title, description, code, language, url | → `KnowledgeResource` |
| `ExtractedCodeSnippet` | id, code, language, description, source_url | → `KnowledgeResource` |
| `ExtractedReference` | id, source, title, url, published_at, author, confidence | → `Evidence` |

### Request / Context / Result

- **ExtractionRequest** — content, source_type, source_id, source_name, source_url, content_type, mode, config
- **ExtractionContext** — extraction metadata (timestamp, source type, size, mode)
- **ExtractionResult** — all extracted entities + errors + statistics
- **ExtractionStatistics** — entity counts, duration, mode

### Domain Conversion

`ExtractionResult` provides these conversion methods:

| Method | Returns |
|---|---|
| `to_signals()` | `list[TechnologySignal]` |
| `to_resources()` | `list[KnowledgeResource]` |
| `to_evidence()` | `list[Evidence]` |
| `to_versions()` | `list[KnowledgeVersion]` |
| `to_sources()` | `list[KnowledgeSource]` |
| `to_discovery_result()` | `DiscoveryResult` |

## Extractor Protocol

Every extractor implements:

| Method | Signature | Returns |
|---|---|---|
| `supports()` | `(content_type: ContentType) → bool` | Whether this extractor handles the content type |
| `extract()` | `(request: ExtractionRequest) → ExtractionResult` | Run extraction |
| `validate()` | `(result: ExtractionResult) → list[str]` | Validation errors |
| `metadata()` | `() → dict` | Extractor metadata |

### BaseExtractor

Provides common utilities to all extractors:

| Method | Purpose |
|---|---|
| `_extract_versions(content)` | SemVer pattern matching |
| `_extract_urls(content, source)` | URL extraction to ExtractedReference |
| `_extract_code_blocks(content)` | Fenced code block extraction |
| `_extract_technology_mentions(content, known)` | Keyword-based tech detection |

## Extractors

| Extractor | Supported Content Types | Extracts |
|---|---|---|
| `DocumentationExtractor` | DOCUMENTATION, GENERIC_TEXT | versions, APIs (endpoint detection), concepts (headings), code blocks, URLs |
| `GitHubExtractor` | GITHUB_README, GITHUB_RELEASE | versions, releases (changelog parsing), dependencies (pkg patterns), tech mentions, code blocks |
| `YouTubeExtractor` | YOUTUBE_VIDEO, YOUTUBE_DESCRIPTION | tech mentions, concepts (hashtags, topic fields), URLs |
| `ResearchExtractor` | RESEARCH_PAPER, RESEARCH_ABSTRACT | models (name matching), frameworks, concepts (abstract parsing), citations, URLs |
| `BlogExtractor` | BLOG_POST, BLOG_ARTICLE, GENERIC_TEXT | tech mentions, concepts (headings, bold highlights), code blocks, URLs |

## Extraction Registry

`ExtractionRegistry` in `registry.py`

| Method | Purpose |
|---|---|
| `register(extractor)` | Register extractor; prevents duplicates |
| `lookup(name)` | Lookup by extractor name |
| `lookup_by_source(content_type)` | All extractors supporting a content type |
| `discover(content_type)` | First extractor supporting a content type |
| `registered` | List of registered extractor names |

## Service

`KnowledgeExtractionService` coordinates extraction.

| Method | Purpose |
|---|---|
| `extract(request)` | Single extraction (async, rule-based or LLM) |
| `extract_batch(requests)` | Batch with per-request error handling |
| `select_extractor(content_type)` | Discover extractor for content type |
| `validate_result(result)` | Run full validation |
| `collect_statistics(result, duration, mode)` | Compute statistics |

## Mode Selection

Mode selection is configurable per request:

| request.mode | Behavior |
|---|---|
| `""` (empty) | Auto-detect: LLM if ModelRouter available, else rule-based |
| `"rule_based"` | Force rule-based extraction |
| `"llm_assisted"` | Force LLM-assisted (falls back to rules if no router) |
| `"auto"` | Auto-detect |

## LLM Integration

LLM-assisted extraction uses the existing `ModelRouter`:

1. Builds `ModelRequest` with `structured_output=True`
2. Sends content via `_LLM_EXTRACTION_PROMPT` with structured JSON schema
3. Parses `response.structured_output` or falls back to `response.content`
4. JSON parsing handles ` ```json ` fences
5. Validation errors per entity are captured in `result.errors`

No hardcoded model names. Uses the ModelRouter's capability-based routing.

## Validation

`validate_extraction_result()` checks:

| Rule | Details |
|---|---|
| Empty content | Rejects empty/blank content |
| Required fields | id, name/version/title per entity type |
| Duplicate IDs | Across all entity categories |
| Version format | Must match `\d+\.\d+\.\d+` |
| URL format | Must start with `http://` or `https://` |
| Reference consistency | All `source_references` must exist in `references` |

All errors are aggregated and raised as a single `ExtractionValidationError`.

## Exception Hierarchy

```
ExtractionError
├── UnsupportedContentError  — no extractor for content type
├── InvalidExtractionError   — extraction produced invalid data
├── ExtractorNotFoundError   — extractor name not in registry
└── ExtractionValidationError — validation failure
```

## DI Registration

```python
from aicos.knowledge_extraction import (
    register_knowledge_extraction,
    KnowledgeExtractionService,
    ExtractionRegistry,
)

register_knowledge_extraction(container, settings)
registry = container.resolve(ExtractionRegistry)
service = container.resolve(KnowledgeExtractionService)
```

Registers:
- `ExtractionRegistry` — singleton, auto-populated with 5 extractors
- `KnowledgeExtractionService` — singleton, optionally depends on `ModelRouter`

## Best Practices

- Always validate results via `validate_result()` before converting to domain models
- Prefer rule-based extraction for known, structured content formats
- Use LLM-assisted for unstructured or novel content types
- Batch extraction handles per-request errors independently
- Entity IDs should be unique across the entire result
- Confidence scores should reflect extraction certainty, not source trust
- Always use `to_discovery_result()` for pipeline integration
- Never modify frozen dataclasses after creation
