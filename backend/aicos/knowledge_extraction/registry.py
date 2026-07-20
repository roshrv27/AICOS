from __future__ import annotations

from typing import TYPE_CHECKING

from ..logging import get_logger
from .enums import ContentType
from .exceptions import ExtractorNotFoundError

if TYPE_CHECKING:
    from .interfaces import ExtractorProtocol


class ExtractionRegistry:
    def __init__(self) -> None:
        self._extractors: dict[str, ExtractorProtocol] = {}
        self._content_map: dict[ContentType, list[str]] = {}
        self._logger = get_logger("knowledge_extraction.registry")

    def register(self, extractor: ExtractorProtocol) -> None:
        name = extractor.name
        if name in self._extractors:
            self._logger.warning(
                "extractor already registered; skipping",
                extra={"extractor": name},
            )
            return
        self._extractors[name] = extractor
        for content_type in ContentType:
            if extractor.supports(content_type):
                self._content_map.setdefault(content_type, []).append(name)
        self._logger.info(
            "extractor registered",
            extra={"extractor": name},
        )

    def lookup(self, name: str) -> ExtractorProtocol:
        extractor = self._extractors.get(name)
        if extractor is None:
            raise ExtractorNotFoundError(f"no extractor registered with name: {name!r}")
        return extractor

    def lookup_by_source(self, content_type: ContentType) -> list[ExtractorProtocol]:
        names = self._content_map.get(content_type, [])
        return [self._extractors[name] for name in names]

    def discover(self, content_type: ContentType) -> ExtractorProtocol | None:
        names = self._content_map.get(content_type, [])
        if not names:
            return None
        return self._extractors[names[0]]

    @property
    def registered(self) -> list[str]:
        return list(self._extractors.keys())
