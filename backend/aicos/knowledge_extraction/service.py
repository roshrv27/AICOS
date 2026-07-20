from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from ..llm import ModelRouter
from ..logging import get_logger
from .enums import ContentType, ExtractionMode
from .exceptions import ExtractionError, UnsupportedContentError
from .models import (
    ExtractedAPI,
    ExtractedCodeSnippet,
    ExtractedConcept,
    ExtractedDependency,
    ExtractedExample,
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
from .registry import ExtractionRegistry
from .validation import validate_extraction_result

if TYPE_CHECKING:
    from ..llm.models import ModelRequest

_LLM_EXTRACTION_PROMPT = """You are a knowledge extraction system. Extract structured information from the following content.

Return a JSON object with these optional arrays:
- technologies: [{"id": str, "name": str, "summary": str, "category": str}]
- frameworks: [{"id": str, "name": str, "description": str, "version": str, "language": str}]
- models: [{"id": str, "name": str, "description": str, "provider": str, "version": str}]
- tools: [{"id": str, "name": str, "description": str, "category": str}]
- apis: [{"id": str, "name": str, "description": str, "endpoint": str, "version": str}]
- concepts: [{"id": str, "name": str, "description": str, "category": str}]
- versions: [{"id": str, "version": str}]
- releases: [{"id": str, "name": str, "version": str, "description": str}]
- dependencies: [{"id": str, "name": str, "version": str, "category": str}]
- examples: [{"id": str, "title": str, "description": str, "code": str, "language": str}]
- code_snippets: [{"id": str, "code": str, "language": str, "description": str}]
- references: [{"id": str, "source": str, "title": str, "url": str, "author": str}]

Use descriptive unique IDs prefixed by category (e.g., "tech_1", "fw_1", "model_1").
Only include entities that are clearly present in the content.
Return ONLY valid JSON, no other text.

Content to extract from:
"""


class KnowledgeExtractionService:
    def __init__(
        self,
        registry: ExtractionRegistry | None = None,
        model_router: ModelRouter | None = None,
    ) -> None:
        self._registry = registry or ExtractionRegistry()
        self._model_router = model_router
        self._logger = get_logger("knowledge_extraction.service")

    async def extract(self, request: ExtractionRequest) -> ExtractionResult:
        started_at = time.perf_counter()
        actual_mode = self._resolve_mode(request)

        if actual_mode == ExtractionMode.LLM_ASSISTED:
            result = await self._extract_llm(request)
        else:
            result = self._extract_rules(request)

        elapsed = (time.perf_counter() - started_at) * 1000
        stats = self.collect_statistics(result, elapsed, actual_mode.value)
        object.__setattr__(result, "statistics", stats)

        self._logger.info(
            "extraction completed",
            extra={
                "source_id": request.source_id,
                "source_type": request.source_type.value,
                "mode": actual_mode.value,
                "entities": stats.total_entities,
                "duration_ms": elapsed,
            },
        )

        return result

    async def extract_batch(
        self, requests: list[ExtractionRequest],
    ) -> list[ExtractionResult]:
        results: list[ExtractionResult] = []
        for req in requests:
            try:
                result = await self.extract(req)
                results.append(result)
            except ExtractionError as exc:
                self._logger.warning(
                    "batch extraction failed for request",
                    extra={"source_id": req.source_id, "error": str(exc)},
                )
                context = ExtractionContext(
                    source_type=req.source_type,
                    source_id=req.source_id,
                    source_name=req.source_name,
                    source_url=req.source_url,
                    content_type=req.content_type,
                    content_size=len(req.content),
                    extracted_at=datetime.now(timezone.utc),
                    extraction_mode="error",
                )
                empty = ExtractionResult(request=req, context=context, errors=[str(exc)])
                results.append(empty)
        return results

    def select_extractor(
        self, content_type: ContentType,
    ) -> Any | None:
        return self._registry.discover(content_type)

    def validate_result(self, result: ExtractionResult) -> None:
        validate_extraction_result(result)

    def collect_statistics(
        self, result: ExtractionResult, duration_ms: float, mode: str,
    ) -> ExtractionStatistics:
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
            extraction_duration_ms=duration_ms,
            extraction_mode=mode,
            errors=result.errors[:],
        )

    def _resolve_mode(self, request: ExtractionRequest) -> ExtractionMode:
        if request.mode:
            try:
                resolved = ExtractionMode(request.mode)
                if resolved == ExtractionMode.AUTO:
                    return self._auto_select_mode()
                if resolved == ExtractionMode.LLM_ASSISTED and self._model_router is None:
                    self._logger.warning(
                        "LLM mode requested but no model router available; "
                        "falling back to rule-based extraction"
                    )
                    return ExtractionMode.RULE_BASED
                return resolved
            except ValueError:
                pass
        return self._auto_select_mode()

    def _auto_select_mode(self) -> ExtractionMode:
        if self._model_router is not None:
            return ExtractionMode.LLM_ASSISTED
        return ExtractionMode.RULE_BASED

    def _extract_rules(self, request: ExtractionRequest) -> ExtractionResult:
        content_type = self._resolve_content_type(request)
        extractor = self._registry.discover(content_type)
        if extractor is None:
            raise UnsupportedContentError(
                f"no rule-based extractor available for content type: {content_type.value}"
            )
        return extractor.extract(request)

    async def _extract_llm(self, request: ExtractionRequest) -> ExtractionResult:
        from ..llm.models import ChatMessage, ModelRequest

        system_msg = ChatMessage(
            role="system",
            content="You are a precise knowledge extraction system. Return only valid JSON.",
        )
        user_msg = ChatMessage(role="user", content=_LLM_EXTRACTION_PROMPT + request.content)

        model_request = ModelRequest(
            messages=(system_msg, user_msg),
            structured_output=True,
            stream=False,
        )

        try:
            response = await self._model_router.generate(model_request)
        except Exception as exc:
            self._logger.exception("LLM extraction failed")
            raise ExtractionError(f"LLM extraction failed: {exc}") from exc

        if response.structured_output:
            parsed = response.structured_output
        else:
            parsed = self._parse_llm_response(response.content)

        context = self._build_context(request, ExtractionMode.LLM_ASSISTED.value)
        result = self._build_result(request, context, parsed)
        return result

    def _parse_llm_response(self, content: str) -> dict[str, Any]:
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            raise ExtractionError("LLM response is not valid JSON")

    def _build_context(
        self, request: ExtractionRequest, mode: str,
    ) -> ExtractionContext:
        return ExtractionContext(
            source_type=request.source_type,
            source_id=request.source_id,
            source_name=request.source_name,
            source_url=request.source_url,
            content_type=request.content_type,
            content_size=len(request.content),
            extracted_at=datetime.now(timezone.utc),
            extraction_mode=mode,
        )

    def _build_result(
        self, request: ExtractionRequest, context: ExtractionContext,
        parsed: dict[str, Any],
    ) -> ExtractionResult:
        extractors: dict[str, type] = {
            "technologies": ExtractedTechnology,
            "frameworks": ExtractedFramework,
            "models": ExtractedModel,
            "tools": ExtractedTool,
            "apis": ExtractedAPI,
            "concepts": ExtractedConcept,
            "versions": ExtractedVersion,
            "releases": ExtractedRelease,
            "dependencies": ExtractedDependency,
            "examples": ExtractedExample,
            "code_snippets": ExtractedCodeSnippet,
            "references": ExtractedReference,
        }

        kwargs: dict[str, list[Any]] = {
            "technologies": [],
            "frameworks": [],
            "models": [],
            "tools": [],
            "apis": [],
            "concepts": [],
            "versions": [],
            "releases": [],
            "dependencies": [],
            "examples": [],
            "code_snippets": [],
            "references": [],
            "errors": [],
        }

        for key, model_cls in extractors.items():
            items = parsed.get(key, [])
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        try:
                            obj = model_cls(
                                **{k: v for k, v in item.items() if k in model_cls.__dataclass_fields__}
                            )
                            kwargs[key].append(obj)
                        except (TypeError, ValueError) as exc:
                            kwargs["errors"].append(f"invalid {key} item: {exc}")

        return ExtractionResult(
            request=request,
            context=context,
            **kwargs,
        )

    def _resolve_content_type(self, request: ExtractionRequest) -> ContentType:
        if request.content_type:
            try:
                return ContentType(request.content_type)
            except ValueError:
                return ContentType.UNKNOWN
        return ContentType.UNKNOWN
