from __future__ import annotations

import re
from datetime import datetime, timezone

from ..enums import ContentType, ExtractionMode
from ..models import (
    ExtractedConcept,
    ExtractedReference,
    ExtractedTechnology,
    ExtractionContext,
    ExtractionRequest,
    ExtractionResult,
)
from .base import BaseExtractor

_HASHTAG_PATTERN = re.compile(r"#(\w+)")
_CHANNEL_TECH_PATTERN = re.compile(r"@(\w+)")
_TIMESTAMP_PATTERN = re.compile(r"\b(\d{1,2}:\d{2}(?::\d{2})?)\b")

_KNOWN_TECHNOLOGIES = [
    "python", "javascript", "typescript", "rust", "go", "java",
    "machine learning", "deep learning", "neural network", "transformer",
    "gpt", "llm", "rag", "agent", "langchain", "pytorch", "tensorflow",
    "jax", "kubernetes", "docker", "aws", "gcp", "azure",
    "react", "nextjs", "node", "fastapi", "llamaindex",
]


class YouTubeExtractor(BaseExtractor):
    name = "youtube"
    supported_content_types = {ContentType.YOUTUBE_VIDEO, ContentType.YOUTUBE_DESCRIPTION}

    def _do_extract(self, request: ExtractionRequest) -> ExtractionResult:
        content = request.content
        context = self._make_context(request)

        refs = self._extract_urls(content, request.source_name)
        techs = self._extract_technology_mentions(content, _KNOWN_TECHNOLOGIES)
        concepts = self._extract_concepts(content)
        versions = self._extract_versions(content)

        for ref in refs:
            parts = ref.url.split("/")
            if len(parts) >= 2:
                ref_id = parts[-1]
                if ref_id.startswith("watch") and len(parts) >= 3:
                    ref_id = parts[-2]
                object.__setattr__(ref, "id", f"yt_ref_{ref_id[:16]}")

        result = ExtractionResult(
            request=request,
            context=context,
            technologies=techs,
            concepts=concepts,
            versions=versions,
            references=refs,
        )
        object.__setattr__(result, "statistics", self._make_stats(result))
        return result

    def _extract_concepts(self, content: str) -> list[ExtractedConcept]:
        concepts: list[ExtractedConcept] = []
        seen: set[str] = set()

        for match in _HASHTAG_PATTERN.finditer(content):
            tag = match.group(1).lower()
            if tag not in seen:
                seen.add(tag)
                concepts.append(ExtractedConcept(
                    id=f"hashtag_{len(concepts)}",
                    name=match.group(1),
                    category="tag",
                    confidence_score=0.6,
                ))

        lines = content.splitlines()
        for line in lines[:5]:
            line = line.strip()
            if line and ":" in line and len(line) < 100:
                parts = line.split(":", 1)
                key = parts[0].strip().lower()
                if key in {"topic", "about", "description", "overview"}:
                    val = parts[1].strip()
                    if val and val.lower() not in seen:
                        seen.add(val.lower())
                        concepts.append(ExtractedConcept(
                            id=f"topic_{len(concepts)}",
                            name=val,
                            category="topic",
                            confidence_score=0.4,
                        ))

        return concepts

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
