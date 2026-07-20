"""Metadata extraction for documents and chunks.

Generates structural metadata (source, filename, chunk index, timestamps,
statistics).  No AI-generated or semantic metadata is produced.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

from .models import Document, DocumentChunk


class MetadataExtractor:
    """Extract structural metadata from documents and their chunks."""

    def extract_base(self, document: Document) -> dict[str, Any]:
        """Return metadata common to all chunks of a document."""
        content = document.content
        word_count = len(content.split())
        char_count = len(content)
        doc_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

        meta: dict[str, Any] = dict(document.metadata)
        meta["word_count"] = word_count
        meta["char_count"] = char_count
        meta["document_hash"] = doc_hash
        meta["ingested_at"] = int(time.time())
        return meta

    def extract_chunk(self, chunk: DocumentChunk) -> dict[str, Any]:
        """Return metadata for a single chunk, derived from its content."""
        word_count = len(chunk.content.split())
        char_count = len(chunk.content)

        meta: dict[str, Any] = dict(chunk.metadata)
        meta["chunk_word_count"] = word_count
        meta["chunk_char_count"] = char_count
        return meta
