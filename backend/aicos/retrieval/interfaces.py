"""Provider-neutral protocols for retrieval.

Application code depends **only** on the protocols defined here.
Concrete implementations are wired via DI.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import QueryRequest, RetrievedChunk


@runtime_checkable
class RankingStrategy(Protocol):
    """Strategy for ranking retrieved chunks by relevance."""

    def rank(
        self,
        chunks: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        """Sort *chunks* by score descending and reassign ranks.

        Returns a new list sorted in descending order of ``score``.
        Does not mutate the input list.
        """
        ...


@runtime_checkable
class QueryValidator(Protocol):
    """Protocol for query validation and normalization."""

    def validate_and_normalize(self, query: str) -> str:
        """Validate and normalize *query*.

        Returns the normalized query string.
        Raises :class:`QueryValidationError` when the query is invalid.
        """
        ...
