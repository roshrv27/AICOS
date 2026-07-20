from __future__ import annotations

import re
from datetime import datetime, timezone

from ..enums import ContentType, ExtractionMode
from ..models import (
    ExtractedDependency,
    ExtractedReference,
    ExtractedRelease,
    ExtractedTechnology,
    ExtractedVersion,
    ExtractionContext,
    ExtractionRequest,
    ExtractionResult,
)
from .base import BaseExtractor

_DEPENDENCY_PATTERN = re.compile(r"([a-zA-Z0-9_.-]+)\s*[=~><!]+\s*([\d.*]+)")
_REQUIREMENT_FILE_PATTERN = re.compile(r"^([a-zA-Z0-9_.-]+)(?:[=~><!]+[\d.*]+.*)?$", re.MULTILINE)
_DEPENDENCY_LINE_PATTERN = re.compile(r"(?:dep(?:endenc)?(?:ies|s)?|require(?:s|d)?|install)\s*:?\s*(.+)", re.IGNORECASE)
_RELEASE_NOTE_HEADER = re.compile(r"^##?\s+\[?v?(\d+\.\d+\.\d+)\]?", re.IGNORECASE)

_KNOWN_TECHNOLOGIES = [
    "python", "javascript", "typescript", "rust", "go", "java", "c++",
    "tensorflow", "pytorch", "jax", "transformers", "langchain",
    "llamaindex", "fastapi", "flask", "django", "react", "vue",
    "docker", "kubernetes", "helm", "postgresql", "redis",
    "opentelemetry", "prometheus", "grafana",
]


class GitHubExtractor(BaseExtractor):
    name = "github"
    supported_content_types = {ContentType.GITHUB_README, ContentType.GITHUB_RELEASE}

    def _do_extract(self, request: ExtractionRequest) -> ExtractionResult:
        content = request.content
        context = self._make_context(request)

        refs = self._extract_urls(content, request.source_name)
        code_blocks = self._extract_code_blocks(content)
        techs = self._extract_technology_mentions(content, _KNOWN_TECHNOLOGIES)
        versions = self._extract_versions(content)
        releases = self._extract_releases(content)
        dependencies = self._extract_dependencies(content)

        result = ExtractionResult(
            request=request,
            context=context,
            technologies=techs,
            versions=versions,
            releases=releases,
            dependencies=dependencies,
            references=refs,
            code_snippets=code_blocks,
        )
        object.__setattr__(result, "statistics", self._make_stats(result))
        return result

    def _extract_releases(self, content: str) -> list[ExtractedRelease]:
        releases: list[ExtractedRelease] = []
        lines = content.splitlines()
        current_header: str | None = None
        current_changes: list[str] = []

        for line in lines:
            match = _RELEASE_NOTE_HEADER.match(line.strip())
            if match:
                if current_header is not None:
                    releases.append(ExtractedRelease(
                        id=f"release_{len(releases)}",
                        name=current_header,
                        version=match.group(1),
                        changes=current_changes[:],
                    ))
                    current_changes = []
                current_header = line.strip().lstrip("#").strip()
            elif current_header is not None:
                stripped = line.strip().strip("-*").strip()
                if stripped:
                    current_changes.append(stripped)

        if current_header is not None:
            releases.append(ExtractedRelease(
                id=f"release_{len(releases)}",
                name=current_header,
                version=releases[-1].version if releases else "0.0.0",
                changes=current_changes[:],
            ))

        return releases

    def _extract_dependencies(self, content: str) -> list[ExtractedDependency]:
        deps: list[ExtractedDependency] = []
        seen: set[str] = set()

        matches = _DEPENDENCY_PATTERN.findall(content)
        for name, version in matches:
            name = name.strip()
            if name.lower() not in seen:
                seen.add(name.lower())
                deps.append(ExtractedDependency(
                    id=f"dep_{len(deps)}",
                    name=name,
                    version=version,
                    category="dependency",
                ))

        dep_line_match = _DEPENDENCY_LINE_PATTERN.search(content)
        if dep_line_match:
            dep_section = dep_line_match.group(1)
            comma_parts = re.split(r"[,;]\s*", dep_section)
            for part in comma_parts:
                part = part.strip()
                ver_match = re.match(r"([a-zA-Z0-9_.-]+)\s*[=~><!]+\s*([\d.*]+)", part)
                if ver_match:
                    name = ver_match.group(1).strip()
                    version = ver_match.group(2)
                    if name.lower() not in seen:
                        seen.add(name.lower())
                        deps.append(ExtractedDependency(
                            id=f"dep_{len(deps)}",
                            name=name,
                            version=version,
                            category="dependency",
                        ))
                elif re.match(r"^[a-zA-Z][a-zA-Z0-9_.-]*$", part):
                    name = part.strip()
                    if name.lower() not in seen:
                        seen.add(name.lower())
                        deps.append(ExtractedDependency(
                            id=f"dep_{len(deps)}",
                            name=name,
                            category="dependency",
                        ))

        for line in content.splitlines():
            line = line.strip()
            if re.match(r"^\s*#", line) or line.startswith("- ") or line.startswith("* "):
                continue
            if "==" in line or ">=" in line or "<=" in line:
                continue
            match = re.match(r"^([a-zA-Z][a-zA-Z0-9_.-]*)\s*$", line)
            if match and match.group(1).lower() not in seen:
                name = match.group(1)
                if len(name) > 1:
                    seen.add(name.lower())
                    deps.append(ExtractedDependency(
                        id=f"dep_{len(deps)}",
                        name=name,
                        category="dependency",
                    ))

        return deps

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
