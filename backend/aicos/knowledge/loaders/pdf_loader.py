"""PDF document loader.

Attempts to import ``PyMuPDF`` (``fitz``) — if unavailable a helpful
``LoaderError`` is raised at runtime.
"""

from __future__ import annotations

from pathlib import Path

from ..exceptions import LoaderError
from ..models import Document

_PDF_IMPORT_ERROR: str | None = None

try:
    import fitz  # type: ignore[import-untyped]
except ImportError:
    _PDF_IMPORT_ERROR = (
        "PyMuPDF (fitz) is required to load PDF files. "
        "Install it with: pip install PyMuPDF"
    )


class PDFLoader:
    """Load PDF (``.pdf``) files via PyMuPDF."""

    def supports(self, path: Path) -> bool:
        return path.suffix.lower() == ".pdf"

    def load(self, path: Path) -> Document:
        if _PDF_IMPORT_ERROR is not None:
            raise LoaderError(_PDF_IMPORT_ERROR)
        if not path.exists():
            raise LoaderError(f"file not found: {path}")
        if not path.is_file():
            raise LoaderError(f"path is not a file: {path}")
        try:
            doc = fitz.open(str(path))
        except Exception as exc:
            raise LoaderError(f"could not open PDF {path}: {exc}") from exc

        pages: list[str] = []
        page_count = 0
        try:
            page_count = len(doc)
            for page_num in range(page_count):
                page = doc.load_page(page_num)
                text = page.get_text()
                pages.append(text)
        except Exception as exc:
            raise LoaderError(f"could not read PDF {path}: {exc}") from exc
        finally:
            doc.close()

        content = "\n\n".join(pages).strip()
        if not content:
            raise LoaderError(f"PDF file contains no extractable text: {path}")

        return Document(
            content=content,
            metadata={
                "source": str(path),
                "filename": path.name,
                "format": "pdf",
                "page_count": page_count,
            },
            source=path,
        )
