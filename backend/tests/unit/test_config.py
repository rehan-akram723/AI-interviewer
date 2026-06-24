# ─────────────────────────────────────────────────────────────────────────────
# backend/tests/unit/test_config.py
#
# Unit tests for backend/src/core/config.py
#
# Tests verify:
#   1. Settings loads correctly from environment
#   2. is_demo / is_production properties work correctly
#   3. Default values are correct
#   4. Type constraints are enforced
# ─────────────────────────────────────────────────────────────────────────────

import pytest
import os
from unittest.mock import patch


class TestSettingsDefaults:
    """Verify that all default values match the manifest specification."""

    def test_default_app_mode_is_demo(self):
        """APP_MODE should default to 'demo' to prevent accidental API charges."""
        with patch.dict(os.environ, {}, clear=True):
            from importlib import reload
            import src.core.config as config_module
            reload(config_module)
            settings = config_module.Settings()
        assert settings.app_mode == "demo"

    def test_default_model_is_free_tier(self):
        """Default OpenRouter model must be a free-tier model."""
        with patch.dict(os.environ, {}, clear=True):
            from src.core.config import Settings
            s = Settings()
        assert ":free" in s.openrouter_model

    def test_default_max_followups(self):
        """Hard limit on follow-up chains must be 2 per manifest."""
        from src.core.config import Settings
        s = Settings()
        assert s.max_followups_per_question == 2

    def test_storage_paths_have_data_prefix(self):
        """All storage paths must point inside ./data/."""
        from src.core.config import Settings
        s = Settings()
        assert s.candidate_storage_path.startswith("./data/")
        assert s.session_storage_path.startswith("./data/")
        assert s.report_storage_path.startswith("./data/")


class TestIsDemoProperty:
    """Verify the is_demo / is_production gate property behaviour."""

    def test_is_demo_true_when_mode_is_demo(self):
        with patch.dict(os.environ, {"APP_MODE": "demo"}):
            from src.core.config import Settings
            s = Settings()
        assert s.is_demo is True
        assert s.is_production is False

    def test_is_demo_false_when_mode_is_production(self):
        with patch.dict(os.environ, {"APP_MODE": "production"}):
            from src.core.config import Settings
            s = Settings()
        assert s.is_demo is False
        assert s.is_production is True

    def test_is_demo_is_boolean(self):
        from src.core.config import Settings
        s = Settings()
        assert isinstance(s.is_demo, bool)
        assert isinstance(s.is_production, bool)


class TestSettingsValidation:
    """Verify pydantic validation rejects invalid values."""

    def test_invalid_app_mode_raises(self):
        """app_mode must be strictly 'demo' or 'production'."""
        from pydantic import ValidationError
        from src.core.config import Settings
        with pytest.raises((ValidationError, ValueError)):
            Settings(app_mode="staging")  # type: ignore

    def test_cors_origins_is_list(self):
        """CORS origins must be a list."""
        from src.core.config import Settings
        s = Settings()
        assert isinstance(s.cors_origins, list)
        assert len(s.cors_origins) > 0


class TestSettingsSingleton:
    """Verify the module-level singleton is usable."""

    def test_singleton_is_importable(self):
        """The `settings` singleton must be importable and valid."""
        from src.core.config import settings
        assert settings is not None
        assert settings.app_name == "AI Interviewer"

    def test_singleton_has_is_demo(self):
        """The singleton must expose the is_demo property."""
        from src.core.config import settings
        assert hasattr(settings, "is_demo")
        assert isinstance(settings.is_demo, bool)
