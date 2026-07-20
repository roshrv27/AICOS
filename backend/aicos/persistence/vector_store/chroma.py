"""ChromaDB-backed implementation of the VectorStorePort protocol."""

from __future__ import annotations

import time
from typing import Any

import chromadb

from ...logging import get_logger
from collections.abc import Mapping

from .collections import CollectionManager
from .exceptions import CollectionError, DocumentError, SearchError
from .models import EmbeddingDocument, SearchResult


class ChromaDBVectorStore:
    """Vector-store implementation backed by ChromaDB.

    Initialise with a pre-configured ChromaDB client::

        client = chromadb.PersistentClient(path=settings.chromadb.persist_directory)
        store = ChromaDBVectorStore(client)
    """

    def __init__(self, client: chromadb.ClientAPI) -> None:
        self._client = client
        self._collections = CollectionManager(client)
        self._logger = get_logger("database")

    # ── collection operations ──────────────────────────────────────

    def create_collection(self, name: str) -> None:
        self._collections.create(name)

    def delete_collection(self, name: str) -> None:
        self._collections.delete(name)

    def collection_exists(self, name: str) -> bool:
        return self._collections.exists(name)

    def list_collections(self) -> list[str]:
        return self._collections.list()

    # ── document operations ────────────────────────────────────────

    def add_document(self, collection: str, document: EmbeddingDocument) -> None:
        started_at = time.perf_counter()
        try:
            coll = self._collections.get(collection)
            existing = coll.get(ids=[document.id])
            if existing and existing.get("ids"):
                raise DocumentError(
                    f"document '{document.id}' already exists in collection '{collection}'"
                )
            meta: dict[str, Any] | None = document.metadata if document.metadata else None
            coll.add(
                ids=[document.id],
                embeddings=[document.embedding],
                metadatas=meta,
                documents=[document.content],
            )
        except CollectionError:
            raise
        except DocumentError:
            raise
        except Exception as exc:
            raise DocumentError(str(exc)) from exc
        self._logger.debug(
            "document added",
            extra={
                "collection": collection,
                "document_id": document.id,
                "execution_duration_ms": (time.perf_counter() - started_at) * 1000,
            },
        )

    def update_document(self, collection: str, document: EmbeddingDocument) -> None:
        started_at = time.perf_counter()
        try:
            coll = self._collections.get(collection)
            meta: dict[str, Any] | None = document.metadata if document.metadata else None
            coll.upsert(
                ids=[document.id],
                embeddings=[document.embedding],
                metadatas=meta,
                documents=[document.content],
            )
        except CollectionError:
            raise
        except Exception as exc:
            raise DocumentError(str(exc)) from exc
        self._logger.debug(
            "document updated",
            extra={
                "collection": collection,
                "document_id": document.id,
                "execution_duration_ms": (time.perf_counter() - started_at) * 1000,
            },
        )

    def delete_document(self, collection: str, document_id: str) -> None:
        started_at = time.perf_counter()
        try:
            coll = self._collections.get(collection)
            coll.delete(ids=[document_id])
        except CollectionError:
            raise
        except Exception as exc:
            raise DocumentError(str(exc)) from exc
        self._logger.debug(
            "document deleted",
            extra={
                "collection": collection,
                "document_id": document_id,
                "execution_duration_ms": (time.perf_counter() - started_at) * 1000,
            },
        )

    def get_document(self, collection: str, document_id: str) -> EmbeddingDocument | None:
        started_at = time.perf_counter()
        try:
            coll = self._collections.get(collection)
            result = coll.get(ids=[document_id], include=["embeddings", "metadatas", "documents"])
        except CollectionError:
            raise
        except Exception as exc:
            raise DocumentError(str(exc)) from exc

        if not result or not result.get("ids"):
            return None

        doc = _chroma_result_to_document(result, 0)
        self._logger.debug(
            "document retrieved",
            extra={
                "collection": collection,
                "document_id": document_id,
                "execution_duration_ms": (time.perf_counter() - started_at) * 1000,
            },
        )
        return doc

    # ── search ─────────────────────────────────────────────────────

    def search(
        self,
        collection: str,
        query_vector: list[float],
        top_k: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        started_at = time.perf_counter()
        try:
            coll = self._collections.get(collection)
            where = _to_chroma_where(filter) if filter else None
            results = coll.query(
                query_embeddings=[query_vector],
                n_results=top_k,
                where=where,
            )
        except CollectionError:
            raise
        except Exception as exc:
            raise SearchError(str(exc)) from exc

        mapped = _map_search_results(results)
        self._logger.debug(
            "search executed",
            extra={
                "collection": collection,
                "top_k": top_k,
                "results_count": len(mapped),
                "execution_duration_ms": (time.perf_counter() - started_at) * 1000,
            },
        )
        return mapped


# ── internal helpers ──────────────────────────────────────────────────


def _to_chroma_where(filter: dict[str, Any]) -> dict[str, Any]:
    """Convert a flat metadata filter to ChromaDB's ``where`` format.

    Single-key: ``{"category": "math"}`` → ``{"category": {"$eq": "math"}}``
    Multi-key: ``{"category": "math", "level": 3}`` → ``{"$and": [{"category": {"$eq": "math"}}, {"level": {"$eq": 3}}]}``
    """
    if not filter:
        return {}
    if len(filter) == 1:
        key = next(iter(filter))
        return {key: {"$eq": filter[key]}}
    return {"$and": [{k: {"$eq": v}} for k, v in filter.items()]}


def _chroma_result_to_document(result: dict[str, Any], index: int) -> EmbeddingDocument:
    """Extract one document from a ChromaDB get/query result dict."""
    ids = result.get("ids", [])
    raw_embeddings = result.get("embeddings")
    raw_metadatas = result.get("metadatas")
    documents_list = result.get("documents", [])

    emb: list[float] = []
    if raw_embeddings is not None and index < len(raw_embeddings) and raw_embeddings[index] is not None:
        emb = [float(v) for v in raw_embeddings[index]]

    meta: dict[str, Any] = {}
    if raw_metadatas is not None and index < len(raw_metadatas) and raw_metadatas[index] is not None:
        meta = dict(raw_metadatas[index])

    return EmbeddingDocument(
        id=ids[index],
        content=documents_list[index] if documents_list else "",
        embedding=emb,
        metadata=meta,
    )


def _map_search_results(results: dict[str, Any]) -> list[SearchResult]:
    """Convert a ChromaDB query result dict to a sorted list of SearchResult."""
    mapped: list[SearchResult] = []
    ids_list = results.get("ids", [[]])[0]
    distances_list = results.get("distances", [[]])[0]
    documents_list = results.get("documents", [[]])[0]
    raw_embeddings = results.get("embeddings")
    raw_metadatas = results.get("metadatas")

    for i, doc_id in enumerate(ids_list):
        doc_content = documents_list[i] if documents_list and i < len(documents_list) else ""
        doc_emb: list[float] = []
        if raw_embeddings is not None and raw_embeddings[0] is not None and i < len(raw_embeddings[0]) and raw_embeddings[0][i] is not None:
            doc_emb = [float(v) for v in raw_embeddings[0][i]]
        doc_meta: dict[str, Any] = {}
        if raw_metadatas is not None and raw_metadatas[0] is not None and i < len(raw_metadatas[0]) and raw_metadatas[0][i] is not None:
            doc_meta = dict(raw_metadatas[0][i])

        document = EmbeddingDocument(
            id=doc_id,
            content=doc_content,
            embedding=doc_emb,
            metadata=doc_meta,
        )
        score = float(distances_list[i]) if distances_list and i < len(distances_list) else 0.0
        mapped.append(SearchResult(document=document, score=score, rank=i + 1))

    return mapped
