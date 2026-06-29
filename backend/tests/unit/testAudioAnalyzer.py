# ─────────────────────────────────────────────────────────────────────────────
# backend/tests/unit/testAudioAnalyzer.py
# ─────────────────────────────────────────────────────────────────────────────

import pytest
from unittest.mock import patch, MagicMock

from src.schemas.analysisSchema import AudioMetrics

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

class TestAudioAnalyzerDemoMode:
    def test_filler_words_detected_in_text(self):
        with patch("src.modules.analysis.audioAnalyzer.settings", makeDemoSettings()):
            from src.modules.analysis.audioAnalyzer import analyzeAudio
            transcript = "Um, I literally built a scalable system, you know."
            result = analyzeAudio(None, transcript, 1)
            
            assert result.filler_word_count == 3
            assert set(result.filler_words_detected) == {"um", "literally", "you know"}
            assert result.demo_mode is True
            assert result.words_per_minute is None

    def test_filler_words_word_boundaries_respected(self):
        """Should not match 'like' inside 'alike' or 'um' in 'drum'."""
        with patch("src.modules.analysis.audioAnalyzer.settings", makeDemoSettings()):
            from src.modules.analysis.audioAnalyzer import analyzeAudio
            transcript = "The drum looks alike to a plum."
            result = analyzeAudio(None, transcript, 1)
            
            assert result.filler_word_count == 0
            assert len(result.filler_words_detected) == 0

    def test_all_numeric_fields_none_in_demo(self):
        with patch("src.modules.analysis.audioAnalyzer.settings", makeDemoSettings()):
            from src.modules.analysis.audioAnalyzer import analyzeAudio
            result = analyzeAudio(None, "Valid text.", 1)
            
            assert result.words_per_minute is None
            assert result.avg_pause_duration_seconds is None
            assert result.longest_pause_seconds is None
            assert result.voice_energy_level is None
            assert result.demo_mode is True


class TestAudioAnalyzerProductionMode:
    def test_production_metrics_calculated(self):
        mockLibrosa = MagicMock()
        mockLibrosa.load.return_value = ([0.1, 0.2, 0.3], 22050)
        mockLibrosa.get_duration.return_value = 2.0
        
        # mock RMS array: shape (1, frames)
        mockLibrosa.feature.rms.return_value = [[0.5, 0.6]]
        
        # mock interval gaps (1 gap of 22050 samples = 1 sec)
        mockLibrosa.effects.split.return_value = [[0, 1000], [23050, 24000]]
        
        mockNp = MagicMock()
        mockNp.mean.side_effect = lambda x: sum(x)/len(x) if isinstance(x, list) else x
        mockNp.max.return_value = 1.0
        
        with patch("src.modules.analysis.audioAnalyzer.settings", makeProductionSettings()):
            with patch.dict("sys.modules", {"librosa": mockLibrosa, "numpy": mockNp}):
                from src.modules.analysis.audioAnalyzer import analyzeAudio
                transcript = "This is ten words so we get five WPM right now."
                result = analyzeAudio(b"fake_audio_bytes", transcript, 1)
                
                assert result.demo_mode is False
                # 11 words / 2 seconds * 60 = 330 WPM
                assert result.words_per_minute == 330.0
                assert result.voice_energy_level == 0.55
                assert result.avg_pause_duration_seconds == 1.0
                assert result.longest_pause_seconds == 1.0
            
    def test_production_missing_audio_bytes_falls_back(self):
        with patch("src.modules.analysis.audioAnalyzer.settings", makeProductionSettings()):
            from src.modules.analysis.audioAnalyzer import analyzeAudio
            result = analyzeAudio(None, "No audio provided.", 1)
            assert result.demo_mode is True
            assert result.voice_energy_level is None

    def test_exception_in_production_falls_back(self):
        mockLibrosa = MagicMock()
        mockLibrosa.load.side_effect = Exception("Librosa crashed")
        mockNp = MagicMock()
        
        with patch("src.modules.analysis.audioAnalyzer.settings", makeProductionSettings()):
            with patch.dict("sys.modules", {"librosa": mockLibrosa, "numpy": mockNp}):
                from src.modules.analysis.audioAnalyzer import analyzeAudio
                result = analyzeAudio(b"audio", "Crashing test", 1)
                assert result.demo_mode is True
                assert result.voice_energy_level is None

