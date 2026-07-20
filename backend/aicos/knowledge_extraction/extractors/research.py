from __future__ import annotations

import re
from datetime import datetime, timezone

from ..enums import ContentType, ExtractionMode
from ..models import (
    ExtractedConcept,
    ExtractedFramework,
    ExtractedModel,
    ExtractedReference,
    ExtractedTechnology,
    ExtractionContext,
    ExtractionRequest,
    ExtractionResult,
)
from .base import BaseExtractor

_MODEL_PATTERN = re.compile(
    r"\b(GPT-4[o]?|GPT-4|GPT-3\.5|LLaMA\s*\d|Llama\s*\d|Claude\s*\d(?:\.\d)?"
    r"|Gemini\s*\d(?:\.\d)?|Mistral\s*\w+|Mixtral|DeepSeek[-\s]\w+"
    r"|Qwen\s*\d|Falcon[-\s]\w+|BLOOM|T5|BERT|RoBERTa|DeBERTa|ELECTRA"
    r"|Stable\s*Diffusion|DALL[-\s]E|CLIP|ViT|ResNet|EfficientNet"
    r"|YOLO|Whisper|Codex|Copilot)\b"
)

_CITATION_PATTERN = re.compile(r"\[(\d+)\]")
_ABSTRACT_HEADER = re.compile(r"^##?\s*(Abstract|Introduction)", re.IGNORECASE)

_KNOWN_FRAMEWORKS = [
    "pytorch", "tensorflow", "jax", "transformers", "accelerate",
    "diffusers", "langchain", "llamaindex", "ray", "dask",
    "spark", "flink", "kubeflow", "mlflow", "wandb",
]


class ResearchExtractor(BaseExtractor):
    name = "research"
    supported_content_types = {ContentType.RESEARCH_PAPER, ContentType.RESEARCH_ABSTRACT}

    def _do_extract(self, request: ExtractionRequest) -> ExtractionResult:
        content = request.content
        context = self._make_context(request)

        refs = self._extract_urls(content, request.source_name)
        models = self._extract_models(content)
        frameworks = self._extract_frameworks(content)
        concepts = self._extract_concepts(content)
        versions = self._extract_versions(content)
        citations = self._extract_citations(content, request.source_name)

        seen: dict[str, ExtractedReference] = {}
        for r in refs:
            seen[r.url or r.id] = r
        for r in citations:
            seen[r.id] = r
        all_refs = list(seen.values())

        result = ExtractionResult(
            request=request,
            context=context,
            technologies=[],
            models=models,
            frameworks=frameworks,
            concepts=concepts,
            versions=versions,
            references=all_refs,
        )
        object.__setattr__(result, "statistics", self._make_stats(result))
        return result

    def _extract_models(self, content: str) -> list[ExtractedModel]:
        models: list[ExtractedModel] = []
        seen: set[str] = set()

        for match in _MODEL_PATTERN.finditer(content):
            name = match.group(1).strip()
            key = name.lower().replace(" ", "")
            if key not in seen:
                seen.add(key)
                models.append(ExtractedModel(
                    id=f"model_{len(models)}",
                    name=name,
                    description=f"Model mentioned in research extraction",
                    url="",
                    confidence_score=0.6,
                ))

        return models

    def _extract_frameworks(self, content: str) -> list[ExtractedFramework]:
        frameworks: list[ExtractedFramework] = []
        seen: set[str] = set()
        content_lower = content.lower()

        for fw in _KNOWN_FRAMEWORKS:
            if fw.lower() in content_lower and fw.lower() not in seen:
                seen.add(fw.lower())
                frameworks.append(ExtractedFramework(
                    id=f"fw_{len(frameworks)}",
                    name=fw,
                    confidence_score=0.5,
                ))

        return frameworks

    def _extract_concepts(self, content: str) -> list[ExtractedConcept]:
        concepts: list[ExtractedConcept] = []
        seen: set[str] = set()

        in_abstract = False
        for line in content.splitlines():
            line = line.strip()
            if _ABSTRACT_HEADER.match(line):
                in_abstract = True
                continue
            if in_abstract and line.startswith("## "):
                in_abstract = False

            if in_abstract and line.endswith(".") and len(line) > 30:
                words = line.split()
                for word in words:
                    word_clean = word.strip(".,;:()[]")
                    if (word_clean[0].isupper() and len(word_clean) > 3
                            and word_clean.lower() not in seen
                            and not word_clean.startswith("http")):
                        seen.add(word_clean.lower())
                        if len(concepts) < 10:
                            concepts.append(ExtractedConcept(
                                id=f"concept_{len(concepts)}",
                                name=word_clean,
                                category="research",
                                confidence_score=0.3,
                            ))

        return concepts

    def _extract_citations(
        self, content: str, source_name: str,
    ) -> list[ExtractedReference]:
        citations: list[ExtractedReference] = []
        seen_nums: set[str] = set()

        for match in _CITATION_PATTERN.finditer(content):
            num = match.group(1)
            if num not in seen_nums:
                seen_nums.add(num)
                citations.append(ExtractedReference(
                    id=f"citation_{num}",
                    source=source_name or "research_paper",
                    title=f"Reference [{num}]",
                    confidence=0.7,
                ))

        return citations

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
