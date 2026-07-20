"""Metadata filter construction for vector-store search.

Translates the provider-independent ``SearchFilters`` model into the
simple ``dict`` format that ``VectorStorePort.search`` expects.
"""

from __future__ import annotations

from typing import Any

from .exceptions import FilterError
from .models import SearchFilters


class MetadataFilterBuilder:
    """Build a provider-independent filter dict from ``SearchFilters``."""

    def build(self, filters: SearchFilters | None) -> dict[str, Any] | None:
        """Convert *filters* to a flat dict for vector-store search.

        Returns ``None`` when no filters are provided, allowing the
        search implementation to skip filtering entirely.
        """
        if filters is None:
            return None

        result: dict[str, Any] = {}

        if filters.source is not None:
            result["source"] = filters.source
        if filters.filename is not None:
            result["filename"] = filters.filename
        if filters.document_id is not None:
            result["document_id"] = filters.document_id
        if filters.custom_metadata is not None:
            for k, v in filters.custom_metadata.items():
                if not isinstance(k, str):
                    raise FilterError(f"filter key must be a string, got {type(k).__name__}")
                if not k.strip():
                    raise FilterError("filter key must not be empty")
                result[k] = v

        return result if result else None
