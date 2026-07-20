"""Document indexer for embedding and storing chunks.

``DocumentIndexer`` owns the embedding-generation and vector-store
concerns.  It depends only on ``EmbeddingService`` and
``VectorStorePort``.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ..ai.embeddings.models import EmbeddingRequest
from ..logging import get_logger
from ..persistence.vector_store import EmbeddingDocument

if TYPE_CHECKING:
    from ..ai.embeddings import EmbeddingService
    from ..persistence.vector_store import VectorStorePort
    from .models import DocumentChunk


class DocumentIndexer:
    """Embed chunks and persist them in the vector store."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStorePort,
    ) -> None:
        self._embedding_service = embedding_service
        self._vector_store = vector_store
        self._logger = get_logger("knowledge")

    def index(
        self,
        chunks: list[DocumentChunk],
        chunk_metas: list[dict],
        collection_name: str,
        source: Path,
    ) -> None:
        if not self._vector_store.collection_exists(collection_name):
            self._vector_store.create_collection(collection_name)

        for chunk, meta in zip(chunks, chunk_metas):
            embedding_response = self._embedding_service.embed(
                EmbeddingRequest(text=chunk.content)
            )

            emb_doc = EmbeddingDocument(
                id=f"{Path(source.name).stem}_{chunk.chunk_index}",
                content=chunk.content,
                embedding=embedding_response.embedding,
                metadata=meta,
            )
            self._vector_store.add_document(collection_name, emb_doc)
