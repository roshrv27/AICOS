"""Unit tests for the AICOS configuration system."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from backend.aicos.settings import Settings, SettingsLoader


class SettingsTests(unittest.TestCase):
    def tearDown(self) -> None:
        SettingsLoader.reset()

    def test_profile_yaml_is_loaded_and_cached(self) -> None:
        config_dir = Path(__file__).parents[1] / "config"
        with patch.dict(os.environ, {"AICOS_PROFILE": "development"}, clear=False):
            settings = SettingsLoader.load(config_dir=config_dir, force_reload=True)
            cached = SettingsLoader.load()

        self.assertIs(settings, cached)
        self.assertEqual(settings.profile, "development")
        self.assertTrue(settings.application.debug)
        self.assertEqual(settings.logging.level, "DEBUG")
        self.assertIsNone(settings.ollama.default_model)

    def test_environment_overrides_dotenv_and_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config_dir = root / "config"
            config_dir.mkdir()
            (config_dir / "base.yaml").write_text("logging:\n  level: INFO\n", encoding="utf-8")
            (root / ".env").write_text("AICOS_LOGGING__LEVEL=WARNING\n", encoding="utf-8")

            previous_directory = Path.cwd()
            try:
                os.chdir(root)
                with patch.dict(os.environ, {"AICOS_LOGGING__LEVEL": "ERROR"}, clear=False):
                    settings = SettingsLoader.load(config_dir=config_dir, force_reload=True)
            finally:
                os.chdir(previous_directory)

        self.assertEqual(settings.logging.level, "ERROR")

    def test_dotenv_selects_profile_before_yaml_is_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            config_dir = root / "config"
            config_dir.mkdir()
            (config_dir / "production.yaml").write_text(
                "application:\n  debug: false\nlogging:\n  level: ERROR\n",
                encoding="utf-8",
            )
            (root / ".env").write_text("AICOS_PROFILE=production\n", encoding="utf-8")

            previous_directory = Path.cwd()
            try:
                os.chdir(root)
                with patch.dict(os.environ, {}, clear=True):
                    settings = SettingsLoader.load(config_dir=config_dir, force_reload=True)
            finally:
                os.chdir(previous_directory)

        self.assertEqual(settings.profile, "production")
        self.assertEqual(settings.logging.level, "ERROR")

    def test_invalid_production_configuration_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            config_dir = Path(temporary_directory)
            (config_dir / "production.yaml").write_text("application:\n  debug: true\n", encoding="utf-8")

            with self.assertRaises(ValidationError):
                Settings(profile="production", config_dir=config_dir)

    def test_invalid_typed_value_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            config_dir = Path(temporary_directory)
            (config_dir / "base.yaml").write_text("ui:\n  port: 70000\n", encoding="utf-8")

            with self.assertRaises(ValidationError):
                Settings(config_dir=config_dir)


if __name__ == "__main__":
    unittest.main()
