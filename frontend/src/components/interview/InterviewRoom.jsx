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
import CameraFeed from './CameraFeed';
import QuestionDisplay from './QuestionDisplay';
import CoachingSidebar from './CoachingSidebar';
import ProgressBar from './ProgressBar';
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
                    <span>Difficulty: <strong className="text-white">{difficultyMetrics.difficultyLevel || 2}/5</strong></span>
                    <span>Question: <strong className="text-white">{(currentQuestion?.index ?? 0) + 1}</strong></span>
                </div>
            </div>

            {/* ── Progress Bar ─────────────────────────────────────────────────── */}
            <div className="bg-gray-900 py-3 border-b border-gray-800">
                <ProgressBar currentQuestionIndex={currentQuestion?.index ?? 0} totalQuestions={5} />
            </div>

            {/* ── Three-Column Main Body ───────────────────────────────────────── */}
            <div className="flex flex-1 overflow-hidden">
                
                {/* ── LEFT: Camera / Demo Placeholder ────────────────────────── */}
                <CameraFeed 
                    isDemo={isDemo} 
                    cameraRef={cameraRef} 
                    difficultyMetrics={difficultyMetrics} 
                />

                {/* ── CENTER: Question + Answer ───────────────────────────────── */}
                <main className="flex-1 flex flex-col justify-center px-10 py-8 space-y-6 max-w-3xl mx-auto w-full">
                    
                    <QuestionDisplay 
                        currentQuestion={currentQuestion}
                        connectionError={connectionError}
                        submitError={submitError}
                        phaseConfig={phaseConfig}
                    />

                    {/* Answer input */}
                    <div className="bg-gray-900 rounded-xl p-5 border border-gray-800 shadow-xl">
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
                <CoachingSidebar coachingFeedback={coachingFeedback} />

            </div>
        </div>
    );
};

export default InterviewRoom;
