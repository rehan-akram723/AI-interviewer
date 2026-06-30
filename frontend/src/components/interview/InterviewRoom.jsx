// ─────────────────────────────────────────────────────────────────────────────
// frontend/src/components/interview/InterviewRoom.jsx
//
// The core live interview interface. Three-column layout:
//  Left   — Camera feed (production) or text indicator (demo)
//  Center — Question display + phase badge + AnswerInput
//  Right  — Coaching sidebar with real-time feedback from WebSocket
// ─────────────────────────────────────────────────────────────────────────────

import React, { useState, useRef, useCallback } from 'react';
import useWebSocket from '../../hooks/useWebSocket';
import AnswerInput from './AnswerInput';
import { setupInterview } from '../../services/api';
import axios from 'axios';

const PHASE_LABELS = {
    icebreaker: { label: 'Icebreaker', color: 'bg-teal-100 text-teal-800' },
    cv_deep_dive: { label: 'CV Deep Dive', color: 'bg-blue-100 text-blue-800' },
    dynamic_followup: { label: 'Follow-up', color: 'bg-purple-100 text-purple-800' },
    closing: { label: 'Closing', color: 'bg-gray-100 text-gray-700' }
};

const InterviewRoom = ({ sessionId, isDemo = true, currentQuestion = null, sessionMeta = {} }) => {
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [submitError, setSubmitError] = useState(null);
    const cameraRef = useRef(null);

    const { isConnected, coachingFeedback, difficultyMetrics, connectionError } =
        useWebSocket(sessionId);

    const handleSubmitAnswer = useCallback(async ({ audioBlob, textAnswer }) => {
        if (isSubmitting) return;
        setIsSubmitting(true);
        setSubmitError(null);

        try {
            const formData = new FormData();
            formData.append('sessionId', sessionId);
            formData.append('questionIndex', currentQuestion?.index ?? 0);
            formData.append('textAnswer', textAnswer || '');

            if (audioBlob) {
                formData.append('audioFile', audioBlob, 'answer.webm');
            }

            await axios.post(
                `http://localhost:8000/api/sessions/${sessionId}/answer`,
                formData,
                { headers: { 'Content-Type': 'multipart/form-data' } }
            );
        } catch (err) {
            console.error('[InterviewRoom] Failed to submit answer:', err);
            setSubmitError('Failed to submit your answer. Please try again.');
        } finally {
            setIsSubmitting(false);
        }
    }, [sessionId, currentQuestion, isSubmitting]);

    const phaseConfig = PHASE_LABELS[currentQuestion?.phase] || PHASE_LABELS.icebreaker;

    return (
        <div className="min-h-screen bg-gray-950 text-white flex flex-col">
            
            {/* ── Top Status Bar ──────────────────────────────────────────────── */}
            <div className="flex items-center justify-between px-6 py-3 bg-gray-900 border-b border-gray-800">
                <div className="flex items-center gap-3">
                    <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400 animate-pulse'}`}></span>
                    <span className="text-sm text-gray-400">
                        {isConnected ? 'Live — Connected' : 'Reconnecting...'}
                    </span>
                    {isDemo && (
                        <span className="ml-2 px-2 py-0.5 text-xs font-medium bg-amber-500 text-black rounded-full">
                            DEMO MODE
                        </span>
                    )}
                </div>
                <div className="flex items-center gap-4 text-sm text-gray-400">
                    <span>Difficulty: <strong className="text-white">{difficultyMetrics.difficultyLevel}/5</strong></span>
                    <span>Question: <strong className="text-white">{(currentQuestion?.index ?? 0) + 1}</strong></span>
                </div>
            </div>

            {/* ── Three-Column Main Body ───────────────────────────────────────── */}
            <div className="flex flex-1 overflow-hidden">
                
                {/* ── LEFT: Camera / Demo Placeholder ────────────────────────── */}
                <aside className="w-64 flex-shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col items-center justify-center p-4 space-y-4">
                    {isDemo ? (
                        <div className="w-full aspect-video rounded-xl bg-gray-800 border-2 border-dashed border-gray-600 flex flex-col items-center justify-center space-y-2">
                            <svg className="w-10 h-10 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M3 8a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z" />
                            </svg>
                            <p className="text-xs text-gray-500 text-center">Camera disabled in demo mode</p>
                        </div>
                    ) : (
                        <video
                            ref={cameraRef}
                            className="w-full aspect-video rounded-xl bg-black object-cover"
                            autoPlay
                            muted
                            playsInline
                        />
                    )}

                    {/* Difficulty axis pills */}
                    {Object.keys(difficultyMetrics.difficultyDimensions).length > 0 && (
                        <div className="w-full space-y-1">
                            <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">Difficulty Axes</p>
                            {Object.entries(difficultyMetrics.difficultyDimensions).map(([dim, val]) => (
                                <div key={dim} className="flex items-center justify-between text-xs">
                                    <span className="text-gray-400 capitalize">{dim}</span>
                                    <span className="text-white font-semibold">{val}/5</span>
                                </div>
                            ))}
                        </div>
                    )}
                </aside>

                {/* ── CENTER: Question + Answer ───────────────────────────────── */}
                <main className="flex-1 flex flex-col justify-center px-10 py-8 space-y-6 max-w-3xl mx-auto w-full">
                    {connectionError && (
                        <div className="bg-red-900/50 border border-red-700 rounded-lg p-3 text-sm text-red-300">
                            {connectionError}
                        </div>
                    )}

                    {/* Phase badge + question index */}
                    <div className="flex items-center gap-3">
                        <span className={`text-xs font-semibold px-3 py-1 rounded-full ${phaseConfig.color}`}>
                            {phaseConfig.label}
                        </span>
                        {currentQuestion && (
                            <span className="text-xs text-gray-500">
                                Difficulty Level {currentQuestion.difficulty}/5
                            </span>
                        )}
                    </div>

                    {/* Question text */}
                    <div className="space-y-2">
                        {currentQuestion ? (
                            <>
                                <h2 className="text-2xl font-semibold leading-snug text-white">
                                    {currentQuestion.text}
                                </h2>
                                {currentQuestion.category && (
                                    <p className="text-sm text-gray-500 capitalize">
                                        Category: {currentQuestion.category}
                                    </p>
                                )}
                            </>
                        ) : (
                            <div className="space-y-3 animate-pulse">
                                <div className="h-7 bg-gray-700 rounded w-3/4"></div>
                                <div className="h-5 bg-gray-800 rounded w-1/2"></div>
                            </div>
                        )}
                    </div>

                    {/* Submission error */}
                    {submitError && (
                        <div className="bg-red-900/50 border border-red-700 rounded-lg p-3 text-sm text-red-300">
                            {submitError}
                        </div>
                    )}

                    {/* Answer input */}
                    <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
                        <p className="text-xs text-gray-500 mb-3 font-medium uppercase tracking-wide">
                            Your Answer
                        </p>
                        <AnswerInput
                            isDemo={isDemo}
                            onSubmitAnswer={handleSubmitAnswer}
                            isSubmitting={isSubmitting}
                        />
                    </div>
                </main>

                {/* ── RIGHT: Coaching Sidebar ─────────────────────────────────── */}
                <aside className="w-80 flex-shrink-0 bg-gray-900 border-l border-gray-800 flex flex-col">
                    <div className="px-5 py-4 border-b border-gray-800">
                        <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">
                            Live Coaching
                        </h3>
                    </div>
                    <div className="flex-1 overflow-y-auto p-4 space-y-4">
                        {coachingFeedback.length === 0 ? (
                            <div className="text-center py-8 space-y-2">
                                <svg className="w-8 h-8 text-gray-700 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                                </svg>
                                <p className="text-sm text-gray-600">Coaching insights will appear here after each answer.</p>
                            </div>
                        ) : (
                            [...coachingFeedback].reverse().map((fb, idx) => (
                                <div key={idx} className="bg-gray-800 rounded-lg p-4 space-y-3 border border-gray-700">
                                    {/* Score preview */}
                                    <div className="flex items-center justify-between">
                                        <span className="text-xs text-gray-400 font-medium">Answer {fb.answerIndex + 1}</span>
                                        <span className={`text-sm font-bold ${
                                            fb.scorePreview >= 8 ? 'text-green-400' :
                                            fb.scorePreview >= 6 ? 'text-yellow-400' :
                                            'text-red-400'
                                        }`}>
                                            {fb.scorePreview}/10
                                        </span>
                                    </div>

                                    {/* Feedback text */}
                                    <p className="text-sm text-gray-300 leading-relaxed">
                                        {fb.feedbackText}
                                    </p>

                                    {/* Strengths */}
                                    {fb.strengths?.length > 0 && (
                                        <div>
                                            <p className="text-xs text-green-400 font-semibold mb-1">✓ Strengths</p>
                                            <ul className="space-y-0.5">
                                                {fb.strengths.map((s, i) => (
                                                    <li key={i} className="text-xs text-gray-400">• {s}</li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}

                                    {/* Improvements */}
                                    {fb.improvements?.length > 0 && (
                                        <div>
                                            <p className="text-xs text-amber-400 font-semibold mb-1">⚑ Improve</p>
                                            <ul className="space-y-0.5">
                                                {fb.improvements.map((s, i) => (
                                                    <li key={i} className="text-xs text-gray-400">• {s}</li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </div>
                            ))
                        )}
                    </div>
                </aside>

            </div>
        </div>
    );
};

export default InterviewRoom;
