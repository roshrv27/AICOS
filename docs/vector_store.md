# Vector Store Infrastructure

## Architecture Overview

The vector store layer provides a provider-neutral storage abstraction for
vector databases.  It isolates ChromaDB completely behind a runtime-checkable
Protocol so that application code depends only on the abstraction, never on
ChromaDB types, exceptions, or client objects.

```
┌──────────────────────────────────────────────────┐
│                  Application                      │
│  depends only on VectorStorePort                  │
└────────────────────┬─────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────┐
│              VectorStorePort (Protocol)            │
│  create_collection  ·  delete_collection          │
│  collection_exists  ·  list_collections           │
│  add_document      ·  update_document             │
│  delete_document   ·  get_document                │
│  search                                          │
└────────────────────┬─────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────┐
│            ChromaDBVectorStore                     │
│  implements VectorStorePort                       │
│  delegates collection ops → CollectionManager     │
│  wraps ChromaDB client via try/except             │
└────┬─────────────────────────────┬───────────────┘
     │                             │
     ▼                             ▼
┌──────────┐           ┌──────────────────┐
│ ChromaDB │           │ CollectionManager │
│ Client   │◄─────────│  create / delete   │
│          │           │  exists / list     │
│          │           │  get / create_if_  │
│          │           │    not_exists      │
└──────────┘           └──────────────────┘
```

## Dependency Graph

```
persistence/
├── exceptions.py          # PersistenceError (base)
├── vector_store/
│   ├── __init__.py        # Exports + register_vector_store()
│   ├── exceptions.py      # VectorStoreError hierarchy
│   ├── models.py          # EmbeddingDocument, SearchResult
│   ├── interfaces.py      # VectorStorePort protocol
│   ├── collections.py     # CollectionManager
│   ├── chroma.py          # ChromaDBVectorStore
```

- `interfaces.py` depends on `models.py` and `typing` only.
- `collections.py` depends on `exceptions.py` and `logging` only.
- `chroma.py` depends on `collections.py`, `exceptions.py`, `models.py`, and
  `chromadb`.
- `__init__.py` depends on all four internal modules plus `chroma.py` for
  `ChromaDBVectorStore`.

## VectorStorePort Responsibilities

`VectorStorePort` is a `@runtime_checkable` Protocol in
`interfaces.py`.  It defines nine methods covering three concerns:

### Collection Lifecycle

| Method               | Description                                      |
|----------------------|--------------------------------------------------|
| `create_collection`  | Create a named collection. Raises `CollectionError` if it exists. |
| `delete_collection`  | Delete a named collection. Raises `CollectionError` if missing.   |
| `collection_exists`  | Return `True` if the collection exists.          |
| `list_collections`   | Return all collection names.                     |

### Document Lifecycle

| Method               | Description                                      |
|----------------------|--------------------------------------------------|
| `add_document`       | Insert one document. Raises `DocumentError` if ID exists. |
| `update_document`    | Upsert — insert or replace.                      |
| `delete_document`    | Remove by ID. No error if missing.               |
| `get_document`       | Retrieve by ID. Returns `None` when missing.     |

### Search

| Method               | Description                                      |
|----------------------|--------------------------------------------------|
| `search`             | Semantic vector search with optional metadata filter. |

All signatures use only project types (`EmbeddingDocument`, `SearchResult`,
`list[float]`, `dict[str, Any]`).  No ChromaDB types appear anywhere in the
protocol.

## ChromaDBVectorStore Responsibilities

`ChromaDBVectorStore` in `chroma.py` is the concrete implementation of
`VectorStorePort` backed by ChromaDB.  It:

- Accepts a `chromadb.ClientAPI` instance in its constructor.
- Wraps every ChromaDB call in `try`/`except`, translating ChromaDB exceptions
  into `CollectionError`, `DocumentError`, or `SearchError`.
- Delegates collection-level operations to `CollectionManager`.
- Logs every operation with duration (`execution_duration_ms`).
- Converts flat metadata filter dicts to ChromaDB's `$eq`/`$and` `where` format.
- Never logs embeddings or document content.

## Collection Lifecycle

1. **Create**: `create_collection(name)` → `CollectionManager.create(name)` →
   `client.create_collection(name=name, embedding_function=None)`.  The
   `embedding_function=None` flag tells ChromaDB to store caller-provided
   embeddings directly rather than generating them.

2. **Idempotent create**: `CollectionManager.create_if_not_exists(name)` catches
   ChromaDB's "already exists" error silently and returns.  Used by callers
   that want to ensure a collection exists without error handling.

3. **Existence check**: `collection_exists(name)` → `get_collection()` wrapped
   in try/except; returns `False` on any error.

4. **List**: `list_collections()` returns `[c.name for c in client.list_collections()]`.

5. **Delete**: `delete_collection(name)` raises `CollectionError` if the
   collection does not exist (checked via `exists()` first).

## Document Lifecycle

1. **Add**: `add_document(collection, document)` — checks for duplicate ID via
   `coll.get(ids=[id])` first, then calls `coll.add()`.  Raises `DocumentError`
   on duplicate.  Empty metadata dicts are converted to `None` (ChromaDB
   requirement).  Collections must exist; `CollectionError` is raised otherwise.

2. **Update**: `update_document(collection, document)` — calls
   `coll.upsert()`.  This is an upsert operation: it creates the document if
   it does not exist, or replaces it if it does.

3. **Get**: `get_document(collection, id)` — calls
   `coll.get(ids=[id], include=["embeddings", "metadatas", "documents"])`.
   Returns `EmbeddingDocument` or `None`.  Numpy arrays from ChromaDB are
   converted to `list[float]`.

4. **Delete**: `delete_document(collection, id)` — calls `coll.delete(ids=[id])`.
   No error is raised if the ID does not exist (ChromaDB's behavior).

## Search Flow

```
search(collection, query_vector, top_k=10, filter=None)
    │
    ▼
CollectionManager.get(collection)    # raises CollectionError if missing
    │
    ▼
_to_chroma_where(filter)             # convert flat dict → ChromaDB where
    │
    ▼
coll.query(query_embeddings=[query_vector],
           n_results=top_k,
           where=where)
    │
    ▼
_map_search_results(results)         # convert ChromaDB → list[SearchResult]
    │
    ▼
return list[SearchResult]
```

- Results are ordered by ChromaDB's default distance (ascending → most similar
  first).
- Each result carries a `rank` field (1-based index).
- Floating-point values from ChromaDB are converted to Python `float`.

## Metadata Filtering

The `search` method accepts an optional `filter` parameter: a flat dict of
metadata key-value pairs.  Only exact matches are supported.

The internal helper `_to_chroma_where()` converts the flat dict to ChromaDB's
`where` format:

| Input | ChromaDB where |
|-------|---------------|
| `{"category": "math"}` | `{"category": {"$eq": "math"}}` |
| `{"category": "math", "level": 3}` | `{"$and": [{"category": {"$eq": "math"}}, {"level": {"$eq": 3}}]}` |

No range queries, `$contains`, `$in`, or other operators are exposed.  Future
extensions can add these by expanding `_to_chroma_where()`.

## Dependency Injection

Registered by `register_vector_store(container, settings)` in
`backend/aicos/persistence/vector_store/__init__.py`:

| Service | Lifetime | Registration |
|---------|----------|-------------|
| `ChromaDBVectorStore` | Singleton | Factory creates client (Persistent or HTTP), wraps in store |
| `VectorStorePort` | Singleton | Resolves the `ChromaDBVectorStore` singleton — same instance |
| `CollectionManager` | Transient | Injected via container-resolved `ChromaDBVectorStore._client` |

Called from `register_persistence()` in `backend/aicos/persistence/__init__.py`.
Application code resolves `VectorStorePort` only:

```python
store = container.resolve(VectorStorePort)
store.create_collection("my_collection")
store.add_document("my_collection", doc)
```

## Configuration

Reuses the existing `ChromaDBConfig` model in `settings.py`:

```python
class ChromaDBConfig(BaseModel):
    host: str = "localhost"
    port: int = Field(default=8000, ge=1, le=65535)
    persist_directory: Path = Path("data/chroma")
    use_http: bool = False
```

Configured in `config/base.yaml`:

```yaml
chromadb:
  host: localhost
  port: 8000
  persist_directory: data/chroma
  use_http: false
```

When `use_http` is `False`, a `PersistentClient` is created with
`persist_directory`.  When `True`, an `HttpClient` is created pointing at
`host:port`.

## Logging

Every operation is logged at `DEBUG` level under the `aicos.database` logger.
Each log record includes:

| Field | Description |
|-------|-------------|
| `collection` | Target collection name |
| `document_id` | Document ID (for document operations) |
| `top_k` | Requested result count (search only) |
| `results_count` | Actual result count (search only) |
| `execution_duration_ms` | Wall-clock duration in milliseconds |

No embeddings or document contents are ever logged.

## Extension Points

### Adding a new vector database (e.g., FAISS, Qdrant, Pinecone)

1. Create a new implementation class that fulfills `VectorStorePort`:
   ```python
   @runtime_checkable
   class VectorStorePort(Protocol):
       ...  # same 9 methods
   ```

2. Implement all nine methods using the target database's SDK.
3. Wire it in `register_vector_store()` by replacing or branching the
   `create_store` factory.

No changes to `interfaces.py`, `models.py`, or `exceptions.py` are needed —
the protocol, data models, and exception hierarchy are provider-neutral.

### Adding new search operators (e.g., `$gt`, `$lt`, `$contains`)

Extend `_to_chroma_where()` in `chroma.py` to handle enriched filter dicts,
e.g. `{"price": {"$gt": 100}}`.  This is a ChromaDB-specific adapter and
does not affect the protocol signature.

### Adding new storage backends

The `CollectionManager` class can be extracted into a provider-neutral
interface if needed.  Currently it is ChromaDB-coupled (uses
`client.create_collection()`, `client.delete_collection()`, etc.), but it is
private to the `vector_store` package and only consumed by
`ChromaDBVectorStore`.

---

*Part of the AICOS Persistence Layer — Milestone 9C*
