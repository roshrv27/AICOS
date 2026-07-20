"""Ollama provider adapter using its documented local HTTP API."""

from __future__ import annotations

import time

from ..models import ModelDefinition, ModelRequest
from ..response import ModelResponse, UsageMetadata
from .base import BaseHTTPProvider


class OllamaProvider(BaseHTTPProvider):
    """Optional local Ollama adapter; callers interact only through ModelRouter."""

    def __init__(self, base_url: str, timeout_seconds: float = 120.0) -> None:
        super().__init__("ollama", base_url, timeout_seconds)

    async def generate(self, request: ModelRequest, model: ModelDefinition) -> ModelResponse:
        started_at = time.perf_counter()
        payload = {
            "model": model.model_name,
            "messages": [message.model_dump() for message in request.messages],
            "stream": False,
        }
        response = await self._post_json("/api/chat", payload)
        usage = UsageMetadata(
            prompt_tokens=response.get("prompt_eval_count"),
            completion_tokens=response.get("eval_count"),
        )
        return ModelResponse(
            provider=self.name,
            model_name=model.model_name,
            content=response.get("message", {}).get("content", ""),
            usage=usage,
            latency_ms=(time.perf_counter() - started_at) * 1000,
        )

    async def _health_request(self) -> None:
        await self._get_json("/api/tags")
