"""Unit tests for AICOS structured logging."""

from __future__ import annotations

import json
import logging
import tempfile
import unittest
from pathlib import Path

from backend.aicos.logging import LOGGER_NAMES, configure_logging, get_logger, logging_context, shutdown_logging
from backend.aicos.settings import Settings


class LoggingTests(unittest.TestCase):
    def tearDown(self) -> None:
        shutdown_logging()

    def _settings(self, log_path: Path) -> Settings:
        return Settings(
            config_dir=log_path.parent / "missing-config",
            logging={
                "level": "INFO",
                "format": "json",
                "console_enabled": False,
                "file_enabled": True,
                "file_path": log_path,
                "max_bytes": 1024,
                "backup_count": 2,
            },
        )

    def test_configures_required_subsystem_loggers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            configure_logging(self._settings(Path(temporary_directory) / "aicos.log"), force=True)
            for name in LOGGER_NAMES:
                logger = get_logger(name)
                self.assertFalse(logger.propagate)
                self.assertTrue(logger.handlers)

    def test_json_file_log_includes_context_and_exception(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            log_path = Path(temporary_directory) / "logs" / "aicos.log"
            configure_logging(self._settings(log_path), force=True)
            logger = get_logger("agents.worker")

            with logging_context(correlation_id="request-123", execution_duration_ms=12.5):
                logger.info("worker started")
                try:
                    raise ValueError("test failure")
                except ValueError:
                    logger.exception("worker failed")

            for handler in logger.handlers:
                handler.flush()
            records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(records[0]["level"], "INFO")
        self.assertEqual(records[0]["module"], "test_logging")
        self.assertEqual(records[0]["correlation_id"], "request-123")
        self.assertEqual(records[0]["execution_duration_ms"], 12.5)
        self.assertIn("timestamp", records[0])
        self.assertIn("ValueError: test failure", records[1]["exception"])

    def test_rotating_file_handler_is_configured(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            configure_logging(self._settings(Path(temporary_directory) / "aicos.log"), force=True)
            handlers = get_logger("system").handlers

        self.assertTrue(any(isinstance(handler, logging.handlers.RotatingFileHandler) for handler in handlers))


if __name__ == "__main__":
    unittest.main()
