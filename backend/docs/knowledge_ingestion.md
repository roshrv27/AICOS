# Knowledge Ingestion Infrastructure

## Architecture

```
 File Path
    │
    ▼
 ┌────────────┐
 │  Loader    │  (TextLoader, MarkdownLoader, PDFLoader)
 └─────┬──────┘
       │ Document
       ▼
 ┌────────────┐
 │  Chunker   │  (RecursiveCharacterChunker)
 └─────┬──────┘
       │ list[DocumentChunk]
       ▼
 ┌────────────┐
 │  Metadata  │  (MetadataExtractor)
 └─────┬──────┘
       │ enriched chunk metadata
       ▼
 ┌────────────┐
 │  Embedding │  (EmbeddingService → EmbeddingProvider)
 └─────┬──────┘
       │ embedding vector
       ▼
 ┌────────────┐
 │Vector Store│  (VectorStorePort → ChromaDBVectorStore)
 └────────────┘
```

## Key Components

| Component | Responsibility | Protocol |
|---|---|---|
| `TextLoader` | Load `.txt` files | `DocumentLoader` |
| `MarkdownLoader` | Load `.md` files, strip formatting | `DocumentLoader` |
| `PDFLoader` | Load `.pdf` files via PyMuPDF | `DocumentLoader` |
| `RecursiveCharacterChunker` | Split text on paragraph/sentence/word boundaries | `ChunkingStrategy` |
| `MetadataExtractor` | Structural metadata (word count, hash, timestamp) | — |
| `KnowledgeIngestionService` | Orchestrate load → chunk → embed → store | — |

## Usage

```python
from pathlib import Path
from aicos.knowledge import KnowledgeIngestionService
from aicos.knowledge.models import IngestionRequest

service: KnowledgeIngestionService = container.resolve(KnowledgeIngestionService)
result = service.ingest(IngestionRequest(source=Path("/path/to/doc.md")))
print(f"Ingested {result.chunks_ingested} chunks into {result.collection_name}")
```

## Configuration

See `config/base.yaml` under the `knowledge` key:

```yaml
knowledge:
  chunk_size: 1000
  chunk_overlap: 200
  supported_extensions:
    - .txt
    - .md
    - .pdf
  default_collection: knowledge
```

## Adding a New Loader

1. Create `aicos/knowledge/loaders/<format>_loader.py`.
2. Implement the `DocumentLoader` protocol (`supports` and `load`).
3. Register the loader in `aicos/knowledge/__init__.py` (the `loaders` list).
