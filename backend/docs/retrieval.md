# Retrieval Infrastructure

## Architecture

```
 Application
      │
      ▼
 RetrievalService
      │
      ├── QueryProcessor        (validate & normalize)
      ├── EmbeddingService      (generate query embedding)
      ├── MetadataFilterBuilder (build filter dict)
      ├── VectorStorePort       (semantic search)
      └── SimilarityRanker      (sort by score)
```

**Dependency graph:**

- `RetrievalService` depends on `EmbeddingService`, `VectorStorePort`, `RankingStrategy`, `MetadataFilterBuilder`
- `EmbeddingService` depends on `EmbeddingProvider` (protocol)
- `VectorStorePort` depends on `ChromaDBVectorStore` (or any vector-db adapter)

## Query Lifecycle

1. **Validate** — `QueryProcessor` strips whitespace, rejects empty/whitespace-only queries
2. **Embed** — `EmbeddingService.embed(EmbeddingRequest(text=query))` returns `EmbeddingResponse`
3. **Filter** — `MetadataFilterBuilder.build(SearchFilters)` produces a flat `dict[str, Any]`
4. **Search** — `VectorStorePort.search(collection, query_vector, top_k, filter)` returns `list[SearchResult]`
5. **Threshold** — results below `similarity_threshold` are removed
6. **Rank** — `SimilarityRanker.rank()` sorts by descending score, reassigns ranks
7. **Return** — `RetrievalResult` with query, results, and summary

## Ranking

`SimilarityRanker` sorts chunks by descending `score`. No reranking,
cross-encoder, or LLM-based ranking is performed.

## Filtering

`SearchFilters` supports:

| Field | Type | Description |
|---|---|---|
| `collection_name` | `str \| None` | Target collection |
| `source` | `str \| None` | Source file path |
| `filename` | `str \| None` | File name |
| `document_id` | `str \| None` | Document identifier |
| `custom_metadata` | `dict[str, Any] \| None` | Arbitrary key-value pairs |

## Configuration

```yaml
retrieval:
  default_top_k: 10
  max_top_k: 100
  similarity_threshold: 0.0
```

| Field | Default | Description |
|---|---|---|
| `default_top_k` | `10` | Fallback when `top_k < 1` |
| `max_top_k` | `100` | Upper clamp for `top_k` |
| `similarity_threshold` | `0.0` | Minimum similarity score (0.0 = no filter) |

## Dependency Injection

```python
from aicos.retrieval import register_retrieval, RetrievalService

register_retrieval(container, settings)
service = container.resolve(RetrievalService)
```

## Logging

The logger name is `aicos.retrieval`. Logged at `INFO` level per query:

- `top_k`
- `threshold`
- `retrieved_count`
- `duration_ms`

Query text, embeddings, and document content are never logged.

## Exception Hierarchy

```
RetrievalError
├── QueryValidationError  — empty/whitespace query
├── SearchError           — embedding or vector-store failure
├── RankingError          — ranking failure (reserved)
└── FilterError           — invalid filter keys
```

## Extension Points

- **New ranking strategy**: implement `RankingStrategy` protocol
- **New filter logic**: extend `MetadataFilterBuilder`
- **Custom query validation**: implement `QueryValidator` protocol
