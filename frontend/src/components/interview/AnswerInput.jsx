// ─────────────────────────────────────────────────────────────────────────────
// frontend/src/components/interview/AnswerInput.jsx
//
// Dynamically switches between a text-input path (demo mode) and a
// voice-recording action panel (production mode) based on `isDemo`.
// ─────────────────────────────────────────────────────────────────────────────

import React, { useState, useEffect } from 'react';
import useAudioRecorder from '../../hooks/useAudioRecorder';

const AnswerInput = ({ isDemo = true, onSubmitAnswer, isSubmitting = false }) => {
    const [textAnswer, setTextAnswer] = useState('');
    const { isRecording, audioBlob, permissionError, startRecording, stopRecording, clearAudioBlob } =
        useAudioRecorder(isDemo);

    // When an audioBlob is ready, automatically submit it
    useEffect(() => {
        if (audioBlob && !isDemo) {
            onSubmitAnswer({ audioBlob, textAnswer: '' });
            clearAudioBlob();
        }
    }, [audioBlob]);

    const handleTextSubmit = () => {
        const trimmed = textAnswer.trim();
        if (!trimmed) return;
        onSubmitAnswer({ audioBlob: null, textAnswer: trimmed });
        setTextAnswer('');
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleTextSubmit();
        }
    };

    // ── Demo mode: Standard text input ────────────────────────────────────────
    if (isDemo) {
        return (
            <div className="space-y-3">
                <textarea
                    className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-none h-28 text-sm transition-all"
                    placeholder="Type your answer here... (Press Enter to submit)"
                    value={textAnswer}
                    onChange={(e) => setTextAnswer(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={isSubmitting}
                />
                <button
                    onClick={handleTextSubmit}
                    disabled={!textAnswer.trim() || isSubmitting}
                    className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white font-semibold py-2.5 rounded-lg transition-colors"
                >
                    {isSubmitting ? 'Submitting...' : 'Submit Answer →'}
                </button>
            </div>
        );
    }

    // ── Production mode: Voice recording panel ────────────────────────────────
    return (
        <div className="space-y-3">
            {permissionError && (
                <div className="bg-red-50 border-l-4 border-red-500 p-3 rounded text-sm text-red-700">
                    {permissionError}
                </div>
            )}

            <div className="flex items-center justify-center">
                <button
                    onClick={isRecording ? stopRecording : startRecording}
                    disabled={isSubmitting}
                    className={`flex items-center gap-3 px-8 py-4 rounded-full font-semibold text-white transition-all shadow-lg ${
                        isRecording
                            ? 'bg-red-500 hover:bg-red-600 animate-pulse'
                            : 'bg-blue-600 hover:bg-blue-700'
                    } disabled:bg-gray-300`}
                >
                    {isRecording ? (
                        <>
                            <span className="w-3 h-3 bg-white rounded-sm"></span>
                            Stop Recording
                        </>
                    ) : (
                        <>
                            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M7 4a3 3 0 016 0v4a3 3 0 01-6 0V4zm-1 4a4 4 0 008 0V4a4 4 0 00-8 0v4z" />
                                <path d="M3.5 9a1 1 0 00-1 1 7.5 7.5 0 0015 0 1 1 0 00-2 0 5.5 5.5 0 01-11 0 1 1 0 00-1-1z" />
                            </svg>
                            Start Recording
                        </>
                    )}
                </button>
            </div>

            {isRecording && (
                <p className="text-center text-sm text-red-500 font-medium">
                    🔴 Recording in progress...
                </p>
            )}

            {isSubmitting && (
                <p className="text-center text-sm text-blue-500 font-medium">
                    Submitting your answer...
                </p>
            )}
        </div>
    );
};

export default AnswerInput;
