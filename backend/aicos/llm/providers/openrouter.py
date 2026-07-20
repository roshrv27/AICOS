"""OpenRouter provider adapter using its OpenAI-compatible HTTP endpoint."""

from __future__ import annotations

import time

from ..models import ModelDefinition, ModelRequest
from ..response import ModelResponse, UsageMetadata
from .base import BaseHTTPProvider


class OpenRouterProvider(BaseHTTPProvider):
    """Optional OpenRouter adapter; API keys are supplied only from Settings."""

    def __init__(self, base_url: str, api_key: str, timeout_seconds: float = 120.0) -> None:
        super().__init__("openrouter", base_url, timeout_seconds)
        self._headers = {"Authorization": f"Bearer {api_key}"}

    async def generate(self, request: ModelRequest, model: ModelDefinition) -> ModelResponse:
        started_at = time.perf_counter()
        payload = {
            "model": model.model_name,
            "messages": [message.model_dump() for message in request.messages],
            "stream": False,
        }
        response = await self._post_json("/chat/completions", payload, self._headers)
        usage_payload = response.get("usage", {})
        usage = UsageMetadata(
            prompt_tokens=usage_payload.get("prompt_tokens"),
            completion_tokens=usage_payload.get("completion_tokens"),
            total_tokens=usage_payload.get("total_tokens"),
        )
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        return ModelResponse(
            provider=self.name,
            model_name=model.model_name,
            content=content or "",
            usage=usage,
            latency_ms=(time.perf_counter() - started_at) * 1000,
        )

    async def _health_request(self) -> None:
        await self._get_json("/models", self._headers)
