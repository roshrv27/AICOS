# Embedding Infrastructure

## Architecture Overview

The embedding layer provides a provider-neutral abstraction for generating
text embeddings.  Ollama is the default provider, but the architecture allows
any embedding service (OpenAI, Gemini, VoyageAI, BGE, Sentence Transformers,
etc.) to be substituted without changing application code.

```
┌──────────────────────────────────────────────────────┐
│                   Application                          │
│            depends only on EmbeddingService             │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│                 EmbeddingService                        │
│  • input validation                                    │
│  • delegates to EmbeddingProvider                      │
│  • no business logic                                   │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│               EmbeddingProvider (Protocol)              │
│  embed()  ·  embed_batch()  ·  health_check()          │
│  model_info()                                          │
│  No provider types in signatures                       │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│             OllamaEmbeddingProvider                     │
│  • HTTP calls to /api/embed                            │
│  • exception translation                               │
│  • reads config — no hardcoded values                  │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│                  Ollama Server                          │
│         Qwen3-Embedding:0.6B (default model)            │
└───────────────────────────────────────────────────────┘
```

## Dependency Graph

```
backend/aicos/ai/embeddings/
├── __init__.py           # Exports + register_embeddings()
├── exceptions.py         # EmbeddingError hierarchy
├── models.py             # EmbeddingRequest, EmbeddingResponse, ModelInfo
├── interfaces.py         # EmbeddingProvider protocol
├── ollama.py             # OllamaEmbeddingProvider
└── service.py            # EmbeddingService
```

- `interfaces.py` depends on `models.py` and `typing` only.
- `ollama.py` depends on `exceptions.py`, `models.py`, `logging`, and
  `urllib.request` (stdlib).
- `service.py` depends on `interfaces.py`, `models.py`, `exceptions.py`, and
  `logging`.
- `__init__.py` depends on all four internal modules plus `di` and `settings`.

## EmbeddingService Responsibilities

`EmbeddingService` is the **single application-facing entry point**.

- Validates inputs (rejects empty strings, empty batches, whitespace-only).
- Delegates embed operations to the configured `EmbeddingProvider`.
- Logs every request with model, dimensions, count, and duration.
- Contains zero business logic, zero caching, zero telemetry.

Application code resolves `EmbeddingService` from the DI container:

```python
service = container.resolve(EmbeddingService)
resp = service.embed(EmbeddingRequest(text="hello"))
```

## EmbeddingProvider Responsibilities

`EmbeddingProvider` is a `@runtime_checkable` Protocol with four methods:

| Method | Description |
|--------|-------------|
| `embed(text)` | Embed a single string. Returns `EmbeddingResponse`. |
| `embed_batch(texts)` | Embed multiple strings. Preserves order. Returns `EmbeddingBatchResponse`. |
| `health_check()` | Return `True` if the provider is reachable and the model is available. |
| `model_info()` | Return a `ModelInfo` with name, dimensions, and availability. |

No provider-specific types appear in any signature.  All parameters and return
values are project data models or standard Python types.

## OllamaEmbeddingProvider Responsibilities

`OllamaEmbeddingProvider` implements `EmbeddingProvider` by calling Ollama's
`/api/embed` endpoint over HTTP using the standard library (`urllib.request`).

- Constructs JSON payloads with `{"model": ..., "input": ...}`.
- Translates all HTTP and network errors into project exceptions.
- Logs each embedding generation with model, dimensions, and duration.
- Never exposes HTTP details, Ollama client objects, or raw API responses.

## Request Flow

```
Application
    │
    ▼
EmbeddingService.embed(EmbeddingRequest(text="..."))
    │
    ├── validates input
    │
    ▼
EmbeddingProvider.embed(text)
    │
    ▼
OllamaEmbeddingProvider._call_api(input_data)
    │
    ├── POST /api/embed  {model, input}
    │
    ▼
urllib.request.urlopen → JSON response
    │
    ▼
OllamaEmbeddingProvider parses embeddings
    │
    ├── EmbeddingResponse(embedding, dimensions, model)
    │
    ▼
EmbeddingService returns EmbeddingResponse
```

Batch flow follows the same path with a list of texts as input.

## Configuration

Reuses the existing `OllamaConfig` model in `settings.py`:

| Field | Default | Description |
|-------|---------|-------------|
| `enabled` | `True` | Enable/disable the Ollama provider |
| `base_url` | `http://localhost:11434` | Ollama server URL |
| `timeout_seconds` | `120` | HTTP request timeout |
| `embedding_model` | `Qwen3-Embedding:0.6B` | Model name for embeddings |

Configured in `config/base.yaml`:

```yaml
ollama:
  enabled: true
  base_url: http://localhost:11434
  timeout_seconds: 120
  embedding_model: Qwen3-Embedding:0.6B
```

## Dependency Injection

Registered by `register_embeddings(container, settings)` in
`backend/aicos/ai/embeddings/__init__.py`:

| Service | Lifetime | Registration |
|---------|----------|-------------|
| `OllamaEmbeddingProvider` | Singleton | Factory creates from `settings.ollama` |
| `EmbeddingProvider` | Singleton | Resolves the `OllamaEmbeddingProvider` singleton |
| `EmbeddingService` | Singleton | Auto-constructed — `EmbeddingProvider` injected via constructor |

Application code resolves `EmbeddingService` only:

```python
from aicos.core.di import Container
from aicos.settings import Settings
from aicos.ai.embeddings import EmbeddingService, register_embeddings

container = Container()
settings = Settings(config_dir="config")
register_embeddings(container, settings)

service = container.resolve(EmbeddingService)
```

## Logging

Every embedding operation is logged at `DEBUG` level under the `aicos.embeddings`
logger.  Each log record includes:

| Field | Description |
|-------|-------------|
| `model` | Active embedding model name |
| `dimensions` | Embedding vector dimensions |
| `count` | Number of embeddings in batch |
| `execution_duration_ms` | Wall-clock duration in milliseconds |

No input text, no embedding vectors, and no request payloads are ever logged.

## Exception Handling

All embedding exceptions inherit from `EmbeddingError`:

```
EmbeddingError
├── ProviderUnavailableError    — provider unreachable or returning 5xx
├── ModelNotFoundError          — model not found on provider (404)
├── EmbeddingGenerationError    — generic generation failure
└── ConfigurationError          — invalid input or disabled provider
```

Every exception from the HTTP layer or Ollama is translated before reaching
the application.  No `urllib.error`, `json.JSONDecodeError`, or other
infrastructure exception escapes the embedding layer.

## Extension Points

### Adding a new embedding provider (e.g., OpenAI, VoyageAI, BGE)

1. Create a new class that fulfills `EmbeddingProvider`:
   ```python
   class OpenAIEmbeddingProvider:
       def embed(self, text: str) -> EmbeddingResponse: ...
       def embed_batch(self, texts: list[str]) -> EmbeddingBatchResponse: ...
       def health_check(self) -> bool: ...
       def model_info(self) -> ModelInfo: ...
   ```

2. Wire it in `register_embeddings()` by replacing the factory:
   ```python
   container.replace(
       EmbeddingProvider,
       factory=lambda: OpenAIEmbeddingProvider(api_key=...),
       lifetime=ServiceLifetime.SINGLETON,
   )
   ```

No changes to `interfaces.py`, `models.py`, `service.py`, or `exceptions.py`
are needed.  The protocol, data models, service, and exception hierarchy are
all provider-neutral.

### Adding new operations

The `EmbeddingProvider` protocol can be extended with new methods (e.g.,
`embed_document()`, `token_count()`).  All implementations must be updated to
match the protocol.

---

*Part of the AICOS AI Layer — Milestone 9D*
