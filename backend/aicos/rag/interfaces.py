"""Provider-neutral protocols for RAG orchestration.

Application code depends **only** on the protocols defined here.
Concrete implementations are wired via DI.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import Citation, ContextChunk, GenerationResult, Prompt, PromptSection


@runtime_checkable
class PromptBuilderProtocol(Protocol):
    """Strategy for assembling a prompt from system prompt, query, and context."""

    def build(
        self,
        system_prompt: str,
        query: str,
        context_chunks: list[ContextChunk],
        max_context_chunks: int = 5,
        max_prompt_tokens: int = 4096,
    ) -> Prompt:
        """Assemble a :class:`Prompt` from the given components.

        The builder truncates context when *max_prompt_tokens* would be
        exceeded and limits the number of chunks to *max_context_chunks*.
        No AI rewriting, summarization, or reordering occurs.
        """
        ...


@runtime_checkable
class CitationBuilderProtocol(Protocol):
    """Strategy for building citations from context chunks."""

    def build(self, context_chunks: list[ContextChunk]) -> list[Citation]:
        """Build deduplicated citations from *context_chunks*.

        Preserves retrieval order.  Duplicates (same ``chunk_id``) are
        removed, keeping the first occurrence.
        """
        ...


@runtime_checkable
class GenerationServiceProtocol(Protocol):
    """Strategy for generating an answer from a prompt via an LLM."""

    async def generate(self, prompt: Prompt) -> GenerationResult:
        """Generate an answer from *prompt*.

        Translates provider/LLM exceptions into :class:`GenerationError`.
        Returns a provider-independent :class:`GenerationResult`.
        """
        ...
