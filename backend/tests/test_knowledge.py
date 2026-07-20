"""Tests for the knowledge-ingestion pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from aicos.knowledge.chunking import RecursiveCharacterChunker
from aicos.knowledge.exceptions import LoaderError
from aicos.knowledge.loaders import MarkdownLoader, PDFLoader, TextLoader
from aicos.knowledge.metadata import MetadataExtractor
from aicos.knowledge.models import Document, DocumentChunk, IngestionRequest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_text(tmp_path: Path) -> Path:
    p = tmp_path / "sample.txt"
    p.write_text("Hello world. This is a test document.")
    return p


@pytest.fixture
def sample_markdown(tmp_path: Path) -> Path:
    p = tmp_path / "sample.md"
    p.write_text("# Title\n\n**bold** and *italic* text.\n\n- list item")
    return p


@pytest.fixture
def empty_file(tmp_path: Path) -> Path:
    p = tmp_path / "empty.txt"
    p.write_text("")
    return p


# ---------------------------------------------------------------------------
# TextLoader
# ---------------------------------------------------------------------------

class TestTextLoader:
    def test_supports_txt(self) -> None:
        assert TextLoader().supports(Path("foo.txt"))
        assert not TextLoader().supports(Path("foo.md"))

    def test_load(self, sample_text: Path) -> None:
        doc = TextLoader().load(sample_text)
        assert isinstance(doc, Document)
        assert "Hello world" in doc.content
        assert doc.metadata["filename"] == "sample.txt"

    def test_load_missing(self) -> None:
        with pytest.raises(LoaderError, match="file not found"):
            TextLoader().load(Path("/nonexistent/file.txt"))

    def test_load_empty(self, empty_file: Path) -> None:
        with pytest.raises(LoaderError, match="empty"):
            TextLoader().load(empty_file)


# ---------------------------------------------------------------------------
# MarkdownLoader
# ---------------------------------------------------------------------------

class TestMarkdownLoader:
    def test_supports_md(self) -> None:
        assert MarkdownLoader().supports(Path("foo.md"))
        assert not MarkdownLoader().supports(Path("foo.txt"))

    def test_load_strips_formatting(self, sample_markdown: Path) -> None:
        doc = MarkdownLoader().load(sample_markdown)
        assert "Title" in doc.content
        assert "bold" in doc.content
        assert "italic" in doc.content
        assert "list item" in doc.content
        assert "**" not in doc.content

    def test_load_missing(self) -> None:
        with pytest.raises(LoaderError, match="file not found"):
            MarkdownLoader().load(Path("/nonexistent/file.md"))


# ---------------------------------------------------------------------------
# PDFLoader
# ---------------------------------------------------------------------------

class TestPDFLoader:
    def test_supports_pdf(self) -> None:
        assert PDFLoader().supports(Path("foo.pdf"))
        assert not PDFLoader().supports(Path("foo.txt"))

    def test_load_missing(self) -> None:
        try:
            PDFLoader().load(Path("/nonexistent/file.pdf"))
            pytest.fail("expected LoaderError")
        except LoaderError:
            pass


# ---------------------------------------------------------------------------
# RecursiveCharacterChunker
# ---------------------------------------------------------------------------

class TestRecursiveCharacterChunker:
    def test_chunk_small_document(self) -> None:
        doc = Document(content="Hello world.")
        chunks = RecursiveCharacterChunker().chunk(doc, chunk_size=1000)
        assert len(chunks) == 1
        assert chunks[0].content == "Hello world."

    def test_chunk_split_on_paragraph(self) -> None:
        content = "A" * 300 + "\n\n" + "B" * 300
        doc = Document(content=content)
        chunks = RecursiveCharacterChunker().chunk(doc, chunk_size=400, chunk_overlap=50)
        assert len(chunks) >= 1

    def test_chunk_empty_document(self) -> None:
        doc = Document(content="   ")
        with pytest.raises(Exception):
            RecursiveCharacterChunker().chunk(doc)

    def test_chunk_index_in_metadata(self) -> None:
        content = "word " * 500
        doc = Document(content=content)
        chunks = RecursiveCharacterChunker().chunk(doc, chunk_size=200, chunk_overlap=20)
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i
            assert chunk.metadata.get("chunk_index") == i

    def test_invalid_params(self) -> None:
        doc = Document(content="test")
        with pytest.raises(Exception):
            RecursiveCharacterChunker().chunk(doc, chunk_size=0)
        with pytest.raises(Exception):
            RecursiveCharacterChunker().chunk(doc, chunk_size=100, chunk_overlap=-1)
        with pytest.raises(Exception):
            RecursiveCharacterChunker().chunk(doc, chunk_size=100, chunk_overlap=200)


# ---------------------------------------------------------------------------
# MetadataExtractor
# ---------------------------------------------------------------------------

class TestMetadataExtractor:
    def test_extract_base(self) -> None:
        doc = Document(content="hello world foo bar", metadata={"source": "test.txt"})
        meta = MetadataExtractor().extract_base(doc)
        assert meta["source"] == "test.txt"
        assert meta["word_count"] == 4
        assert meta["char_count"] == 19
        assert "document_hash" in meta
        assert "ingested_at" in meta

    def test_extract_chunk(self) -> None:
        chunk = DocumentChunk(content="hello world", chunk_index=0)
        meta = MetadataExtractor().extract_chunk(chunk)
        assert meta["chunk_word_count"] == 2
        assert meta["chunk_char_count"] == 11


# ---------------------------------------------------------------------------
# IngestionRequest
# ---------------------------------------------------------------------------

class TestIngestionRequest:
    def test_defaults(self, sample_text: Path) -> None:
        req = IngestionRequest(source=sample_text)
        assert req.collection_name == "knowledge"
        assert req.chunk_size == 1000
        assert req.chunk_overlap == 200
