from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from ..enums import ContentType, ExtractionMode
from ..exceptions import UnsupportedContentError
from ..models import (
    ExtractedAPI,
    ExtractedCodeSnippet,
    ExtractedConcept,
    ExtractedFramework,
    ExtractedModel,
    ExtractedReference,
    ExtractedRelease,
    ExtractedTechnology,
    ExtractedTool,
    ExtractedVersion,
    ExtractionContext,
    ExtractionRequest,
    ExtractionResult,
    ExtractionStatistics,
)

_VERSION_PATTERN = re.compile(r"\b(\d+\.\d+\.\d+)\b")
_URL_PATTERN = re.compile(r"(https?://[^\s<>\"'\]\)]+)")
_CODE_BLOCK_PATTERN = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
_VERSION_HEADER_PATTERN = re.compile(r"##\s+\[?v?(\d+\.\d+\.\d+)\]?", re.IGNORECASE)


class BaseExtractor:
    name: str = "base"
    supported_content_types: set[ContentType] = set()

    def supports(self, content_type: ContentType) -> bool:
        return content_type in self.supported_content_types

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        if not self.supports(self._resolve_content_type(request)):
            raise UnsupportedContentError(
                f"extractor {self.name} does not support content type: {request.content_type}"
            )
        return self._do_extract(request)

    def _resolve_content_type(self, request: ExtractionRequest) -> ContentType:
        if request.content_type:
            try:
                return ContentType(request.content_type)
            except ValueError:
                return ContentType.UNKNOWN
        return ContentType.UNKNOWN

    def _do_extract(self, request: ExtractionRequest) -> ExtractionResult:
        raise NotImplementedError

    def validate(self, result: ExtractionResult) -> list[str]:
        return []

    def metadata(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "supported_types": [ct.value for ct in self.supported_content_types],
            "mode": "rule_based",
        }

    def _make_context(self, request: ExtractionRequest) -> ExtractionContext:
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

    def _make_stats(self, result: ExtractionResult) -> ExtractionStatistics:
        return ExtractionStatistics(
            total_entities=(
                len(result.technologies)
                + len(result.frameworks)
                + len(result.models)
                + len(result.tools)
                + len(result.apis)
                + len(result.concepts)
                + len(result.versions)
                + len(result.releases)
                + len(result.dependencies)
                + len(result.examples)
                + len(result.code_snippets)
                + len(result.references)
            ),
            technologies=len(result.technologies),
            frameworks=len(result.frameworks),
            models=len(result.models),
            tools=len(result.tools),
            apis=len(result.apis),
            concepts=len(result.concepts),
            versions=len(result.versions),
            releases=len(result.releases),
            dependencies=len(result.dependencies),
            examples=len(result.examples),
            code_snippets=len(result.code_snippets),
            references=len(result.references),
            extraction_mode=ExtractionMode.RULE_BASED.value,
        )

    def _extract_versions(self, content: str) -> list[ExtractedVersion]:
        seen: set[str] = set()
        versions: list[ExtractedVersion] = []
        for match in _VERSION_PATTERN.finditer(content):
            version = match.group(1)
            if version not in seen:
                seen.add(version)
                versions.append(ExtractedVersion(
                    id=f"ver_{len(versions)}",
                    version=version,
                ))
        return versions

    def _extract_urls(self, content: str, base_source: str) -> list[ExtractedReference]:
        seen: set[str] = set()
        refs: list[ExtractedReference] = []
        for match in _URL_PATTERN.finditer(content):
            url = match.group(1)
            if url not in seen:
                seen.add(url)
                refs.append(ExtractedReference(
                    id=f"ref_{len(refs)}",
                    source=base_source,
                    title=url.rsplit("/", 1)[-1] if "/" in url else url,
                    url=url,
                ))
        return refs

    def _extract_code_blocks(self, content: str) -> list[ExtractedCodeSnippet]:
        snippets: list[ExtractedCodeSnippet] = []
        for match in _CODE_BLOCK_PATTERN.finditer(content):
            lang = match.group(1) or ""
            code = match.group(2).strip()
            if code:
                snippets.append(ExtractedCodeSnippet(
                    id=f"code_{len(snippets)}",
                    code=code,
                    language=lang or "text",
                ))
        return snippets

    def _extract_technology_mentions(
        self, content: str, known_techs: list[str],
    ) -> list[ExtractedTechnology]:
        found: list[ExtractedTechnology] = []
        seen: set[str] = set()
        content_lower = content.lower()
        for i, tech in enumerate(known_techs):
            if tech.lower() in content_lower and tech.lower() not in seen:
                seen.add(tech.lower())
                found.append(ExtractedTechnology(
                    id=f"tech_{len(found)}",
                    name=tech,
                    category="llm",
                    importance=5,
                    confidence_score=0.4,
                ))
        return found
