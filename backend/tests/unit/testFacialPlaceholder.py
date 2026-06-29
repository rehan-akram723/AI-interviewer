# ─────────────────────────────────────────────────────────────────────────────
# backend/tests/unit/testFacialPlaceholder.py
# ─────────────────────────────────────────────────────────────────────────────

import pytest
from unittest.mock import patch, MagicMock

from src.schemas.analysisSchema import FacialMetrics

def makeDemoSettings() -> MagicMock:
    m = MagicMock()
    m.is_demo = True
    m.is_production = False
    return m

def makeProductionSettings() -> MagicMock:
    m = MagicMock()
    m.is_demo = False
    m.is_production = True
    return m

class TestFacialPlaceholderDemoMode:
    def test_demo_mode_returns_nones(self):
        with patch("src.modules.analysis.facialPlaceholder.settings", makeDemoSettings()):
            from src.modules.analysis.facialPlaceholder import processFacialData
            result = processFacialData({"frames": [{"lookingAtCamera": True}]}, 1)
            
            assert result.demo_mode is True
            assert result.eye_contact_percentage is None
            assert result.avg_blink_rate_per_minute is None
            assert result.head_movement_score is None
            assert result.engagement_score is None

class TestFacialPlaceholderProductionMode:
    def test_production_missing_data_returns_demo_fallback(self):
        with patch("src.modules.analysis.facialPlaceholder.settings", makeProductionSettings()):
            from src.modules.analysis.facialPlaceholder import processFacialData
            result = processFacialData(None, 1)
            assert result.demo_mode is True
            assert result.eye_contact_percentage is None

    def test_production_empty_frames_returns_demo_fallback(self):
        with patch("src.modules.analysis.facialPlaceholder.settings", makeProductionSettings()):
            from src.modules.analysis.facialPlaceholder import processFacialData
            result = processFacialData({"frames": []}, 1)
            assert result.demo_mode is True
            assert result.eye_contact_percentage is None

    def test_production_computes_valid_metrics(self):
        with patch("src.modules.analysis.facialPlaceholder.settings", makeProductionSettings()):
            from src.modules.analysis.facialPlaceholder import processFacialData
            
            frames = [
                {"lookingAtCamera": True, "blinkDetected": False, "headJitter": 0.2},
                {"lookingAtCamera": True, "blinkDetected": True, "headJitter": 0.3},
                {"lookingAtCamera": False, "blinkDetected": False, "headJitter": 0.4},
                {"lookingAtCamera": True, "blinkDetected": False, "headJitter": 0.3},
            ]
            
            result = processFacialData({"frames": frames}, 1, durationSeconds=2.0)
            
            assert result.demo_mode is False
            # 3 out of 4 frames looking at camera = 75%
            assert result.eye_contact_percentage == 75.0
            
            # 1 blink in 2.0 seconds = 30 blinks per minute
            assert result.avg_blink_rate_per_minute == 30.0
            
            # jitter avg = 0.3 -> score = 3.0
            assert result.head_movement_score == 3.0
            
            # engagement = base (0.75 * 8 = 6.0) + movementBonus (2.0) = 8.0
            assert result.engagement_score == 8.0
