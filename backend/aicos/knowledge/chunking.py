"""Chunking strategies for document splitting.

The default implementation splits text recursively on paragraph, sentence,
and word boundaries.
"""

from __future__ import annotations

import re
from typing import Any

from .exceptions import ChunkingError
from .models import Document, DocumentChunk


class RecursiveCharacterChunker:
    """Split a :class:`Document` into overlapping chunks on natural boundaries.

    Attempts to split on paragraph breaks (``\\n\\n``), then sentence
    boundaries (``. ``), then word boundaries (space).  Chunks smaller than
    ``chunk_size`` are merged; oversized chunks are re-split at the next
    boundary level.
    """

    def __init__(self) -> None:
        self._separators = ["\n\n", "\n", ". ", " "]

    def chunk(
        self,
        document: Document,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> list[DocumentChunk]:
        if chunk_size < 1:
            raise ChunkingError("chunk_size must be at least 1")
        if chunk_overlap < 0:
            raise ChunkingError("chunk_overlap must be non-negative")
        if chunk_overlap >= chunk_size:
            raise ChunkingError("chunk_overlap must be less than chunk_size")
        if not document.content.strip():
            raise ChunkingError("cannot chunk an empty document")

        texts = self._split_text(document.content, chunk_size, chunk_overlap)
        chunks: list[DocumentChunk] = []
        for i, text in enumerate(texts):
            meta: dict[str, Any] = dict(document.metadata)
            meta["chunk_index"] = i
            chunks.append(DocumentChunk(content=text, metadata=meta, chunk_index=i))
        return chunks

    def _split_text(
        self,
        text: str,
        chunk_size: int,
        chunk_overlap: int,
    ) -> list[str]:
        if len(text) <= chunk_size:
            return [text]

        results: list[str] = []
        current = text

        while current:
            if len(current) <= chunk_size:
                results.append(current)
                break

            split_point = self._find_split(current, chunk_size)
            results.append(current[:split_point].strip())
            overlap_start = max(0, split_point - chunk_overlap)
            current = current[overlap_start:]

        return results

    def _find_split(self, text: str, target: int) -> int:
        if len(text) <= target:
            return len(text)

        for sep in self._separators:
            pos = text.rfind(sep, 0, target)
            if pos > 0:
                return pos + len(sep)

        return target
