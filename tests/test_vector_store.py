"""Comprehensive tests for the AICOS vector-store layer."""

from __future__ import annotations

import unittest

import chromadb

from backend.aicos.persistence import (
    ChromaDBVectorStore,
    CollectionError,
    CollectionManager,
    DocumentError,
    EmbeddingDocument,
    SearchError,
    SearchResult,
    VectorStoreError,
    VectorStorePort,
    register_persistence,
    register_vector_store,
)
from backend.aicos.persistence.exceptions import PersistenceError
from backend.aicos.settings import Settings


def _ephemeral_store() -> ChromaDBVectorStore:
    client = chromadb.EphemeralClient()
    return ChromaDBVectorStore(client)


def _make_doc(
    doc_id: str = "d1",
    content: str = "test content",
    embedding: list[float] | None = None,
) -> EmbeddingDocument:
    return EmbeddingDocument(
        id=doc_id,
        content=content,
        embedding=embedding or [0.1, 0.2, 0.3],
        metadata={"source": "test", "doc_id": doc_id},
    )


# ── Exception hierarchy ──────────────────────────────────────────────


class TestVectorStoreExceptions(unittest.TestCase):
    def test_vector_store_error_is_persistence_error(self) -> None:
        self.assertTrue(issubclass(VectorStoreError, PersistenceError))

    def test_collection_error_is_vector_store_error(self) -> None:
        self.assertTrue(issubclass(CollectionError, VectorStoreError))

    def test_document_error_is_vector_store_error(self) -> None:
        self.assertTrue(issubclass(DocumentError, VectorStoreError))

    def test_search_error_is_vector_store_error(self) -> None:
        self.assertTrue(issubclass(SearchError, VectorStoreError))


# ── Data models ──────────────────────────────────────────────────────


class TestVectorStoreModels(unittest.TestCase):
    def test_embedding_document_frozen(self) -> None:
        doc = _make_doc()
        with self.assertRaises(AttributeError):
            doc.id = "changed"  # type: ignore[misc]

    def test_embedding_document_default_metadata(self) -> None:
        doc = EmbeddingDocument(id="x", content="c", embedding=[0.0])
        self.assertEqual(doc.metadata, {})

    def test_search_result_frozen(self) -> None:
        doc = _make_doc()
        result = SearchResult(document=doc, score=0.95, rank=1)
        with self.assertRaises(AttributeError):
            result.score = 0.5  # type: ignore[misc]

    def test_search_result_ordering(self) -> None:
        d1 = _make_doc("a")
        d2 = _make_doc("b")
        r1 = SearchResult(document=d1, score=0.9, rank=1)
        r2 = SearchResult(document=d2, score=0.8, rank=2)
        results = sorted([r2, r1], key=lambda r: r.rank)
        self.assertEqual([r.document.id for r in results], ["a", "b"])


# ── EmbeddingDocument model ──────────────────────────────────────────


class TestEmbeddingDocument(unittest.TestCase):
    def test_strong_typing(self) -> None:
        doc = _make_doc()
        self.assertIsInstance(doc.id, str)
        self.assertIsInstance(doc.content, str)
        self.assertIsInstance(doc.embedding, list)
        self.assertIsInstance(doc.metadata, dict)

    def test_metadata_support(self) -> None:
        meta = {"key": "value", "num": 42}
        doc = EmbeddingDocument(id="x", content="c", embedding=[0.0], metadata=meta)
        self.assertEqual(doc.metadata["key"], "value")
        self.assertEqual(doc.metadata["num"], 42)


# ── CollectionManager ────────────────────────────────────────────────


class TestCollectionManager(unittest.TestCase):
    def setUp(self) -> None:
        self.client = chromadb.EphemeralClient()
        self.mgr = CollectionManager(self.client)

    def tearDown(self) -> None:
        for name in self.mgr.list():
            try:
                self.mgr.delete(name)
            except Exception:
                pass

    def test_create_and_exists(self) -> None:
        self.mgr.create("test_coll")
        self.assertTrue(self.mgr.exists("test_coll"))

    def test_create_duplicate_raises(self) -> None:
        self.mgr.create("test_coll")
        with self.assertRaises(CollectionError):
            self.mgr.create("test_coll")

    def test_create_if_not_exists_idempotent(self) -> None:
        self.mgr.create_if_not_exists("test_coll")
        self.mgr.create_if_not_exists("test_coll")
        self.assertTrue(self.mgr.exists("test_coll"))

    def test_delete(self) -> None:
        self.mgr.create("test_coll")
        self.mgr.delete("test_coll")
        self.assertFalse(self.mgr.exists("test_coll"))

    def test_delete_nonexistent_raises(self) -> None:
        with self.assertRaises(CollectionError):
            self.mgr.delete("nonexistent")

    def test_exists_returns_false_for_missing(self) -> None:
        self.assertFalse(self.mgr.exists("nonexistent"))

    def test_get_returns_collection(self) -> None:
        self.mgr.create("test_coll")
        coll = self.mgr.get("test_coll")
        self.assertEqual(coll.name, "test_coll")

    def test_get_nonexistent_raises(self) -> None:
        with self.assertRaises(CollectionError):
            self.mgr.get("nonexistent")

    def test_list_empty(self) -> None:
        self.assertEqual(self.mgr.list(), [])

    def test_list_returns_names(self) -> None:
        self.mgr.create("alpha")
        self.mgr.create("beta")
        names = self.mgr.list()
        self.assertIn("alpha", names)
        self.assertIn("beta", names)


# ── ChromaDBVectorStore — collection operations ──────────────────────


class TestVectorStoreCollections(unittest.TestCase):
    def setUp(self) -> None:
        self.store = _ephemeral_store()

    def tearDown(self) -> None:
        for name in self.store.list_collections():
            try:
                self.store.delete_collection(name)
            except Exception:
                pass

    def test_create_collection(self) -> None:
        self.store.create_collection("coll1")
        self.assertTrue(self.store.collection_exists("coll1"))

    def test_create_duplicate_collection_raises(self) -> None:
        self.store.create_collection("coll1")
        with self.assertRaises(CollectionError):
            self.store.create_collection("coll1")

    def test_delete_collection(self) -> None:
        self.store.create_collection("coll1")
        self.store.delete_collection("coll1")
        self.assertFalse(self.store.collection_exists("coll1"))

    def test_delete_nonexistent_collection_raises(self) -> None:
        with self.assertRaises(CollectionError):
            self.store.delete_collection("nonexistent")

    def test_collection_exists(self) -> None:
        self.assertFalse(self.store.collection_exists("coll1"))
        self.store.create_collection("coll1")
        self.assertTrue(self.store.collection_exists("coll1"))

    def test_list_collections(self) -> None:
        self.store.create_collection("alpha")
        self.store.create_collection("beta")
        names = self.store.list_collections()
        self.assertIn("alpha", names)
        self.assertIn("beta", names)

    def test_list_collections_empty(self) -> None:
        self.assertEqual(self.store.list_collections(), [])

    def test_port_protocol_satisfied(self) -> None:
        self.assertIsInstance(self.store, VectorStorePort)


# ── ChromaDBVectorStore — document operations ────────────────────────


class TestVectorStoreDocuments(unittest.TestCase):
    def setUp(self) -> None:
        self.store = _ephemeral_store()
        self.store.create_collection("docs")

    def tearDown(self) -> None:
        for name in self.store.list_collections():
            try:
                self.store.delete_collection(name)
            except Exception:
                pass

    def test_add_document(self) -> None:
        doc = _make_doc()
        self.store.add_document("docs", doc)
        retrieved = self.store.get_document("docs", "d1")
        self.assertIsNotNone(retrieved)
        assert retrieved is not None
        self.assertEqual(retrieved.content, "test content")
        self.assertEqual(retrieved.metadata["source"], "test")

    def test_add_duplicate_id_raises(self) -> None:
        doc = _make_doc()
        self.store.add_document("docs", doc)
        with self.assertRaises(DocumentError):
            self.store.add_document("docs", doc)

    def test_get_document_returns_none_when_missing(self) -> None:
        result = self.store.get_document("docs", "nonexistent")
        self.assertIsNone(result)

    def test_update_document(self) -> None:
        doc = _make_doc(content="original")
        self.store.add_document("docs", doc)

        updated = _make_doc(content="updated")
        self.store.update_document("docs", updated)

        retrieved = self.store.get_document("docs", "d1")
        assert retrieved is not None
        self.assertEqual(retrieved.content, "updated")

    def test_update_nonexistent_document(self) -> None:
        doc = _make_doc()
        self.store.update_document("docs", doc)
        retrieved = self.store.get_document("docs", "d1")
        assert retrieved is not None
        self.assertEqual(retrieved.content, doc.content)

    def test_delete_document(self) -> None:
        doc = _make_doc()
        self.store.add_document("docs", doc)
        self.store.delete_document("docs", "d1")
        self.assertIsNone(self.store.get_document("docs", "d1"))

    def test_delete_nonexistent_document(self) -> None:
        self.store.delete_document("docs", "nonexistent")
        self.assertIsNone(self.store.get_document("docs", "nonexistent"))

    def test_add_document_into_nonexistent_collection_raises(self) -> None:
        doc = _make_doc()
        with self.assertRaises(CollectionError):
            self.store.add_document("bad_coll", doc)

    def test_add_document_with_embedding(self) -> None:
        emb = [0.5, 0.6, 0.7]
        doc = EmbeddingDocument(id="e1", content="embed test", embedding=emb)
        self.store.add_document("docs", doc)
        retrieved = self.store.get_document("docs", "e1")
        assert retrieved is not None
        for a, b in zip(retrieved.embedding, emb):
            self.assertAlmostEqual(a, b, places=5)


# ── ChromaDBVectorStore — search ─────────────────────────────────────


class TestVectorStoreSearch(unittest.TestCase):
    def setUp(self) -> None:
        self.store = _ephemeral_store()
        self.store.create_collection("search_test")

        docs = [
            EmbeddingDocument(id="v1", content="cat", embedding=[0.1, 0.2, 0.3]),
            EmbeddingDocument(id="v2", content="dog", embedding=[0.4, 0.5, 0.6]),
            EmbeddingDocument(id="v3", content="bird", embedding=[0.7, 0.8, 0.9]),
        ]
        for d in docs:
            self.store.add_document("search_test", d)

    def tearDown(self) -> None:
        for name in self.store.list_collections():
            try:
                self.store.delete_collection(name)
            except Exception:
                pass

    def test_search_returns_results(self) -> None:
        results = self.store.search("search_test", [0.1, 0.2, 0.3], top_k=3)
        self.assertEqual(len(results), 3)

    def test_search_ordered_by_similarity(self) -> None:
        results = self.store.search("search_test", [0.1, 0.2, 0.3], top_k=3)
        scores = [r.score for r in results]
        self.assertEqual(scores, sorted(scores))

    def test_search_top_k(self) -> None:
        results = self.store.search("search_test", [0.1, 0.2, 0.3], top_k=2)
        self.assertLessEqual(len(results), 2)

    def test_search_empty_results(self) -> None:
        self.store.delete_collection("search_test")
        self.store.create_collection("search_test")
        results = self.store.search("search_test", [0.1, 0.2, 0.3], top_k=3)
        self.assertEqual(len(results), 0)

    def test_search_result_has_rank(self) -> None:
        results = self.store.search("search_test", [0.1, 0.2, 0.3], top_k=3)
        for i, r in enumerate(results):
            self.assertEqual(r.rank, i + 1)

    def test_search_result_has_document(self) -> None:
        results = self.store.search("search_test", [0.1, 0.2, 0.3], top_k=1)
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0].document, EmbeddingDocument)
        self.assertIsInstance(results[0].score, float)

    def test_search_into_nonexistent_collection_raises(self) -> None:
        with self.assertRaises(CollectionError):
            self.store.search("bad_coll", [0.1, 0.2, 0.3])


# ── ChromaDBVectorStore — metadata filtering ─────────────────────────


class TestVectorStoreMetadataFiltering(unittest.TestCase):
    def setUp(self) -> None:
        self.store = _ephemeral_store()
        self.store.create_collection("filter_test")

        docs = [
            EmbeddingDocument(
                id="c1", content="math doc", embedding=[0.1, 0.2],
                metadata={"category": "math", "level": 1},
            ),
            EmbeddingDocument(
                id="c2", content="science doc", embedding=[0.3, 0.4],
                metadata={"category": "science", "level": 2},
            ),
            EmbeddingDocument(
                id="c3", content="advanced math", embedding=[0.5, 0.6],
                metadata={"category": "math", "level": 3},
            ),
        ]
        for d in docs:
            self.store.add_document("filter_test", d)

    def tearDown(self) -> None:
        for name in self.store.list_collections():
            try:
                self.store.delete_collection(name)
            except Exception:
                pass

    def test_filter_by_exact_metadata(self) -> None:
        results = self.store.search(
            "filter_test", [0.1, 0.2], top_k=10,
            filter={"category": "math"},
        )
        self.assertEqual(len(results), 2)
        ids = {r.document.id for r in results}
        self.assertIn("c1", ids)
        self.assertIn("c3", ids)

    def test_filter_with_multiple_conditions(self) -> None:
        results = self.store.search(
            "filter_test", [0.1, 0.2], top_k=10,
            filter={"category": "math", "level": 3},
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].document.id, "c3")

    def test_empty_filter_returns_all(self) -> None:
        results = self.store.search("filter_test", [0.1, 0.2], top_k=10)
        self.assertEqual(len(results), 3)

    def test_filter_no_matches(self) -> None:
        results = self.store.search(
            "filter_test", [0.1, 0.2], top_k=10,
            filter={"category": "nonexistent"},
        )
        self.assertEqual(len(results), 0)


# ── Error translation ────────────────────────────────────────────────


class TestVectorStoreErrorTranslation(unittest.TestCase):
    def test_chromadb_exception_wrapped(self) -> None:
        store = _ephemeral_store()
        with self.assertRaises(CollectionError):
            store.get_document("nonexistent", "x")

    def test_search_error_type(self) -> None:
        store = _ephemeral_store()
        with self.assertRaises(CollectionError):
            store.search("nonexistent", [0.1, 0.2])

    def test_document_error_type_on_duplicate(self) -> None:
        store = _ephemeral_store()
        store.create_collection("test")
        store.add_document("test", _make_doc("d1"))
        with self.assertRaises(DocumentError):
            store.add_document("test", _make_doc("d1"))


# ── Dependency Injection ─────────────────────────────────────────────


class TestVectorStoreDependencyInjection(unittest.TestCase):
    def test_register_vector_store_resolves_port(self) -> None:
        from backend.aicos.core.di import Container

        container = Container()
        settings = Settings(config_dir="missing-config")
        settings.chromadb.persist_directory = ":memory:"
        register_persistence(container, settings)

        store = container.resolve(VectorStorePort)
        self.assertIsInstance(store, ChromaDBVectorStore)

    def test_vector_store_is_singleton(self) -> None:
        from backend.aicos.core.di import Container

        container = Container()
        settings = Settings(config_dir="missing-config")
        settings.chromadb.persist_directory = ":memory:"
        register_persistence(container, settings)

        s1 = container.resolve(VectorStorePort)
        s2 = container.resolve(VectorStorePort)
        self.assertIs(s1, s2)


# ── Integration ──────────────────────────────────────────────────────


class TestVectorStoreIntegration(unittest.TestCase):
    def test_full_lifecycle(self) -> None:
        store = _ephemeral_store()

        store.create_collection("lifecycle")
        self.assertTrue(store.collection_exists("lifecycle"))

        doc = _make_doc("l1", "full lifecycle test", embedding=[0.1, 0.2, 0.3])
        store.add_document("lifecycle", doc)

        retrieved = store.get_document("lifecycle", "l1")
        self.assertIsNotNone(retrieved)
        assert retrieved is not None
        self.assertEqual(retrieved.content, "full lifecycle test")

        updated = _make_doc("l1", "updated content", embedding=[0.1, 0.2, 0.3])
        store.update_document("lifecycle", updated)
        retrieved2 = store.get_document("lifecycle", "l1")
        assert retrieved2 is not None
        self.assertEqual(retrieved2.content, "updated content")

        results = store.search("lifecycle", [0.1, 0.2, 0.3], top_k=5)
        self.assertGreaterEqual(len(results), 1)

        store.delete_document("lifecycle", "l1")
        self.assertIsNone(store.get_document("lifecycle", "l1"))

        store.delete_collection("lifecycle")
        self.assertFalse(store.collection_exists("lifecycle"))


if __name__ == "__main__":
    unittest.main()
