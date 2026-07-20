"""Comprehensive tests for the AICOS embedding infrastructure.

No tests require a running Ollama server — provider interactions are mocked.
"""

from __future__ import annotations

import json
import unittest
import urllib.error
from io import BytesIO
from typing import Any
from unittest.mock import MagicMock, patch

from backend.aicos.ai.embeddings import (
    ConfigurationError,
    EmbeddingBatchRequest,
    EmbeddingBatchResponse,
    EmbeddingError,
    EmbeddingGenerationError,
    EmbeddingProvider,
    EmbeddingRequest,
    EmbeddingResponse,
    EmbeddingService,
    ModelInfo,
    ModelNotFoundError,
    OllamaEmbeddingProvider,
    ProviderUnavailableError,
    register_embeddings,
)
from backend.aicos.settings import Settings


# ── helpers ──────────────────────────────────────────────────────────


def _make_provider(model: str = "qwen-test") -> OllamaEmbeddingProvider:
    return OllamaEmbeddingProvider(
        base_url="http://localhost:11434",
        model=model,
        timeout_seconds=30,
    )


def _mock_response(data: dict[str, Any], status: int = 200) -> MagicMock:
    m = MagicMock()
    m.__enter__.return_value = m
    m.read.return_value = json.dumps(data).encode("utf-8")
    m.status = status
    return m


# ── Exception hierarchy ──────────────────────────────────────────────


class TestEmbeddingExceptions(unittest.TestCase):
    def test_embedding_error_is_base(self) -> None:
        self.assertTrue(issubclass(ProviderUnavailableError, EmbeddingError))
        self.assertTrue(issubclass(ModelNotFoundError, EmbeddingError))
        self.assertTrue(issubclass(EmbeddingGenerationError, EmbeddingError))
        self.assertTrue(issubclass(ConfigurationError, EmbeddingError))

    def test_exception_can_be_raised(self) -> None:
        with self.assertRaises(EmbeddingError):
            raise ProviderUnavailableError("test")
        with self.assertRaises(EmbeddingError):
            raise ModelNotFoundError("test")
        with self.assertRaises(EmbeddingError):
            raise EmbeddingGenerationError("test")
        with self.assertRaises(EmbeddingError):
            raise ConfigurationError("test")


# ── Data models ──────────────────────────────────────────────────────


class TestEmbeddingModels(unittest.TestCase):
    def test_embedding_request_frozen(self) -> None:
        req = EmbeddingRequest(text="hello")
        with self.assertRaises(AttributeError):
            req.text = "world"  # type: ignore[misc]

    def test_embedding_batch_request_frozen(self) -> None:
        req = EmbeddingBatchRequest(texts=["a", "b"])
        with self.assertRaises(AttributeError):
            req.texts = []  # type: ignore[misc]

    def test_embedding_response_frozen(self) -> None:
        resp = EmbeddingResponse(embedding=[0.1], dimensions=1, model="m")
        with self.assertRaises(AttributeError):
            resp.model = "n"  # type: ignore[misc]

    def test_embedding_batch_response_frozen(self) -> None:
        resp = EmbeddingBatchResponse(
            embeddings=[[0.1], [0.2]], dimensions=1, model="m"
        )
        with self.assertRaises(AttributeError):
            resp.model = "n"  # type: ignore[misc]

    def test_model_info_frozen(self) -> None:
        info = ModelInfo(name="m", dimensions=768, available=True)
        with self.assertRaises(AttributeError):
            info.available = False  # type: ignore[misc]

    def test_embedding_response_types(self) -> None:
        resp = EmbeddingResponse(
            embedding=[0.1, 0.2, 0.3], dimensions=3, model="qwen"
        )
        self.assertIsInstance(resp.embedding, list)
        self.assertEqual(resp.dimensions, 3)
        self.assertEqual(resp.model, "qwen")

    def test_batch_response_ordering_preserved(self) -> None:
        resp = EmbeddingBatchResponse(
            embeddings=[[0.1], [0.2], [0.3]], dimensions=1, model="m"
        )
        self.assertEqual(len(resp.embeddings), 3)
        self.assertEqual(resp.embeddings[0], [0.1])
        self.assertEqual(resp.embeddings[2], [0.3])


# ── Protocol ─────────────────────────────────────────────────────────


class TestEmbeddingProtocol(unittest.TestCase):
    def test_ollama_provider_satisfies_protocol(self) -> None:
        provider = _make_provider()
        self.assertIsInstance(provider, EmbeddingProvider)

    def test_protocol_runtime_checkable(self) -> None:
        self.assertTrue(hasattr(EmbeddingProvider, "__instancecheck__"))


# ── OllamaEmbeddingProvider — single embed ───────────────────────────


class TestOllamaEmbedSingle(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = _make_provider()

    @patch("urllib.request.urlopen")
    def test_embed_returns_response(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _mock_response(
            {"model": "qwen-test", "embeddings": [[0.1, 0.2, 0.3]]}
        )
        resp = self.provider.embed("hello world")
        self.assertIsInstance(resp, EmbeddingResponse)
        self.assertEqual(resp.embedding, [0.1, 0.2, 0.3])
        self.assertEqual(resp.dimensions, 3)
        self.assertEqual(resp.model, "qwen-test")

    @patch("urllib.request.urlopen")
    def test_embed_sends_correct_payload(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _mock_response(
            {"model": "qwen-test", "embeddings": [[0.1]]}
        )
        self.provider.embed("test text")
        request = mock_urlopen.call_args[0][0]
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(body["model"], "qwen-test")
        self.assertEqual(body["input"], "test text")

    @patch("urllib.request.urlopen")
    def test_embed_raises_on_empty_embeddings(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _mock_response(
            {"model": "qwen-test", "embeddings": []}
        )
        with self.assertRaises(EmbeddingGenerationError):
            self.provider.embed("hello")


# ── OllamaEmbeddingProvider — batch embed ────────────────────────────


class TestOllamaEmbedBatch(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = _make_provider()

    @patch("urllib.request.urlopen")
    def test_embed_batch_returns_response(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _mock_response(
            {
                "model": "qwen-test",
                "embeddings": [[0.1, 0.2], [0.3, 0.4]],
            }
        )
        resp = self.provider.embed_batch(["a", "b"])
        self.assertIsInstance(resp, EmbeddingBatchResponse)
        self.assertEqual(len(resp.embeddings), 2)
        self.assertEqual(resp.dimensions, 2)

    @patch("urllib.request.urlopen")
    def test_embed_batch_sends_list(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _mock_response(
            {"model": "qwen-test", "embeddings": [[0.1], [0.2]]}
        )
        self.provider.embed_batch(["x", "y"])
        request = mock_urlopen.call_args[0][0]
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(body["input"], ["x", "y"])

    @patch("urllib.request.urlopen")
    def test_embed_batch_preserves_order(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _mock_response(
            {
                "model": "qwen-test",
                "embeddings": [[0.5], [0.6], [0.7]],
            }
        )
        resp = self.provider.embed_batch(["c", "b", "a"])
        self.assertEqual(resp.embeddings[0], [0.5])
        self.assertEqual(resp.embeddings[2], [0.7])


# ── OllamaEmbeddingProvider — health check ───────────────────────────


class TestOllamaHealthCheck(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_health_check_returns_true_when_reachable(
        self, mock_urlopen: MagicMock
    ) -> None:
        mock_urlopen.return_value = _mock_response({})
        provider = _make_provider()
        self.assertTrue(provider.health_check())

    @patch("urllib.request.urlopen", side_effect=Exception("unreachable"))
    def test_health_check_returns_false_when_unreachable(
        self, mock_urlopen: MagicMock
    ) -> None:
        provider = _make_provider()
        self.assertFalse(provider.health_check())


# ── OllamaEmbeddingProvider — model info ─────────────────────────────


class TestOllamaModelInfo(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_model_info_available(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _mock_response({})
        provider = _make_provider()
        info = provider.model_info()
        self.assertEqual(info.name, "qwen-test")
        self.assertTrue(info.available)

    @patch("urllib.request.urlopen", side_effect=Exception("unreachable"))
    def test_model_info_unavailable(self, mock_urlopen: MagicMock) -> None:
        provider = _make_provider()
        info = provider.model_info()
        self.assertEqual(info.name, "qwen-test")
        self.assertFalse(info.available)


# ── OllamaEmbeddingProvider — error translation ──────────────────────


class TestOllamaErrorTranslation(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = _make_provider()

    @patch("urllib.request.urlopen")
    def test_http_404_raises_model_not_found(self, mock_urlopen: MagicMock) -> None:
        err = urllib.error.HTTPError(
            "http://localhost:11434/api/embed", 404, "Not Found", {}, None
        )
        mock_urlopen.side_effect = err
        with self.assertRaises(ModelNotFoundError):
            self.provider.embed("hello")

    @patch("urllib.request.urlopen")
    def test_http_503_raises_provider_unavailable(
        self, mock_urlopen: MagicMock
    ) -> None:
        err = urllib.error.HTTPError(
            "http://localhost:11434/api/embed", 503, "Service Unavailable", {}, None
        )
        mock_urlopen.side_effect = err
        with self.assertRaises(ProviderUnavailableError):
            self.provider.embed("hello")

    @patch("urllib.request.urlopen")
    def test_http_400_raises_embedding_generation_error(
        self, mock_urlopen: MagicMock
    ) -> None:
        err = urllib.error.HTTPError(
            "http://localhost:11434/api/embed", 400, "Bad Request", {}, None
        )
        mock_urlopen.side_effect = err
        with self.assertRaises(EmbeddingGenerationError):
            self.provider.embed("hello")

    @patch("urllib.request.urlopen")
    def test_connection_error_raises_provider_unavailable(
        self, mock_urlopen: MagicMock
    ) -> None:
        err = urllib.error.URLError("Connection refused")
        mock_urlopen.side_effect = err
        with self.assertRaises(ProviderUnavailableError):
            self.provider.embed("hello")

    @patch("urllib.request.urlopen")
    def test_generic_exception_wrapped(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = RuntimeError("unexpected")
        with self.assertRaises(EmbeddingGenerationError):
            self.provider.embed("hello")


# ── EmbeddingService ─────────────────────────────────────────────────


class TestEmbeddingService(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = _make_provider()
        self.service = EmbeddingService(self.provider)

    @patch("urllib.request.urlopen")
    def test_embed_delegates_to_provider(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _mock_response(
            {"model": "qwen-test", "embeddings": [[0.1, 0.2]]}
        )
        req = EmbeddingRequest(text="hello")
        resp = self.service.embed(req)
        self.assertIsInstance(resp, EmbeddingResponse)
        self.assertEqual(resp.embedding, [0.1, 0.2])

    @patch("urllib.request.urlopen")
    def test_embed_batch_delegates_to_provider(
        self, mock_urlopen: MagicMock
    ) -> None:
        mock_urlopen.return_value = _mock_response(
            {"model": "qwen-test", "embeddings": [[0.1], [0.2]]}
        )
        req = EmbeddingBatchRequest(texts=["a", "b"])
        resp = self.service.embed_batch(req)
        self.assertIsInstance(resp, EmbeddingBatchResponse)
        self.assertEqual(len(resp.embeddings), 2)

    def test_embed_raises_on_empty_text(self) -> None:
        with self.assertRaises(ConfigurationError):
            self.service.embed(EmbeddingRequest(text=""))
        with self.assertRaises(ConfigurationError):
            self.service.embed(EmbeddingRequest(text="   "))

    def test_embed_batch_raises_on_empty_list(self) -> None:
        with self.assertRaises(ConfigurationError):
            self.service.embed_batch(EmbeddingBatchRequest(texts=[]))

    def test_embed_batch_raises_on_empty_text_in_list(self) -> None:
        with self.assertRaises(ConfigurationError):
            self.service.embed_batch(EmbeddingBatchRequest(texts=["a", ""]))


# ── Dependency Injection ─────────────────────────────────────────────


class TestEmbeddingDI(unittest.TestCase):
    def setUp(self) -> None:
        from backend.aicos.core.di import Container

        self.container = Container()
        self.settings = Settings(config_dir="missing-config")

    def test_register_embeddings_resolves_service(self) -> None:
        register_embeddings(self.container, self.settings)
        service = self.container.resolve(EmbeddingService)
        self.assertIsInstance(service, EmbeddingService)

    def test_register_embeddings_resolves_provider(self) -> None:
        register_embeddings(self.container, self.settings)
        provider = self.container.resolve(EmbeddingProvider)
        self.assertIsInstance(provider, OllamaEmbeddingProvider)

    def test_embeddings_are_singleton(self) -> None:
        register_embeddings(self.container, self.settings)
        s1 = self.container.resolve(EmbeddingService)
        s2 = self.container.resolve(EmbeddingService)
        self.assertIs(s1, s2)

    def test_provider_is_singleton(self) -> None:
        register_embeddings(self.container, self.settings)
        p1 = self.container.resolve(EmbeddingProvider)
        p2 = self.container.resolve(EmbeddingProvider)
        self.assertIs(p1, p2)


# ── Error translation via service ────────────────────────────────────


class TestServiceErrorTranslation(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = _make_provider()
        self.service = EmbeddingService(self.provider)

    @patch("urllib.request.urlopen")
    def test_service_forwards_model_not_found(self, mock_urlopen: MagicMock) -> None:
        err = urllib.error.HTTPError(
            "http://localhost:11434/api/embed", 404, "Not Found", {}, None
        )
        mock_urlopen.side_effect = err
        with self.assertRaises(ModelNotFoundError):
            self.service.embed(EmbeddingRequest(text="hello"))

    @patch("urllib.request.urlopen")
    def test_service_forwards_provider_unavailable(
        self, mock_urlopen: MagicMock
    ) -> None:
        err = urllib.error.URLError("Connection refused")
        mock_urlopen.side_effect = err
        with self.assertRaises(ProviderUnavailableError):
            self.service.embed(EmbeddingRequest(text="hello"))


# ── Configuration ────────────────────────────────────────────────────


class TestEmbeddingConfiguration(unittest.TestCase):
    def test_default_model_from_settings(self) -> None:
        settings = Settings(config_dir="missing-config")
        self.assertEqual(settings.ollama.embedding_model, "Qwen3-Embedding:0.6B")

    def test_custom_model_from_settings(self) -> None:
        settings = Settings(
            config_dir="missing-config",
            ollama={"embedding_model": "custom-model"},
        )
        self.assertEqual(settings.ollama.embedding_model, "custom-model")

    def test_ollama_disabled_raises_on_register(self) -> None:
        from backend.aicos.core.di import Container

        container = Container()
        settings = Settings(
            config_dir="missing-config",
            ollama={"embedding_model": "x", "enabled": False},
        )
        with self.assertRaises(ConfigurationError):
            register_embeddings(container, settings)


# ── Full-stack integration ───────────────────────────────────────────


class TestEmbeddingIntegration(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_embed_request_to_response_flow(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _mock_response(
            {"model": "Qwen3-Embedding:0.6B", "embeddings": [[0.1, 0.2, 0.3, 0.4]]}
        )
        provider = OllamaEmbeddingProvider(
            base_url="http://localhost:11434",
            model="Qwen3-Embedding:0.6B",
            timeout_seconds=30,
        )
        service = EmbeddingService(provider)
        resp = service.embed(EmbeddingRequest(text="integration test"))
        self.assertEqual(resp.dimensions, 4)
        self.assertEqual(resp.model, "Qwen3-Embedding:0.6B")
        self.assertEqual(len(resp.embedding), 4)


if __name__ == "__main__":
    unittest.main()
