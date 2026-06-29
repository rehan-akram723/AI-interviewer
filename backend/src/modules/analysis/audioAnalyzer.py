# ─────────────────────────────────────────────────────────────────────────────
# backend/src/modules/analysis/audioAnalyzer.py
#
# Processes interview answer audio to extract structural and vocal metrics.
#
# Production: Uses librosa for deep DSP analytics (WPM, silence intervals, RMS).
# Demo mode:  Bypasses audio completely, extracting filler words from text only.
# ─────────────────────────────────────────────────────────────────────────────

import logging
import os
import re
import tempfile
from typing import Optional

from src.core.appConfig import settings
from src.schemas.analysisSchema import AudioMetrics

logger = logging.getLogger(__name__)

# Hardcoded filler words contract
FILLER_WORDS = [
    "um", "uh", "like", "you know", "basically",
    "literally", "sort of", "kind of"
]

def analyzeAudio(
    audioBytes: Optional[bytes],
    transcript: str,
    answerIndex: int
) -> AudioMetrics:
    """
    Computes AudioMetrics for a given interview answer.
    
    Args:
        audioBytes: Raw audio data (used in production).
        transcript: The text of the answer.
        answerIndex: Index of the answer.

    Returns:
        AudioMetrics struct.
    """
    # ── Universal text-based analysis ─────────────────────────────────────────
    # Word boundaries to avoid matching "like" inside "alike", or "um" in "drum"
    safeTranscript = (transcript or "").lower()
    
    fillerCount = 0
    detectedFillers = set()
    
    for fw in FILLER_WORDS:
        # Regex to match exact word/phrase with boundaries
        pattern = r'\b' + re.escape(fw) + r'\b'
        matches = len(re.findall(pattern, safeTranscript))
        if matches > 0:
            fillerCount += matches
            detectedFillers.add(fw)
            
    wordCount = len(safeTranscript.split())

    # ── Demo mode short-circuit ───────────────────────────────────────────────
    if settings.is_demo or not audioBytes:
        if settings.is_production and not audioBytes:
            logger.warning(
                "analyzeAudio [production]: audioBytes is empty. "
                "Falling back to text-only demo analysis."
            )
            
        return AudioMetrics(
            answer_index=answerIndex,
            words_per_minute=None,
            filler_word_count=fillerCount,
            filler_words_detected=list(detectedFillers),
            avg_pause_duration_seconds=None,
            longest_pause_seconds=None,
            voice_energy_level=None,
            demo_mode=True
        )

    # ── Production mode: Deep DSP with librosa ────────────────────────────────
    try:
        import librosa  # type: ignore[import]
        import numpy as np # type: ignore[import]
    except ImportError as exc:
        logger.error("analyzeAudio: librosa or numpy missing. Falling back.")
        return AudioMetrics(
            answer_index=answerIndex,
            filler_word_count=fillerCount,
            filler_words_detected=list(detectedFillers),
            demo_mode=True
        )

    tmpFilePath = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False, prefix="analyzer_") as tmpFile:
            tmpFilePath = tmpFile.name
            tmpFile.write(audioBytes)

        # Load audio (y is audio time series, sr is sampling rate)
        y, sr = librosa.load(tmpFilePath, sr=None)
        
        # Guard against completely empty/silent tracks
        if len(y) == 0:
            return AudioMetrics(
                answer_index=answerIndex,
                filler_word_count=fillerCount,
                filler_words_detected=list(detectedFillers),
                demo_mode=True
            )

        duration = librosa.get_duration(y=y, sr=sr)
        
        # 1. Words per minute
        wpm = (wordCount / duration) * 60 if duration > 0 else 0.0

        # 2. Voice energy level (RMS)
        # librosa.load normally normalizes to [-1.0, 1.0], so RMS max is 1.0
        # We take the mean RMS to represent the average speaking energy
        rms_frames = librosa.feature.rms(y=y)[0]
        mean_rms = float(np.mean(rms_frames))
        # Ensure it's cleanly capped between 0 and 1
        energy_level = max(0.0, min(1.0, mean_rms))

        # 3. Pause durations
        # librosa.effects.split returns intervals of non-silent regions [start, end]
        # We find the gaps between these intervals to get pause durations
        speech_intervals = librosa.effects.split(y, top_db=30)
        
        pause_durations = []
        if len(speech_intervals) > 1:
            for i in range(len(speech_intervals) - 1):
                # Gap between end of current and start of next
                gap_samples = speech_intervals[i+1][0] - speech_intervals[i][1]
                gap_seconds = gap_samples / sr
                if gap_seconds > 0.0:
                    pause_durations.append(gap_seconds)
                    
        avg_pause = float(np.mean(pause_durations)) if pause_durations else 0.0
        longest_pause = float(np.max(pause_durations)) if pause_durations else 0.0

        return AudioMetrics(
            answer_index=answerIndex,
            words_per_minute=round(wpm, 1),
            filler_word_count=fillerCount,
            filler_words_detected=list(detectedFillers),
            avg_pause_duration_seconds=round(avg_pause, 2),
            longest_pause_seconds=round(longest_pause, 2),
            voice_energy_level=round(energy_level, 3),
            demo_mode=False
        )

    except Exception as exc:
        logger.error("analyzeAudio [production]: Analysis failed: %s", exc)
        return AudioMetrics(
            answer_index=answerIndex,
            filler_word_count=fillerCount,
            filler_words_detected=list(detectedFillers),
            demo_mode=True
        )

    finally:
        if tmpFilePath and os.path.exists(tmpFilePath):
            try:
                os.remove(tmpFilePath)
            except OSError as cleanupErr:
                logger.warning(
                    "analyzeAudio: Failed to delete temp file %s: %s",
                    tmpFilePath, cleanupErr
                )
