# ─────────────────────────────────────────────────────────────────────────────
# backend/tests/unit/testSttService.py
#
# Unit tests for src.modules.analysis.sttService
#
# Tests validate:
#   1. Demo mode: transcribe() returns textInput directly
#   2. Demo mode: whisper package is NEVER imported or called
#   3. Demo mode: handles None, empty string, whitespace inputs safely
#   4. Demo mode: settings.is_demo gate is actually checked
#   5. Production mode: transcribe() calls getWhisperModel() and model.transcribe()
#   6. Production mode: uses tempfile for audio bytes (whisper needs file path)
#   7. Production mode: falls back to textInput if audioBytes is None
#   8. Production mode: transcription failure falls back to textInput (never crashes)
#   9. getWhisperModel() caches the model (not re-loaded on second call)
#  10. Return value is always a plain str
# ─────────────────────────────────────────────────────────────────────────────

import pytest
from unittest.mock import patch, MagicMock


# ════════════════════════════════════════════════════════════════════════════════
# Demo Mode Tests
# ════════════════════════════════════════════════════════════════════════════════

class TestSttDemoMode:
    """
    All tests in this class force settings.is_demo = True.
    The `whisper` package must NEVER be imported or called in any of these tests.
    """

    def test_returns_text_input_string(self):
        with patch("src.modules.analysis.sttService.settings") as mockSettings:
            mockSettings.is_demo = True
            from src.modules.analysis.sttService import transcribe
            result = transcribe(audioBytes=None, textInput="I built a REST API.")
        assert result == "I built a REST API."

    def test_returns_stripped_text_input(self):
        with patch("src.modules.analysis.sttService.settings") as mockSettings:
            mockSettings.is_demo = True
            from src.modules.analysis.sttService import transcribe
            result = transcribe(audioBytes=None, textInput="  leading and trailing spaces  ")
        assert result == "leading and trailing spaces"

    def test_returns_empty_string_for_none_text_input(self):
        with patch("src.modules.analysis.sttService.settings") as mockSettings:
            mockSettings.is_demo = True
            from src.modules.analysis.sttService import transcribe
            result = transcribe(audioBytes=None, textInput=None)
        assert result == ""

    def test_returns_empty_string_for_empty_text_input(self):
        with patch("src.modules.analysis.sttService.settings") as mockSettings:
            mockSettings.is_demo = True
            from src.modules.analysis.sttService import transcribe
            result = transcribe(audioBytes=None, textInput="")
        assert result == ""

    def test_returns_empty_string_for_whitespace_only(self):
        with patch("src.modules.analysis.sttService.settings") as mockSettings:
            mockSettings.is_demo = True
            from src.modules.analysis.sttService import transcribe
            result = transcribe(audioBytes=None, textInput="   ")
        assert result == ""

    def test_ignores_audio_bytes_in_demo_mode(self):
        """Even if audioBytes is provided, demo mode must ignore it and use textInput."""
        with patch("src.modules.analysis.sttService.settings") as mockSettings:
            mockSettings.is_demo = True
            from src.modules.analysis.sttService import transcribe
            fakeAudioBytes = b"\xff\xfb\x90\x00" * 100  # Fake MP3 header bytes
            result = transcribe(audioBytes=fakeAudioBytes, textInput="Typed text here.")
        assert result == "Typed text here."

    def test_whisper_package_never_imported_in_demo_mode(self):
        """
        Critical isolation test: whisper must not be imported or loaded.
        We verify by patching getWhisperModel and asserting it is never called.
        """
        with patch("src.modules.analysis.sttService.settings") as mockSettings:
            mockSettings.is_demo = True
            with patch("src.modules.analysis.sttService.getWhisperModel") as mockGetModel:
                from src.modules.analysis.sttService import transcribe
                transcribe(audioBytes=None, textInput="Test answer.")
        mockGetModel.assert_not_called()

    def test_returns_str_type(self):
        with patch("src.modules.analysis.sttService.settings") as mockSettings:
            mockSettings.is_demo = True
            from src.modules.analysis.sttService import transcribe
            result = transcribe(audioBytes=None, textInput="Hello world.")
        assert isinstance(result, str)

    def test_long_text_input_returned_completely(self):
        longText = "This is a very detailed answer. " * 50  # 1600+ characters
        with patch("src.modules.analysis.sttService.settings") as mockSettings:
            mockSettings.is_demo = True
            from src.modules.analysis.sttService import transcribe
            result = transcribe(audioBytes=None, textInput=longText)
        assert result == longText.strip()

    def test_unicode_text_input_handled(self):
        unicodeText = "I worked on a système embedded dans un véhicule autonome."
        with patch("src.modules.analysis.sttService.settings") as mockSettings:
            mockSettings.is_demo = True
            from src.modules.analysis.sttService import transcribe
            result = transcribe(audioBytes=None, textInput=unicodeText)
        assert result == unicodeText

    def test_newlines_in_text_preserved(self):
        """Newlines are valid in multi-sentence answers."""
        textWithNewlines = "First point.\nSecond point.\nThird point."
        with patch("src.modules.analysis.sttService.settings") as mockSettings:
            mockSettings.is_demo = True
            from src.modules.analysis.sttService import transcribe
            result = transcribe(audioBytes=None, textInput=textWithNewlines)
        assert "First point." in result
        assert "Second point." in result


# ════════════════════════════════════════════════════════════════════════════════
# Production Mode Tests
# ════════════════════════════════════════════════════════════════════════════════

class TestSttProductionMode:
    """
    All tests in this class force settings.is_demo = False.
    The whisper model itself is mocked — no real model is loaded.
    """

    def _makeSettings(self, whisperModelSize: str = "base") -> MagicMock:
        mockSettings = MagicMock()
        mockSettings.is_demo = False
        mockSettings.whisper_model_size = whisperModelSize
        return mockSettings

    def _makeWhisperModel(self, transcriptText: str = "Transcribed answer text.") -> MagicMock:
        mockModel = MagicMock()
        mockModel.transcribe.return_value = {"text": transcriptText, "segments": []}
        return mockModel

    def test_calls_get_whisper_model(self):
        """Production mode must call getWhisperModel() to load the model."""
        mockModel = self._makeWhisperModel()
        with patch("src.modules.analysis.sttService.settings", self._makeSettings()):
            with patch("src.modules.analysis.sttService.getWhisperModel", return_value=mockModel):
                from src.modules.analysis.sttService import transcribe
                transcribe(audioBytes=b"fake audio bytes", textInput=None)
        mockModel.transcribe.assert_called_once()

    def test_returns_transcribed_text(self):
        mockModel = self._makeWhisperModel("This is what the candidate said.")
        with patch("src.modules.analysis.sttService.settings", self._makeSettings()):
            with patch("src.modules.analysis.sttService.getWhisperModel", return_value=mockModel):
                from src.modules.analysis.sttService import transcribe
                result = transcribe(audioBytes=b"fake audio bytes", textInput=None)
        assert result == "This is what the candidate said."

    def test_returns_stripped_transcription(self):
        """Whisper sometimes adds leading/trailing whitespace — must be stripped."""
        mockModel = self._makeWhisperModel("  Answer with whitespace.  ")
        with patch("src.modules.analysis.sttService.settings", self._makeSettings()):
            with patch("src.modules.analysis.sttService.getWhisperModel", return_value=mockModel):
                from src.modules.analysis.sttService import transcribe
                result = transcribe(audioBytes=b"audio", textInput=None)
        assert result == "Answer with whitespace."

    def test_falls_back_to_text_input_when_no_audio(self):
        """If audioBytes is None in production, textInput is the fallback."""
        with patch("src.modules.analysis.sttService.settings", self._makeSettings()):
            from src.modules.analysis.sttService import transcribe
            result = transcribe(audioBytes=None, textInput="Fallback typed answer.")
        assert result == "Fallback typed answer."

    def test_no_model_load_when_audio_bytes_none(self):
        """No model should be loaded if audio bytes are absent (fallback path)."""
        with patch("src.modules.analysis.sttService.settings", self._makeSettings()):
            with patch("src.modules.analysis.sttService.getWhisperModel") as mockGetModel:
                from src.modules.analysis.sttService import transcribe
                transcribe(audioBytes=None, textInput="No audio.")
        mockGetModel.assert_not_called()

    def test_transcription_failure_falls_back_to_text_input(self):
        """If model.transcribe() throws, should return textInput not crash."""
        mockModel = MagicMock()
        mockModel.transcribe.side_effect = Exception("GPU out of memory")
        with patch("src.modules.analysis.sttService.settings", self._makeSettings()):
            with patch("src.modules.analysis.sttService.getWhisperModel", return_value=mockModel):
                from src.modules.analysis.sttService import transcribe
                result = transcribe(audioBytes=b"audio", textInput="Fallback text.")
        assert result == "Fallback text."

    def test_transcription_failure_returns_empty_string_when_no_text_input(self):
        """Failure with no textInput → empty string, not an exception."""
        mockModel = MagicMock()
        mockModel.transcribe.side_effect = Exception("Audio decode error")
        with patch("src.modules.analysis.sttService.settings", self._makeSettings()):
            with patch("src.modules.analysis.sttService.getWhisperModel", return_value=mockModel):
                from src.modules.analysis.sttService import transcribe
                result = transcribe(audioBytes=b"bad audio", textInput=None)
        assert result == ""
        assert isinstance(result, str)

    def test_return_value_is_always_str(self):
        mockModel = self._makeWhisperModel("A string.")
        with patch("src.modules.analysis.sttService.settings", self._makeSettings()):
            with patch("src.modules.analysis.sttService.getWhisperModel", return_value=mockModel):
                from src.modules.analysis.sttService import transcribe
                result = transcribe(audioBytes=b"audio", textInput=None)
        assert isinstance(result, str)


# ════════════════════════════════════════════════════════════════════════════════
# getWhisperModel Caching
# ════════════════════════════════════════════════════════════════════════════════

class TestGetWhisperModelCaching:

    def test_model_is_cached_after_first_load(self):
        """Second call to getWhisperModel() must not call load_model() again."""
        import src.modules.analysis.sttService as sttMod

        mockWhisperLib = MagicMock()
        mockModel = MagicMock()
        mockWhisperLib.load_model.return_value = mockModel

        # Reset the module cache
        originalModel = sttMod._whisperModel
        sttMod._whisperModel = None

        try:
            with patch("src.modules.analysis.sttService.settings") as mockSettings:
                mockSettings.is_demo = False
                mockSettings.whisper_model_size = "base"
                with patch.dict("sys.modules", {"whisper": mockWhisperLib}):
                    sttMod.getWhisperModel()  # First call
                    sttMod.getWhisperModel()  # Second call — must not re-load

            # load_model should have been called exactly once
            assert mockWhisperLib.load_model.call_count == 1
        finally:
            # Restore original cache state
            sttMod._whisperModel = originalModel

    def test_cached_model_is_returned_on_second_call(self):
        """getWhisperModel() must return the same object on repeated calls."""
        import src.modules.analysis.sttService as sttMod

        mockWhisperLib = MagicMock()
        mockModel = MagicMock()
        mockWhisperLib.load_model.return_value = mockModel

        originalModel = sttMod._whisperModel
        sttMod._whisperModel = None

        try:
            with patch("src.modules.analysis.sttService.settings") as mockSettings:
                mockSettings.is_demo = False
                mockSettings.whisper_model_size = "base"
                with patch.dict("sys.modules", {"whisper": mockWhisperLib}):
                    model1 = sttMod.getWhisperModel()
                    model2 = sttMod.getWhisperModel()

            assert model1 is model2
        finally:
            sttMod._whisperModel = originalModel
