import os
import sys
import io
import wave
import math
import struct
import asyncio
import time

# Add the backend directory to sys.path to allow importing from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.appConfig import settings
from src.core.logger import configureLogging
from src.modules.analysis.sttService import transcribe
from src.agents.liveCoachAgent import liveCoachAgent
from src.agents.difficultyCalibratorAgent import difficultyCalibratorAgent
from src.modules.analysis.audioAnalyzer import analyzeAudio

def generate_dummy_wav(duration_sec=5, sample_rate=16000, frequency=440.0):
    buf = io.BytesIO()
    with wave.open(buf, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        
        num_samples = int(duration_sec * sample_rate)
        data = []
        for i in range(num_samples):
            value = int(32767.0 * math.sin(2.0 * math.pi * frequency * i / sample_rate))
            data.append(struct.pack('<h', value))
        
        f.writeframes(b''.join(data))
    return buf.getvalue()

async def main():
    configureLogging()
    
    # 1. Force production mode
    settings.app_mode = "production"
    print(f"Forced app_mode to: {settings.app_mode}")

    # 2. Build mock InterviewSession
    mock_session = {
        "session_id": "test-prod-session-001",
        "candidate_id": "candidate-123",
        "confirmed_skills": ["Python", "FastAPI", "React"],
        "interview_length": "short",
        "interview_mode": "technical",
        "status": "in_progress",
        "phase": "technical",
        "current_question_index": 0,
        "difficulty_level": 3,
        "difficulty_dimensions": {
            "communication_clarity": 3,
            "technical_relevance": 3,
            "problem_solving": 3,
            "motivation_fit": 3,
            "confidence": 3,
            "listening_comprehension": 3
        },
        "asked_questions": [{
            "index": 0,
            "text": "Can you explain how FastAPI handles async requests?",
            "phase": "technical",
            "category": "backend",
            "difficulty": 3,
            "followup_count": 0,
            "asked_at": "2026-07-01T12:00:00Z"
        }],
        "answers": [{
            "question_index": 0,
            "text": "", # Will be filled by transcription
            "audio_path": None,
            "answered_at": "2026-07-01T12:00:05Z",
            "duration_seconds": 5.0
        }],
        "coaching_feedback": [],
        "audio_metrics_per_answer": [],
        "step_log": []
    }

    # 3. Generate dummy WAV
    print("\n--- Generating dummy WAV ---")
    wav_bytes = generate_dummy_wav(duration_sec=5.0)
    print(f"Generated {len(wav_bytes)} bytes of WAV audio.")

    # 4. Invoke sequentially
    print("\n--- Step 1: sttService.transcribe() ---")
    t0 = time.time()
    try:
        transcript = transcribe(audioBytes=wav_bytes, textInput=None)
        print(f"Transcription: '{transcript}'")
    except Exception as e:
        print(f"Transcription failed (expected degradation if Whisper isn't installed): {e}")
        transcript = "Fallback transcript since STT failed."
    t1 = time.time()
    print(f"Latency: {(t1 - t0) * 1000:.2f} ms")

    mock_session["answers"][0]["text"] = transcript

    print("\n--- Step 2: liveCoachAgent ---")
    t0 = time.time()
    coach_result = liveCoachAgent(mock_session)
    mock_session.update(coach_result)
    t1 = time.time()
    print(f"Latency: {(t1 - t0) * 1000:.2f} ms")
    if mock_session["coaching_feedback"]:
        print(f"Extracted coaching feedback: {mock_session['coaching_feedback'][-1]}")

    print("\n--- Step 3: difficultyCalibratorAgent ---")
    t0 = time.time()
    calibrator_result = difficultyCalibratorAgent(mock_session)
    mock_session.update(calibrator_result)
    t1 = time.time()
    print(f"Latency: {(t1 - t0) * 1000:.2f} ms")
    print(f"New Difficulty Level: {mock_session.get('difficulty_level')}")
    print(f"New Difficulty Dimensions: {mock_session.get('difficulty_dimensions')}")

    print("\n--- Step 4: audioAnalyzer ---")
    t0 = time.time()
    metrics = analyzeAudio(audioBytes=wav_bytes, transcript=transcript, answerIndex=0)
    t1 = time.time()
    print(f"Latency: {(t1 - t0) * 1000:.2f} ms")
    print(f"Audio Metrics: {metrics.model_dump() if hasattr(metrics, 'model_dump') else metrics}")

    print("\n--- Production Turn Test Complete ---")

if __name__ == "__main__":
    asyncio.run(main())
