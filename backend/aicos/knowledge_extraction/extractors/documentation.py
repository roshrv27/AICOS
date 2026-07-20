from __future__ import annotations

from datetime import datetime, timezone

from ..enums import ContentType, ExtractionMode
from ..models import (
    ExtractedAPI,
    ExtractedConcept,
    ExtractedReference,
    ExtractedVersion,
    ExtractionRequest,
    ExtractionResult,
)
from .base import BaseExtractor


class DocumentationExtractor(BaseExtractor):
    name = "documentation"
    supported_content_types = {ContentType.DOCUMENTATION, ContentType.GENERIC_TEXT}

    def _do_extract(self, request: ExtractionRequest) -> ExtractionResult:
        content = request.content
        context = self._make_context(request)

        versions = self._extract_versions(content)
        refs = self._extract_urls(content, request.source_name)
        code_blocks = self._extract_code_blocks(content)

        apis: list[ExtractedAPI] = []
        concepts: list[ExtractedConcept] = []
        seen_concepts: set[str] = set()

        for line in content.splitlines():
            line = line.strip()

            if line.startswith("### ") or line.startswith("## "):
                heading = line.lstrip("#").strip().lower()
                if heading and heading not in seen_concepts:
                    seen_concepts.add(heading)
                    concepts.append(ExtractedConcept(
                        id=f"concept_{len(concepts)}",
                        name=line.lstrip("#").strip(),
                        category="documentation",
                        confidence_score=0.5,
                    ))

            lower = line.lower()
            if "api" in lower and ("endpoint" in lower or "route" in lower):
                parts = line.split(None, 1)
                name = parts[1] if len(parts) > 1 else line
                apis.append(ExtractedAPI(
                    id=f"api_{len(apis)}",
                    name=name.strip("`*\""),
                    endpoint=line.strip("`*\""),
                    url=request.source_url,
                    confidence_score=0.4,
                ))

        result = ExtractionResult(
            request=request,
            context=context,
            versions=versions,
            apis=apis,
            concepts=concepts,
            references=refs,
            code_snippets=code_blocks,
        )
        object.__setattr__(result, "statistics", self._make_stats(result))
        return result

    def _make_context(self, request: ExtractionRequest) -> ExtractionContext:
        from ..models import ExtractionContext
        return ExtractionContext(
            source_type=request.source_type,
            source_id=request.source_id,
            source_name=request.source_name,
            source_url=request.source_url,
            content_type=request.content_type,
            content_size=len(request.content),
            extracted_at=datetime.now(timezone.utc),
            extraction_mode=ExtractionMode.RULE_BASED.value,
        )
