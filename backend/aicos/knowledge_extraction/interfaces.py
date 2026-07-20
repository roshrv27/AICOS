from __future__ import annotations

from typing import Protocol

from .enums import ContentType
from .models import ExtractionRequest, ExtractionResult


class ExtractorProtocol(Protocol):
    @property
    def name(self) -> str: ...

    def supports(self, content_type: ContentType) -> bool: ...

    def extract(self, request: ExtractionRequest) -> ExtractionResult: ...

    def validate(self, result: ExtractionResult) -> list[str]: ...

    def metadata(self) -> dict: ...
