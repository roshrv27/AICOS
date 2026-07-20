"""Knowledge ingestion exception hierarchy.

All exceptions extend :class:`KnowledgeIngestionError` so that upstream code
can catch a single base type.  No loader-specific or library-specific
exceptions escape this layer.
"""


class KnowledgeIngestionError(Exception):
    """Base exception for all knowledge-ingestion operations."""


class LoaderError(KnowledgeIngestionError):
    """Raised when a document loader fails (missing file, unsupported format)."""


class ChunkingError(KnowledgeIngestionError):
    """Raised when document chunking fails."""


class MetadataError(KnowledgeIngestionError):
    """Raised when metadata extraction fails."""


class StorageError(KnowledgeIngestionError):
    """Raised when embedding or vector-store storage fails."""
