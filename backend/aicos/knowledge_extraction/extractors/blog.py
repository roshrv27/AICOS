from __future__ import annotations

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

_KNOWN_TECHNOLOGIES = [
    "python", "javascript", "typescript", "rust", "go", "java", "c++",
    "machine learning", "deep learning", "neural network", "transformer",
    "gpt", "llm", "large language model", "rag", "agent", "autonomous agent",
    "pytorch", "tensorflow", "jax", "langchain", "llamaindex",
    "kubernetes", "docker", "aws", "gcp", "azure",
    "react", "nextjs", "node.js", "fastapi", "flask", "django",
    "vector database", "embeddings", "fine-tuning", "rlhf",
    "openai", "anthropic", "google", "meta", "microsoft",
]


class BlogExtractor(BaseExtractor):
    name = "blog"
    supported_content_types = {ContentType.BLOG_POST, ContentType.BLOG_ARTICLE, ContentType.GENERIC_TEXT}

    def _do_extract(self, request: ExtractionRequest) -> ExtractionResult:
        content = request.content
        context = self._make_context(request)

        refs = self._extract_urls(content, request.source_name)
        code_blocks = self._extract_code_blocks(content)
        techs = self._extract_technology_mentions(content, _KNOWN_TECHNOLOGIES)
        concepts = self._extract_concepts(content)
        versions = self._extract_versions(content)

        result = ExtractionResult(
            request=request,
            context=context,
            technologies=techs,
            concepts=concepts,
            versions=versions,
            references=refs,
            code_snippets=code_blocks,
        )
        object.__setattr__(result, "statistics", self._make_stats(result))
        return result

    def _extract_concepts(self, content: str) -> list[ExtractedConcept]:
        concepts: list[ExtractedConcept] = []
        seen: set[str] = set()

        for line in content.splitlines():
            line = line.strip()
            if line.startswith("## ") or line.startswith("### "):
                heading = line.lstrip("#").strip().lower()
                if heading and heading not in seen and len(heading) < 60:
                    seen.add(heading)
                    concepts.append(ExtractedConcept(
                        id=f"concept_{len(concepts)}",
                        name=line.lstrip("#").strip(),
                        category="blog",
                        confidence_score=0.5,
                    ))

            if line.startswith("- **") and "**" in line[4:]:
                bold_text = line.split("**")[1].strip()
                if bold_text.lower() not in seen and len(bold_text) < 60:
                    seen.add(bold_text.lower())
                    concepts.append(ExtractedConcept(
                        id=f"key_{len(concepts)}",
                        name=bold_text,
                        category="highlight",
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
