# ─────────────────────────────────────────────────────────────────────────────
# backend/tests/unit/testTtsService.py
#
# Unit tests for src.modules.analysis.ttsService
#
# Tests validate:
#   1. Demo mode: speak() returns {"mode": "text", "content": text, "audioUrl": None}
#   2. Demo mode: no HTTP call, no ElevenLabs client created
#   3. Demo mode: handles empty string, None input safely
#   4. Demo mode: content field always equals the input text
#   5. Production mode: calls ElevenLabs endpoint
#   6. Production mode: returns mode="audio" with audioBytes on success
#   7. Production mode: HTTP failure falls back to mode="text" (graceful degradation)
#   8. Production mode: empty text returns safe response without HTTP call
#   9. getTtsClient() caches the client (not re-created on second call)
#  10. Return dict always has all 4 required keys
# ─────────────────────────────────────────────────────────────────────────────

import pytest
from unittest.mock import patch, MagicMock


# ── Helper to build a mock settings object ────────────────────────────────────

def makeDemoSettings() -> MagicMock:
    m = MagicMock()
    m.is_demo = True
    m.elevenlabs_api_key = ""
    m.elevenlabs_voice_id = ""
    return m


def makeProductionSettings(
    apiKey: str = "test-xi-key-abc123",
    voiceId: str = "voice-id-xyz",
) -> MagicMock:
    m = MagicMock()
    m.is_demo = False
    m.elevenlabs_api_key = apiKey
    m.elevenlabs_voice_id = voiceId
    return m


# ── Required output keys ───────────────────────────────────────────────────────
_REQUIRED_KEYS = {"mode", "content", "audioUrl", "audioBytes"}


# ════════════════════════════════════════════════════════════════════════════════
# Demo Mode Tests
# ════════════════════════════════════════════════════════════════════════════════

class TestTtsDemoMode:

    def test_returns_dict(self):
        with patch("src.modules.analysis.ttsService.settings", makeDemoSettings()):
            from src.modules.analysis.ttsService import speak
            result = speak("Hello, candidate.")
        assert isinstance(result, dict)

    def test_mode_is_text(self):
        with patch("src.modules.analysis.ttsService.settings", makeDemoSettings()):
            from src.modules.analysis.ttsService import speak
            result = speak("Tell me about yourself.")
        assert result["mode"] == "text"

    def test_content_matches_input_text(self):
        inputText = "Walk me through your most complex project."
        with patch("src.modules.analysis.ttsService.settings", makeDemoSettings()):
            from src.modules.analysis.ttsService import speak
            result = speak(inputText)
        assert result["content"] == inputText

    def test_audio_url_is_none(self):
        with patch("src.modules.analysis.ttsService.settings", makeDemoSettings()):
            from src.modules.analysis.ttsService import speak
            result = speak("Some question text.")
        assert result["audioUrl"] is None

    def test_audio_bytes_is_none(self):
        with patch("src.modules.analysis.ttsService.settings", makeDemoSettings()):
            from src.modules.analysis.ttsService import speak
            result = speak("Some question text.")
        assert result["audioBytes"] is None

    def test_all_required_keys_present(self):
        with patch("src.modules.analysis.ttsService.settings", makeDemoSettings()):
            from src.modules.analysis.ttsService import speak
            result = speak("Question text.")
        missing = _REQUIRED_KEYS - set(result.keys())
        assert not missing, f"Missing keys in demo response: {missing}"

    def test_no_http_call_in_demo_mode(self):
        """getTtsClient must never be called in demo mode."""
        with patch("src.modules.analysis.ttsService.settings", makeDemoSettings()):
            with patch("src.modules.analysis.ttsService.getTtsClient") as mockClient:
                from src.modules.analysis.ttsService import speak
                speak("This is a question.")
        mockClient.assert_not_called()

    def test_handles_empty_string_input(self):
        with patch("src.modules.analysis.ttsService.settings", makeDemoSettings()):
            from src.modules.analysis.ttsService import speak
            result = speak("")
        assert result["mode"] == "text"
        assert result["content"] == ""
        assert result["audioUrl"] is None

    def test_handles_none_input_gracefully(self):
        """speak(None) should not crash — treat as empty string."""
        with patch("src.modules.analysis.ttsService.settings", makeDemoSettings()):
            from src.modules.analysis.ttsService import speak
            result = speak(None)
        assert isinstance(result, dict)
        assert result["mode"] == "text"
        assert result["audioUrl"] is None

    def test_unicode_text_preserved_in_content(self):
        unicodeText = "Décrivez votre projet le plus complexe."
        with patch("src.modules.analysis.ttsService.settings", makeDemoSettings()):
            from src.modules.analysis.ttsService import speak
            result = speak(unicodeText)
        assert result["content"] == unicodeText

    def test_long_text_preserved_completely(self):
        longText = "This is a very long question that goes on and on. " * 20
        with patch("src.modules.analysis.ttsService.settings", makeDemoSettings()):
            from src.modules.analysis.ttsService import speak
            result = speak(longText.strip())
        assert result["content"] == longText.strip()

    def test_mode_field_is_exactly_text_string(self):
        """Ensure mode is the string 'text', not True/False/None."""
        with patch("src.modules.analysis.ttsService.settings", makeDemoSettings()):
            from src.modules.analysis.ttsService import speak
            result = speak("A question.")
        assert result["mode"] == "text"
        assert isinstance(result["mode"], str)


# ════════════════════════════════════════════════════════════════════════════════
# Production Mode Tests
# ════════════════════════════════════════════════════════════════════════════════

class TestTtsProductionMode:

    def _makeSuccessResponse(self, audioData: bytes = b"MP3_AUDIO_DATA") -> MagicMock:
        """Build a mock httpx response that simulates a successful ElevenLabs call."""
        mockResponse = MagicMock()
        mockResponse.content = audioData
        mockResponse.raise_for_status.return_value = None  # No exception
        return mockResponse

    def test_returns_mode_audio_on_success(self):
        mockResponse = self._makeSuccessResponse()
        mockClient = MagicMock()
        mockClient.post.return_value = mockResponse

        with patch("src.modules.analysis.ttsService.settings", makeProductionSettings()):
            with patch("src.modules.analysis.ttsService.getTtsClient", return_value=mockClient):
                from src.modules.analysis.ttsService import speak
                result = speak("Tell me about yourself.")

        assert result["mode"] == "audio"

    def test_returns_audio_bytes_on_success(self):
        fakeAudio = b"\xff\xfb\x90\x00FAKE_MP3_HEADER" * 100
        mockResponse = self._makeSuccessResponse(fakeAudio)
        mockClient = MagicMock()
        mockClient.post.return_value = mockResponse

        with patch("src.modules.analysis.ttsService.settings", makeProductionSettings()):
            with patch("src.modules.analysis.ttsService.getTtsClient", return_value=mockClient):
                from src.modules.analysis.ttsService import speak
                result = speak("Question text.")

        assert result["audioBytes"] == fakeAudio

    def test_content_field_contains_original_text(self):
        """Production mode must always include the original text in content."""
        inputText = "Describe your system design experience."
        mockResponse = self._makeSuccessResponse()
        mockClient = MagicMock()
        mockClient.post.return_value = mockResponse

        with patch("src.modules.analysis.ttsService.settings", makeProductionSettings()):
            with patch("src.modules.analysis.ttsService.getTtsClient", return_value=mockClient):
                from src.modules.analysis.ttsService import speak
                result = speak(inputText)

        assert result["content"] == inputText

    def test_http_client_is_called(self):
        """Production mode must call the ElevenLabs client."""
        mockResponse = self._makeSuccessResponse()
        mockClient = MagicMock()
        mockClient.post.return_value = mockResponse

        with patch("src.modules.analysis.ttsService.settings", makeProductionSettings()):
            with patch("src.modules.analysis.ttsService.getTtsClient", return_value=mockClient):
                from src.modules.analysis.ttsService import speak
                speak("A question.")

        mockClient.post.assert_called_once()

    def test_client_post_called_with_voice_id_in_path(self):
        """The endpoint must include the configured voice_id."""
        mockResponse = self._makeSuccessResponse()
        mockClient = MagicMock()
        mockClient.post.return_value = mockResponse
        voiceId = "unique-voice-id-123"

        with patch("src.modules.analysis.ttsService.settings", makeProductionSettings(voiceId=voiceId)):
            with patch("src.modules.analysis.ttsService.getTtsClient", return_value=mockClient):
                from src.modules.analysis.ttsService import speak
                speak("Question.")

        callArgs = mockClient.post.call_args
        endpoint = callArgs[0][0] if callArgs[0] else callArgs.kwargs.get("url", "")
        assert voiceId in endpoint

    def test_http_failure_falls_back_to_text_mode(self):
        """HTTP error must degrade gracefully to text mode — never crash."""
        mockClient = MagicMock()
        mockClient.post.side_effect = Exception("Connection timeout")

        with patch("src.modules.analysis.ttsService.settings", makeProductionSettings()):
            with patch("src.modules.analysis.ttsService.getTtsClient", return_value=mockClient):
                from src.modules.analysis.ttsService import speak
                result = speak("A question that will fail TTS.")

        assert result["mode"] == "text"
        assert result["audioUrl"] is None

    def test_http_failure_preserves_original_text(self):
        """On TTS failure, original text must be available in content field."""
        inputText = "Design a distributed cache."
        mockClient = MagicMock()
        mockClient.post.side_effect = Exception("Rate limit exceeded")

        with patch("src.modules.analysis.ttsService.settings", makeProductionSettings()):
            with patch("src.modules.analysis.ttsService.getTtsClient", return_value=mockClient):
                from src.modules.analysis.ttsService import speak
                result = speak(inputText)

        assert result["content"] == inputText

    def test_raise_for_status_called_on_response(self):
        """raise_for_status() must be called to surface HTTP 4xx/5xx errors."""
        mockResponse = self._makeSuccessResponse()
        mockClient = MagicMock()
        mockClient.post.return_value = mockResponse

        with patch("src.modules.analysis.ttsService.settings", makeProductionSettings()):
            with patch("src.modules.analysis.ttsService.getTtsClient", return_value=mockClient):
                from src.modules.analysis.ttsService import speak
                speak("Question.")

        mockResponse.raise_for_status.assert_called_once()

    def test_http_4xx_error_falls_back_to_text(self):
        """A 4xx raise_for_status should trigger graceful fallback."""
        import httpx
        mockResponse = MagicMock()
        mockResponse.raise_for_status.side_effect = Exception("HTTP 401 Unauthorized")
        mockClient = MagicMock()
        mockClient.post.return_value = mockResponse

        with patch("src.modules.analysis.ttsService.settings", makeProductionSettings()):
            with patch("src.modules.analysis.ttsService.getTtsClient", return_value=mockClient):
                from src.modules.analysis.ttsService import speak
                result = speak("Question text.")

        assert result["mode"] == "text"

    def test_empty_text_skips_http_call(self):
        """Empty text in production mode should not call the API."""
        with patch("src.modules.analysis.ttsService.settings", makeProductionSettings()):
            with patch("src.modules.analysis.ttsService.getTtsClient") as mockGetClient:
                from src.modules.analysis.ttsService import speak
                result = speak("")
        mockGetClient.assert_not_called()
        assert result["mode"] == "text"

    def test_all_required_keys_present_in_production_success(self):
        mockResponse = self._makeSuccessResponse()
        mockClient = MagicMock()
        mockClient.post.return_value = mockResponse

        with patch("src.modules.analysis.ttsService.settings", makeProductionSettings()):
            with patch("src.modules.analysis.ttsService.getTtsClient", return_value=mockClient):
                from src.modules.analysis.ttsService import speak
                result = speak("Question.")

        missing = _REQUIRED_KEYS - set(result.keys())
        assert not missing, f"Missing keys in production response: {missing}"

    def test_all_required_keys_present_in_production_failure(self):
        mockClient = MagicMock()
        mockClient.post.side_effect = Exception("Network error")

        with patch("src.modules.analysis.ttsService.settings", makeProductionSettings()):
            with patch("src.modules.analysis.ttsService.getTtsClient", return_value=mockClient):
                from src.modules.analysis.ttsService import speak
                result = speak("Question.")

        missing = _REQUIRED_KEYS - set(result.keys())
        assert not missing, f"Missing keys in failure response: {missing}"


# ════════════════════════════════════════════════════════════════════════════════
# getTtsClient Caching
# ════════════════════════════════════════════════════════════════════════════════

class TestGetTtsClientCaching:

    def test_client_is_cached_after_first_call(self):
        """Second call to getTtsClient() must not create a new httpx.Client."""
        import src.modules.analysis.ttsService as ttsMod

        mockHttpx = MagicMock()
        mockClient = MagicMock()
        mockHttpx.Client.return_value = mockClient

        # Reset the module cache
        originalClient = ttsMod._ttsClient
        ttsMod._ttsClient = None

        try:
            with patch("src.modules.analysis.ttsService.settings", makeProductionSettings()):
                with patch.dict("sys.modules", {"httpx": mockHttpx}):
                    ttsMod.getTtsClient()  # First call
                    ttsMod.getTtsClient()  # Second call

            assert mockHttpx.Client.call_count == 1
        finally:
            ttsMod._ttsClient = originalClient

    def test_same_client_object_returned_on_repeated_calls(self):
        """Both calls must return the identical client object."""
        import src.modules.analysis.ttsService as ttsMod

        mockHttpx = MagicMock()
        mockClient = MagicMock()
        mockHttpx.Client.return_value = mockClient

        originalClient = ttsMod._ttsClient
        ttsMod._ttsClient = None

        try:
            with patch("src.modules.analysis.ttsService.settings", makeProductionSettings()):
                with patch.dict("sys.modules", {"httpx": mockHttpx}):
                    client1 = ttsMod.getTtsClient()
                    client2 = ttsMod.getTtsClient()

            assert client1 is client2
        finally:
            ttsMod._ttsClient = originalClient
