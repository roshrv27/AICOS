from __future__ import annotations

from enum import StrEnum


class SourceType(StrEnum):
    DOCUMENTATION = "documentation"
    GITHUB = "github"
    YOUTUBE = "youtube"
    RESEARCH = "research"
    BLOG = "blog"
    NEWS = "news"
    SOCIAL = "social"
    PODCAST = "podcast"
    CONFERENCE = "conference"
    BENCHMARK = "benchmark"
    PACKAGE_REGISTRY = "package_registry"
    HARDWARE_VENDOR = "hardware_vendor"


class Category(StrEnum):
    LLM = "llm"
    AGENTS = "agents"
    RAG = "rag"
    VISION = "vision"
    SPEECH = "speech"
    MULTIMODAL = "multimodal"
    EDGE_AI = "edge_ai"
    CLOUD_AI = "cloud_ai"
    FRAMEWORK = "framework"
    TOOLING = "tooling"
    HARDWARE = "hardware"
    SECURITY = "security"
    BENCHMARK = "benchmark"


class Capability(StrEnum):
    DOCUMENTATION = "documentation"
    RELEASES = "releases"
    BLOG_POSTS = "blog_posts"
    VIDEOS = "videos"
    REPOSITORIES = "repositories"
    RESEARCH_PAPERS = "research_papers"
    SOCIAL_POSTS = "social_posts"
    BENCHMARKS = "benchmarks"
    PACKAGES = "packages"
    API_REFERENCE = "api_reference"
    CHANGELOGS = "changelogs"


class AuthenticationType(StrEnum):
    NONE = "none"
    API_KEY = "api_key"
    OAUTH = "oauth"
    BEARER = "bearer"


class RefreshFrequency(StrEnum):
    REALTIME = "realtime"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
