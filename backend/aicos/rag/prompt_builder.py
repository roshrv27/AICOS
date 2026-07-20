"""Prompt assembly for RAG.

``PromptBuilder`` constructs a structured prompt from system instructions,
a user query, and retrieved context chunks.  It truncates context when
the estimated token count exceeds ``max_prompt_tokens``.
"""

from __future__ import annotations

from .exceptions import PromptBuildError
from .models import ContextChunk, Prompt, PromptSection

_CHARS_PER_TOKEN = 4


class PromptBuilder:
    """Assemble prompts from system prompt, query, and context chunks."""

    def build(
        self,
        system_prompt: str,
        query: str,
        context_chunks: list[ContextChunk],
        max_context_chunks: int = 5,
        max_prompt_tokens: int = 4096,
    ) -> Prompt:
        if not query.strip():
            raise PromptBuildError("query must not be empty")
        if not system_prompt.strip():
            raise PromptBuildError("system prompt must not be empty")

        limited = context_chunks[:max_context_chunks]

        context_text = self._format_context(limited)

        user_content = f"Context:\n{context_text}\n\nQuestion: {query}" if context_text else query

        sections = [
            PromptSection(role="system", content=system_prompt.strip()),
            PromptSection(role="user", content=user_content),
        ]

        token_count = self._estimate_tokens(sections)

        if token_count > max_prompt_tokens:
            truncated = self._truncate_context(limited, max_prompt_tokens, system_prompt, query)
            sections = [
                PromptSection(role="system", content=system_prompt.strip()),
                PromptSection(
                    role="user",
                    content=f"Context:\n{self._format_context(truncated)}\n\nQuestion: {query}"
                    if truncated
                    else query,
                ),
            ]
            token_count = self._estimate_tokens(sections)

        return Prompt(
            sections=sections,
            context_chunks=limited,
            token_count=token_count,
        )

    @staticmethod
    def _format_context(chunks: list[ContextChunk]) -> str:
        parts = []
        for i, chunk in enumerate(chunks):
            src = chunk.metadata.get("source", chunk.metadata.get("filename", f"chunk_{chunk.chunk_id}"))
            parts.append(f"[{i + 1}] Source: {src}\n{chunk.content}")
        return "\n\n".join(parts)

    @staticmethod
    def _estimate_tokens(sections: list[PromptSection]) -> int:
        total_chars = sum(len(s.content) for s in sections)
        return max(1, total_chars // _CHARS_PER_TOKEN)

    @staticmethod
    def _truncate_context(
        chunks: list[ContextChunk],
        max_tokens: int,
        system_prompt: str,
        query: str,
    ) -> list[ContextChunk]:
        overhead = (
            len(system_prompt)
            + len(query)
            + len("Context:\n\n\nQuestion: ")
            + sum(
                len(f"[{i + 1}] Source: {c.metadata.get('source', c.metadata.get('filename', f'chunk_{c.chunk_id}'))}\n")
                for i, c in enumerate(chunks)
            )
        ) // _CHARS_PER_TOKEN
        budget = max_tokens - overhead

        truncated: list[ContextChunk] = []
        used = 0
        for chunk in chunks:
            chunk_tokens = max(1, len(chunk.content) // _CHARS_PER_TOKEN)
            if used + chunk_tokens > budget:
                break
            truncated.append(chunk)
            used += chunk_tokens

        return truncated
