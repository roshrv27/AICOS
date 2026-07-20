from __future__ import annotations

from enum import StrEnum


class ContentType(StrEnum):
    DOCUMENTATION = "documentation"
    GITHUB_README = "github_readme"
    GITHUB_RELEASE = "github_release"
    YOUTUBE_VIDEO = "youtube_video"
    YOUTUBE_DESCRIPTION = "youtube_description"
    RESEARCH_PAPER = "research_paper"
    RESEARCH_ABSTRACT = "research_abstract"
    BLOG_POST = "blog_post"
    BLOG_ARTICLE = "blog_article"
    GENERIC_TEXT = "generic_text"
    UNKNOWN = "unknown"


class ExtractionMode(StrEnum):
    RULE_BASED = "rule_based"
    LLM_ASSISTED = "llm_assisted"
    AUTO = "auto"
