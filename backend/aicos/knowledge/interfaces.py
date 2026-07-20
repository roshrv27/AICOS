"""Provider-neutral protocols for knowledge ingestion.

Application code depends **only** on :class:`DocumentLoader` and
:class:`ChunkingStrategy`.  Concrete implementations are wired via DI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from .models import Document, DocumentChunk


@runtime_checkable
class DocumentLoader(Protocol):
    """Strategy for loading a document from a file path.

    Implementations detect file type via :meth:`supports` and parse the
    content in :meth:`load`.
    """

    def supports(self, path: Path) -> bool:
        """Return ``True`` when this loader can handle *path*."""
        ...

    def load(self, path: Path) -> Document:
        """Load *path* and return a :class:`Document`.

        Raises :class:`LoaderError` when the file is missing, unreadable,
        or contains unsupported content.
        """
        ...


@runtime_checkable
class ChunkingStrategy(Protocol):
    """Strategy for splitting a :class:`Document` into chunks.

    Implementations must preserve chunk order and carry base metadata
    from the source document into each chunk.
    """

    def chunk(
        self,
        document: Document,
        chunk_size: int,
        chunk_overlap: int,
    ) -> list[DocumentChunk]:
        """Split *document* into a list of ordered chunks.

        Raises :class:`ChunkingError` when the document cannot be split.
        """
        ...
