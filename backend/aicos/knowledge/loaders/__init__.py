"""Document loader implementations.

Each loader implements the :class:`DocumentLoader` protocol and handles a
specific file format.
"""

from __future__ import annotations

from .markdown_loader import MarkdownLoader
from .pdf_loader import PDFLoader
from .text_loader import TextLoader

__all__ = [
    "MarkdownLoader",
    "PDFLoader",
    "TextLoader",
]
