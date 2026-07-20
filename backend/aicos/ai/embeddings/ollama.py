"""Ollama-backed implementation of the :class:`EmbeddingProvider` protocol.

Communicates with Ollama's ``/api/embed`` endpoint via standard-library HTTP.
No Ollama SDK or client object is exposed to callers.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

from ...logging import get_logger
from .exceptions import (
    ConfigurationError,
    EmbeddingError,
    EmbeddingGenerationError,
    ModelNotFoundError,
    ProviderUnavailableError,
)
from .models import EmbeddingBatchResponse, EmbeddingResponse, ModelInfo


class OllamaEmbeddingProvider:
    """Embedding provider backed by a local or remote Ollama instance.

    Reads ``base_url``, ``embedding_model``, and ``timeout_seconds`` from the
    ``OllamaConfig`` object passed at construction.
    """

    def __init__(self, base_url: str, model: str, timeout_seconds: int = 120) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout_seconds
        self._logger = get_logger("embeddings")

    # ── public API ──────────────────────────────────────────────────

    def embed(self, text: str) -> EmbeddingResponse:
        started_at = time.perf_counter()
        try:
            data = self._call_api(text)
        except EmbeddingError:
            raise
        except Exception as exc:
            raise EmbeddingGenerationError(str(exc)) from exc

        embeddings = data.get("embeddings", [])
        if not embeddings:
            raise EmbeddingGenerationError("provider returned an empty embedding list")

        emb = embeddings[0]
        dims = len(emb)
        self._logger.debug(
            "embedding generated",
            extra={
                "model": self._model,
                "dimensions": dims,
                "execution_duration_ms": (time.perf_counter() - started_at) * 1000,
            },
        )
        return EmbeddingResponse(embedding=list(emb), dimensions=dims, model=self._model)

    def embed_batch(self, texts: list[str]) -> EmbeddingBatchResponse:
        started_at = time.perf_counter()
        try:
            data = self._call_api(texts)
        except EmbeddingError:
            raise
        except Exception as exc:
            raise EmbeddingGenerationError(str(exc)) from exc

        embeddings = data.get("embeddings", [])
        if not embeddings:
            raise EmbeddingGenerationError("provider returned an empty embedding list")

        dims = len(embeddings[0]) if embeddings else 0
        result = [list(e) for e in embeddings]
        self._logger.debug(
            "batch embeddings generated",
            extra={
                "model": self._model,
                "count": len(result),
                "dimensions": dims,
                "execution_duration_ms": (time.perf_counter() - started_at) * 1000,
            },
        )
        return EmbeddingBatchResponse(embeddings=result, dimensions=dims, model=self._model)

    def health_check(self) -> bool:
        started_at = time.perf_counter()
        try:
            self._call_api("health")
            self._logger.debug(
                "health check passed",
                extra={
                    "model": self._model,
                    "execution_duration_ms": (time.perf_counter() - started_at) * 1000,
                },
            )
            return True
        except Exception:
            return False

    def model_info(self) -> ModelInfo:
        try:
            self._call_api("health")
            available = True
        except Exception:
            available = False
        return ModelInfo(name=self._model, dimensions=0, available=available)

    # ── internal ────────────────────────────────────────────────────

    def _call_api(self, input_data: str | list[str]) -> dict[str, Any]:
        if isinstance(input_data, str) and input_data == "health":
            req = urllib.request.Request(
                f"{self._base_url}/api/tags",
                method="GET",
                headers={"Accept": "application/json"},
            )
            try:
                with urllib.request.urlopen(req, timeout=self._timeout):
                    return {}
            except urllib.error.HTTPError as exc:
                raise ProviderUnavailableError(
                    f"provider returned HTTP {exc.code}"
                ) from exc
            except urllib.error.URLError as exc:
                raise ProviderUnavailableError(
                    f"provider unreachable: {exc.reason}"
                ) from exc

        payload = json.dumps({"model": self._model, "input": input_data}).encode("utf-8")
        req = urllib.request.Request(
            f"{self._base_url}/api/embed",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code == 404:
                raise ModelNotFoundError(
                    f"model '{self._model}' not found on provider"
                ) from exc
            if exc.code in (502, 503, 504):
                raise ProviderUnavailableError(
                    f"provider unavailable (HTTP {exc.code})"
                ) from exc
            raise EmbeddingGenerationError(
                f"provider returned HTTP {exc.code}: {body[:200]}"
            ) from exc
        except urllib.error.URLError as exc:
            raise ProviderUnavailableError(
                f"provider unreachable: {exc.reason}"
            ) from exc
