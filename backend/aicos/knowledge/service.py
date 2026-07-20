"""Application-facing knowledge ingestion service.

``KnowledgeIngestionService`` is the single entry point for ingesting
documents.  It orchestrates loading, chunking, metadata extraction,
and invokes ``DocumentIndexer`` for embedding and storage.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

from ..logging import get_logger
from .exceptions import LoaderError
from .models import IngestionRequest, IngestionResult, IngestionSummary

if TYPE_CHECKING:
    from .chunking import RecursiveCharacterChunker
    from .indexer import DocumentIndexer
    from .interfaces import DocumentLoader
    from .metadata import MetadataExtractor


class KnowledgeIngestionService:
    """Orchestrate document ingestion: load → chunk → extract → index.

    Depends only on protocols and project services — never on concrete
    providers or infrastructure.
    """

    def __init__(
        self,
        loaders: list[DocumentLoader],
        chunker: RecursiveCharacterChunker,
        metadata_extractor: MetadataExtractor,
        indexer: DocumentIndexer,
    ) -> None:
        self._loaders = loaders
        self._chunker = chunker
        self._metadata_extractor = metadata_extractor
        self._indexer = indexer
        self._logger = get_logger("knowledge")

    def ingest(self, request: IngestionRequest) -> IngestionResult:
        started_at = time.perf_counter()
        source = request.source

        if not source.exists():
            raise LoaderError(f"source path does not exist: {source}")

        loader = self._find_loader(source)
        document = loader.load(source)

        chunks = self._chunker.chunk(
            document,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
        )

        base_meta = self._metadata_extractor.extract_base(document)

        chunk_metas: list[dict] = []
        for chunk in chunks:
            combined_meta = {
                **base_meta,
                **self._metadata_extractor.extract_chunk(chunk),
            }
            chunk_metas.append({**combined_meta, **chunk.metadata})

        self._indexer.index(chunks, chunk_metas, request.collection_name, source)

        total_chars = base_meta.get("char_count", 0)
        total_words = base_meta.get("word_count", 0)
        summary = IngestionSummary(
            total_chunks=len(chunks),
            total_characters=total_chars,
            total_words=total_words,
        )
        self._logger.debug(
            "ingestion completed",
            extra={
                "source": str(source),
                "collection": request.collection_name,
                "chunks": len(chunks),
                "characters": total_chars,
                "words": total_words,
                "execution_duration_ms": (time.perf_counter() - started_at) * 1000,
            },
        )
        return IngestionResult(
            collection_name=request.collection_name,
            chunks_ingested=len(chunks),
            summary=summary,
        )

    def _find_loader(self, path: Path) -> DocumentLoader:
        for loader in self._loaders:
            if loader.supports(path):
                return loader
        raise LoaderError(f"unsupported file extension: {path.suffix}")
