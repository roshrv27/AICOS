"""Structured logging utilities for AICOS components.

Use :func:`get_logger` in components and :func:`logging_context` at request or
job boundaries to attach correlation and duration metadata to every record.
"""

from __future__ import annotations

import json
import logging
import logging.config
from contextlib import contextmanager
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Any, Iterator

from .settings import Settings, SettingsLoader


LOGGER_NAMES = frozenset(
    {"supervisor", "agents", "event_bus", "database", "mcp", "llm", "api", "system"}
)
_correlation_id: ContextVar[str | None] = ContextVar("aicos_correlation_id", default=None)
_execution_duration_ms: ContextVar[float | None] = ContextVar(
    "aicos_execution_duration_ms", default=None
)
_execution_id: ContextVar[str | None] = ContextVar("aicos_execution_id", default=None)
_configuration_lock = RLock()
_configured = False


class LoggingContextFilter(logging.Filter):
    """Add context-variable values to every record handled by AICOS."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = _correlation_id.get()
        record.execution_duration_ms = _execution_duration_ms.get()
        record.execution_id = _execution_id.get()
        return True


class JsonFormatter(logging.Formatter):
    """Render AICOS log records as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "message": record.getMessage(),
        }
        if record.correlation_id is not None:
            payload["correlation_id"] = record.correlation_id
        if record.execution_duration_ms is not None:
            payload["execution_duration_ms"] = record.execution_duration_ms
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for attribute in ("event_id", "event_type", "source", "execution_id"):
            value = getattr(record, attribute, None)
            if value is not None:
                payload[attribute] = value
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(settings: Settings | None = None, *, force: bool = False) -> None:
    """Configure all AICOS loggers from validated application settings.

    Calling this function is normally unnecessary: :func:`get_logger` lazily
    configures logging on its first use. Pass ``force=True`` after a deliberate
    configuration reload.
    """

    global _configured
    with _configuration_lock:
        if _configured and not force:
            return

        settings = settings or SettingsLoader.load()
        logging_settings = settings.logging
        handlers: dict[str, dict[str, Any]] = {}
        handler_names: list[str] = []
        if logging_settings.console_enabled:
            handlers["console"] = {
                "class": "logging.StreamHandler",
                "level": logging_settings.level,
                "formatter": logging_settings.format,
                "filters": ["context"],
                "stream": "ext://sys.stderr",
            }
            handler_names.append("console")
        if logging_settings.file_enabled:
            log_file = Path(logging_settings.file_path)
            log_file.parent.mkdir(parents=True, exist_ok=True)
            handlers["rotating_file"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "level": logging_settings.level,
                "formatter": logging_settings.format,
                "filters": ["context"],
                "filename": str(log_file),
                "maxBytes": logging_settings.max_bytes,
                "backupCount": logging_settings.backup_count,
                "encoding": "utf-8",
            }
            handler_names.append("rotating_file")

        if not handler_names:
            handler_names.append("null")
            handlers["null"] = {"class": "logging.NullHandler"}

        logger_config = {
            "level": logging_settings.level,
            "handlers": handler_names,
            "propagate": False,
        }
        logging.config.dictConfig(
            {
                "version": 1,
                "disable_existing_loggers": False,
                "filters": {"context": {"()": LoggingContextFilter}},
                "formatters": {
                    "json": {"()": JsonFormatter},
                    "text": {
                        "format": (
                            "%(asctime)s %(levelname)s %(name)s %(module)s "
                            "correlation_id=%(correlation_id)s "
                            "execution_duration_ms=%(execution_duration_ms)s %(message)s"
                        )
                    },
                },
                "handlers": handlers,
                "loggers": {
                    "aicos": logger_config,
                    **{f"aicos.{name}": logger_config for name in LOGGER_NAMES},
                },
            }
        )
        _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a configured AICOS logger with one call.

    Named subsystem loggers include ``supervisor``, ``agents``, ``event_bus``,
    ``database``, ``mcp``, ``llm``, ``api``, and ``system``. Additional dotted
    names are supported and inherit the AICOS logger configuration.
    """

    configure_logging()
    qualified_name = name if name.startswith("aicos.") else f"aicos.{name}"
    return logging.getLogger(qualified_name)


@contextmanager
def logging_context(
    *,
    correlation_id: str | None = None,
    execution_id: str | None = None,
    execution_duration_ms: float | None = None,
) -> Iterator[None]:
    """Bind correlation and execution-duration metadata for nested log calls."""

    correlation_token: Token[str | None] = _correlation_id.set(
        _correlation_id.get() if correlation_id is None else correlation_id
    )
    duration_token: Token[float | None] = _execution_duration_ms.set(
        _execution_duration_ms.get() if execution_duration_ms is None else execution_duration_ms
    )
    execution_token: Token[str | None] = _execution_id.set(
        _execution_id.get() if execution_id is None else execution_id
    )
    try:
        yield
    finally:
        _correlation_id.reset(correlation_token)
        _execution_duration_ms.reset(duration_token)
        _execution_id.reset(execution_token)


def get_correlation_id() -> str | None:
    """Return the correlation ID bound to the current execution context."""

    return _correlation_id.get()


def get_execution_id() -> str | None:
    """Return the execution ID bound to the current execution context."""

    return _execution_id.get()


def shutdown_logging() -> None:
    """Close AICOS-owned handlers; primarily useful for graceful shutdown and tests."""

    global _configured
    with _configuration_lock:
        for logger_name in ("aicos", *(f"aicos.{name}" for name in LOGGER_NAMES)):
            logger = logging.getLogger(logger_name)
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)
                handler.close()
        _configured = False
