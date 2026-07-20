"""Shared HTTP provider adapter utilities."""

from __future__ import annotations

import asyncio
import json
import time
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..exceptions import ProviderTimeoutError, ProviderUnavailableError
from ..health import ProviderHealth


class BaseHTTPProvider(ABC):
    """Minimal standard-library HTTP base for optional provider adapters."""

    name: str

    def __init__(self, name: str, base_url: str, timeout_seconds: float = 120.0) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    @abstractmethod
    async def generate(self, request: Any, model: Any) -> Any:
        """Execute a normalized generation request."""

    async def health_check(self) -> ProviderHealth:
        started_at = time.perf_counter()
        try:
            await self._health_request()
        except ProviderUnavailableError:
            return ProviderHealth(provider=self.name, available=False, failures=1)
        return ProviderHealth(
            provider=self.name,
            available=True,
            latency_ms=(time.perf_counter() - started_at) * 1000,
            last_successful_request=datetime.now(UTC),
        )

    @abstractmethod
    async def _health_request(self) -> None:
        """Perform the provider's lightweight availability probe."""

    async def _post_json(
        self,
        path: str,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(self._post_json_sync, path, payload, headers or {})

    async def _get_json(self, path: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
        return await asyncio.to_thread(self._get_json_sync, path, headers or {})

    def _post_json_sync(self, path: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        request = Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", **headers},
            method="POST",
        )
        return self._execute(request)

    def _get_json_sync(self, path: str, headers: dict[str, str]) -> dict[str, Any]:
        return self._execute(Request(f"{self.base_url}{path}", headers=headers, method="GET"))

    def _execute(self, request: Request) -> dict[str, Any]:
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310 - configured provider URL
                return json.loads(response.read().decode("utf-8"))
        except TimeoutError as error:
            raise ProviderTimeoutError(f"provider {self.name} timed out") from error
        except HTTPError as error:
            raise ProviderUnavailableError(f"provider {self.name} returned HTTP {error.code}") from error
        except (URLError, OSError, ValueError, json.JSONDecodeError) as error:
            raise ProviderUnavailableError(f"provider {self.name} is unavailable") from error
