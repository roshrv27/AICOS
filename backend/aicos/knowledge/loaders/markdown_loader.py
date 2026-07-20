"""Markdown document loader.

Strips basic Markdown formatting  (headings, bold, italic, code fences, lists)
to yield plain text.  No AST parsing — lightweight regex approach.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..exceptions import LoaderError
from ..models import Document


class MarkdownLoader:
    """Load Markdown (``.md``) files, stripping formatting."""

    def supports(self, path: Path) -> bool:
        return path.suffix.lower() == ".md"

    def load(self, path: Path) -> Document:
        if not path.exists():
            raise LoaderError(f"file not found: {path}")
        if not path.is_file():
            raise LoaderError(f"path is not a file: {path}")
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise LoaderError(f"could not read {path}: {exc}") from exc
        if not raw.strip():
            raise LoaderError(f"file is empty: {path}")
        content = _strip_markdown(raw)
        return Document(
            content=content,
            metadata={
                "source": str(path),
                "filename": path.name,
                "format": "markdown",
            },
            source=path,
        )


def _strip_markdown(text: str) -> str:
    """Remove common Markdown formatting, preserving content."""
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"_(.*?)_", r"\1", text)
    text = re.sub(r"`{1,3}[^`]*`{1,3}", "", text)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^---+\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    return text.strip()
