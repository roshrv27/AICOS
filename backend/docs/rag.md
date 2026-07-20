# Retrieval-Augmented Generation (RAG) Orchestration

## Architecture

```
 Application
      │
      ▼
 RAGService
      │
      ├────────► RetrievalService
      │
      ├────────► PromptBuilder
      │
      ├────────► CitationBuilder
      │
      └────────► GenerationService
                        │
                        ▼
                   ModelRouter
                        │
                        ▼
                  Configured LLM
```

**Dependency graph:**

- `RAGService` is the single entry point — orchestrates the full RAG pipeline
- `RetrievalService` provides semantic retrieval (from milestone 9F)
- `PromptBuilder` assembles system prompt, query, and context into a structured `Prompt`
- `CitationBuilder` creates deduplicated `Citation` objects from context chunks
- `GenerationService` is the ONLY component that calls `ModelRouter`

## Request Lifecycle

1. **Validate request** — `RAGService.answer()` receives `RAGRequest`
2. **Retrieve context** — calls `RetrievalService.retrieve(QueryRequest)` → `RetrievalResult`
3. **Convert to context chunks** — maps `RetrievedChunk` → `ContextChunk`
4. **Build prompt** — `PromptBuilder.build()` assembles system + user sections with context
5. **Generate answer** — `GenerationService.generate(Prompt)` → `GenerationResult`
6. **Build citations** — `CitationBuilder.build()` deduplicates, preserves order
7. **Return response** — `RAGResponse` with answer, citations, model info, timing

## Prompt Assembly

`PromptBuilder` constructs:

- **System section**: the system prompt (configurable per-request or via settings)
- **User section**: `"Context:\n[1] Source: ...\ncontent\n\n[2] ...\n\nQuestion: {query}"`

Context handling:
- Limited to `max_context_chunks` (default: 5)
- Token count estimated at ~4 chars/token
- If estimated tokens exceed `max_prompt_tokens` (default: 4096), chunks are truncated from the end until the budget fits

## Generation

`GenerationService` converts `Prompt.sections` → `list[ChatMessage]` → `ModelRequest`, calls `ModelRouter.generate()`, and catches/translates all exceptions into `GenerationError`.

## Citations

`CitationBuilder` creates structured citations with:
- `chunk_id` — unique identifier
- `source` — source file path
- `filename` — source filename
- `score` — similarity score
- `rank` — retrieval rank

Duplicates are removed (same `chunk_id`), keeping the first occurrence. No string formatting of citations occurs.

## Configuration

```yaml
rag:
  default_top_k: 10
  max_context_chunks: 5
  max_prompt_tokens: 4096
  default_system_prompt: "You are a helpful AI assistant..."
```

| Field | Default | Description |
|---|---|---|
| `default_top_k` | `10` | Default number of chunks to retrieve |
| `max_context_chunks` | `5` | Max chunks included in the prompt |
| `max_prompt_tokens` | `4096` | Max estimated tokens before truncation |
| `default_system_prompt` | (see base.yaml) | Default system prompt |

## Dependency Injection

```python
from aicos.rag import register_rag, RAGService

register_rag(container, settings)
service = container.resolve(RAGService)
response = await service.answer(RAGRequest(query="..."))
```

Registered components: `PromptBuilder`, `CitationBuilder`, `GenerationService`, `RAGService`.

## Logging

Two loggers:

- `aicos.rag` — logs `retrieved_count`, `prompt_tokens`, `model`, `generation_duration_ms`, `total_duration_ms`
- `aicos.rag.generation` — logs `model`, `provider`, `duration_ms`

User query, prompt text, chunk text, embeddings, and generated answer are never logged.

## Exception Hierarchy

```
RAGError
├── PromptBuildError    — empty query, empty system prompt
├── ContextError        — retrieval returned no context
├── GenerationError     — LLM generation failure
└── CitationError       — citation assembly failure (reserved)
```

## Extension Points

- **Custom prompt template**: implement `PromptBuilderProtocol`
- **Custom citation logic**: implement `CitationBuilderProtocol`
- **Custom generation**: implement `GenerationServiceProtocol`
