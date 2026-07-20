"""Plain-text document loader."""

from __future__ import annotations

from pathlib import Path

from ..exceptions import LoaderError
from ..models import Document


class TextLoader:
    """Load plain-text (``.txt``) files."""

    def supports(self, path: Path) -> bool:
        return path.suffix.lower() == ".txt"

    def load(self, path: Path) -> Document:
        if not path.exists():
            raise LoaderError(f"file not found: {path}")
        if not path.is_file():
            raise LoaderError(f"path is not a file: {path}")
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise LoaderError(f"could not read {path}: {exc}") from exc
        if not content.strip():
            raise LoaderError(f"file is empty: {path}")
        return Document(
            content=content,
            metadata={"source": str(path), "filename": path.name},
            source=path,
        )
