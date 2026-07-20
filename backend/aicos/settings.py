"""Typed, profile-aware configuration for AICOS.

Precedence, from highest to lowest, is: explicit constructor values,
environment variables, `.env`, then `config/base.yaml` and the active profile
file. Nested environment variables use a double underscore, for example
`AICOS_LOGGING__LEVEL=DEBUG`.
"""

from __future__ import annotations

import os
from pathlib import Path
from threading import RLock
from typing import Any, Literal

import yaml
from dotenv import dotenv_values
from pydantic import AnyHttpUrl, BaseModel, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


Profile = Literal["development", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class ApplicationConfig(BaseModel):
    """Application-wide settings."""

    model_config = {"extra": "forbid"}

    name: str = "AICOS"
    debug: bool = False
    data_directory: Path = Path("data")


class LoggingConfig(BaseModel):
    """Structured logging settings."""

    model_config = {"extra": "forbid"}

    level: LogLevel = "INFO"
    format: Literal["json", "text"] = "json"
    console_enabled: bool = True
    file_enabled: bool = True
    file_path: Path = Path("data/logs/aicos.log")
    max_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    backup_count: int = Field(default=5, ge=1)


class SQLiteConfig(BaseModel):
    """Local SQLite storage settings."""

    model_config = {"extra": "forbid"}

    path: Path = Path("data/aicos.db")
    timeout_seconds: int = Field(default=30, gt=0)
    wal_enabled: bool = True


class ChromaDBConfig(BaseModel):
    """ChromaDB connection and persistence settings."""

    model_config = {"extra": "forbid"}

    host: str = "localhost"
    port: int = Field(default=8000, ge=1, le=65535)
    persist_directory: Path = Path("data/chroma")
    use_http: bool = False


class OllamaConfig(BaseModel):
    """Configuration for an optional local Ollama provider."""

    model_config = {"extra": "forbid"}

    enabled: bool = True
    base_url: AnyHttpUrl = "http://localhost:11434"
    timeout_seconds: int = Field(default=120, gt=0)
    default_model: str | None = None


class OpenRouterConfig(BaseModel):
    """Configuration for an optional OpenRouter provider."""

    model_config = {"extra": "forbid"}

    enabled: bool = False
    base_url: AnyHttpUrl = "https://openrouter.ai/api/v1"
    api_key: SecretStr | None = None
    timeout_seconds: int = Field(default=120, gt=0)
    default_model: str | None = None


class MCPConfig(BaseModel):
    """Model Context Protocol integration settings."""

    model_config = {"extra": "forbid"}

    enabled: bool = True
    configuration_directory: Path = Path("config/mcp")
    request_timeout_seconds: int = Field(default=30, gt=0)


class SchedulerConfig(BaseModel):
    """Scheduler service settings."""

    model_config = {"extra": "forbid"}

    enabled: bool = True
    timezone: str = "UTC"
    max_concurrent_jobs: int = Field(default=4, ge=1)


class UIConfig(BaseModel):
    """User-interface service settings."""

    model_config = {"extra": "forbid"}

    host: str = "127.0.0.1"
    port: int = Field(default=3000, ge=1, le=65535)
    allow_remote_access: bool = False


class YamlSettingsSource(PydanticBaseSettingsSource):
    """Load base and profile YAML files from the configured directory."""

    def __init__(self, settings_cls: type[BaseSettings], config_dir: Path, profile: str) -> None:
        super().__init__(settings_cls)
        self.config_dir = config_dir
        self.profile = profile

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for filename in ("base.yaml", f"{self.profile}.yaml"):
            path = self.config_dir / filename
            if not path.exists():
                continue
            with path.open("r", encoding="utf-8") as file:
                document = yaml.safe_load(file) or {}
            if not isinstance(document, dict):
                raise ValueError(f"Configuration file {path} must contain a mapping at its root")
            values = _deep_merge(values, document)
        return values


class Settings(BaseSettings):
    """Validated AICOS configuration.

    Profile-aware YAML values are loaded from `config/base.yaml` and either
    `config/development.yaml` or `config/production.yaml`.
    """

    model_config = SettingsConfigDict(
        env_prefix="AICOS_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="forbid",
        validate_default=True,
    )

    profile: Profile = "development"
    config_dir: Path = Field(default=Path("config"), exclude=True)
    application: ApplicationConfig = Field(default_factory=ApplicationConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    sqlite: SQLiteConfig = Field(default_factory=SQLiteConfig)
    chromadb: ChromaDBConfig = Field(default_factory=ChromaDBConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    openrouter: OpenRouterConfig = Field(default_factory=OpenRouterConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    ui: UIConfig = Field(default_factory=UIConfig)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        init_values = getattr(init_settings, "init_kwargs", {})
        dotenv_values_map = dotenv_values(".env")
        config_dir = Path(
            init_values.get(
                "config_dir",
                os.getenv("AICOS_CONFIG_DIR", dotenv_values_map.get("AICOS_CONFIG_DIR", "config")),
            )
        )
        profile = init_values.get(
            "profile",
            os.getenv("AICOS_PROFILE", dotenv_values_map.get("AICOS_PROFILE", "development")),
        )
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlSettingsSource(settings_cls, config_dir, profile),
            file_secret_settings,
        )

    @model_validator(mode="after")
    def validate_profile_requirements(self) -> "Settings":
        if self.profile == "production" and self.application.debug:
            raise ValueError("application.debug must be false in the production profile")
        if self.ui.allow_remote_access and self.ui.host in {"127.0.0.1", "localhost"}:
            raise ValueError("ui.host must not be loopback when remote access is enabled")
        return self


class SettingsLoader:
    """Thread-safe singleton loader for validated settings."""

    _instance: Settings | None = None
    _lock = RLock()

    @classmethod
    def load(cls, *, config_dir: str | Path | None = None, force_reload: bool = False) -> Settings:
        with cls._lock:
            if cls._instance is None or force_reload:
                values: dict[str, Any] = {}
                if config_dir is not None:
                    values["config_dir"] = Path(config_dir)
                cls._instance = Settings(**values)
            return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Clear the cached settings instance; primarily useful for tests."""

        with cls._lock:
            cls._instance = None


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Merge nested mappings without mutating either input."""

    result = base.copy()
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
