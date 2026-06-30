import React, { useState, useRef, useCallback, useEffect } from 'react';
import useWebSocket from '../../hooks/useWebSocket';
import AnswerInput from './AnswerInput';
import CameraFeed from './CameraFeed';
import QuestionDisplay from './QuestionDisplay';
import CoachingSidebar from './CoachingSidebar';
import ProgressBar from './ProgressBar';
import axios from 'axios';
import { useSession } from '../../context/SessionContext';

const PHASE_LABELS = {
    icebreaker: { label: 'Icebreaker', color: 'rgba(20, 184, 166, 0.15)', text: '#14b8a6' },
    cv_deep_dive: { label: 'CV Deep Dive', color: 'rgba(59, 130, 246, 0.15)', text: '#3b82f6' },
    dynamic_followup: { label: 'Follow-up', color: 'rgba(168, 85, 247, 0.15)', text: '#a855f7' },
    closing: { label: 'Closing', color: 'rgba(156, 163, 175, 0.15)', text: '#9ca3af' }
};

const InterviewRoom = ({ sessionId, isDemo = true, sessionMeta = {} }) => {
    const { setCurrentPhase } = useSession();
    const [currentQuestion, setCurrentQuestion] = useState(null);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [submitError, setSubmitError] = useState(null);
    const cameraRef = useRef(null);

    const { isConnected, coachingFeedback, difficultyMetrics, connectionError } =
        useWebSocket(sessionId);

    // Fetch the first question when the room loads
    useEffect(() => {
        if (!sessionId) return;
        const fetchInitialQuestion = async () => {
            try {
                const res = await axios.get(`http://localhost:8000/api/sessions/${sessionId}/question`);
                if (res.data.status === 'completed') {
                    setCurrentPhase('report');
                } else {
                    setCurrentQuestion(res.data.question);
                }
            } catch (err) {
                console.error("[InterviewRoom] Failed to fetch initial question", err);
                setSubmitError("Failed to load the first question. Please try refreshing.");
            }
        };
        fetchInitialQuestion();
    }, [sessionId, setCurrentPhase]);

    const handleSubmitAnswer = useCallback(async ({ audioBlob, textAnswer }) => {
        if (isSubmitting || !currentQuestion) return;
        setIsSubmitting(true);
        setSubmitError(null);

        try {
            let audioBase64 = null;
            if (audioBlob) {
                // Convert audioBlob to base64
                audioBase64 = await new Promise((resolve, reject) => {
                    const reader = new FileReader();
                    reader.onloadend = () => {
                        const b64 = reader.result.split(',')[1];
                        resolve(b64);
                    };
                    reader.onerror = reject;
                    reader.readAsDataURL(audioBlob);
                });
            }

            const payload = {
                questionIndex: currentQuestion.index,
                text: textAnswer || '',
                audioBase64: audioBase64,
                facialData: null
            };

            const res = await axios.post(
                `http://localhost:8000/api/sessions/${sessionId}/answer`,
                payload,
                { headers: { 'Content-Type': 'application/json' } }
            );

            // Handle turn completion
            if (res.data.is_complete || res.data.status === 'completed') {
                setCurrentPhase('report');
            } else {
                setCurrentQuestion(res.data.next_question);
            }
        } catch (err) {
            console.error('[InterviewRoom] Failed to submit answer:', err);
            setSubmitError('Failed to submit your answer. Please try again.');
        } finally {
            setIsSubmitting(false);
        }
    }, [sessionId, currentQuestion, isSubmitting, setCurrentPhase]);

    const phaseConfig = PHASE_LABELS[currentQuestion?.phase] || PHASE_LABELS.icebreaker;

    return (
        <div style={{
            minHeight: 'calc(100vh - 56px)',
            display: 'flex',
            flexDirection: 'column',
            background: 'var(--bg-primary)',
        }}>
            {/* Top Status Bar */}
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0.75rem 1.5rem',
                background: 'var(--bg-surface)',
                borderBottom: '1px solid var(--bg-border)',
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span style={{
                        width: 8, height: 8, borderRadius: '50%',
                        background: isConnected ? '#10b981' : '#ef4444',
                        boxShadow: isConnected ? '0 0 10px #10b981' : 'none',
                        animation: !isConnected ? 'pulse-dot 2s infinite' : 'none'
                    }}></span>
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        {isConnected ? 'Live Connection Active' : 'Reconnecting...'}
                    </span>
                    {isDemo && (
                        <span style={{
                            marginLeft: '8px',
                            padding: '2px 8px',
                            fontSize: '0.7rem',
                            fontWeight: 700,
                            background: 'var(--accent-amber)',
                            color: '#000',
                            borderRadius: '99px',
                            letterSpacing: '0.5px'
                        }}>
                            DEMO MODE
                        </span>
                    )}
                </div>
                <div style={{ display: 'flex', gap: '24px', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                    <span>Level <strong style={{ color: '#fff' }}>{difficultyMetrics.difficultyLevel || 2}/5</strong></span>
                    <span>Question <strong style={{ color: '#fff' }}>{(currentQuestion?.index ?? 0) + 1}</strong></span>
                </div>
            </div>

            {/* Main Content Area */}
            <div style={{
                display: 'flex',
                flex: 1,
                overflow: 'hidden',
                position: 'relative'
            }}>
                {/* ── LEFT/CENTER: Interactive Interview ──────────────────── */}
                <div style={{
                    flex: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    padding: '2rem',
                    gap: '1.5rem',
                    overflowY: 'auto',
                }}>
                    {/* The Production Camera View / Demo View */}
                    <div style={{
                        width: '100%',
                        maxWidth: isDemo ? '900px' : '1000px',
                        margin: '0 auto',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '2rem'
                    }}>
                        
                        {/* ── Video/Feedback Container (Floating UI in Production) ── */}
                        <CameraFeed 
                            isDemo={isDemo} 
                            cameraRef={cameraRef} 
                            coachingFeedback={coachingFeedback}
                            difficultyMetrics={difficultyMetrics}
                        />

                        {/* ── Question & Answer Area ── */}
                        <div style={{
                            background: 'var(--bg-elevated)',
                            border: '1px solid var(--bg-border)',
                            borderRadius: '16px',
                            padding: '2rem',
                            boxShadow: '0 8px 30px rgba(0,0,0,0.2)'
                        }}>
                            <QuestionDisplay 
                                currentQuestion={currentQuestion}
                                connectionError={connectionError}
                                submitError={submitError}
                                phaseConfig={phaseConfig}
                            />

                            <div style={{ marginTop: '2rem', paddingTop: '2rem', borderTop: '1px solid var(--bg-border)' }}>
                                <AnswerInput
                                    isDemo={isDemo}
                                    onSubmitAnswer={handleSubmitAnswer}
                                    isSubmitting={isSubmitting}
                                />
                            </div>
                        </div>

                    </div>
                </div>

                {/* ── RIGHT: Sidebar for DEMO Mode ONLY ──────────────────── */}
                {/* In production mode, coaching floats on the webcam. In demo mode, it stays in a sidebar. */}
                {isDemo && (
                    <div style={{
                        width: '320px',
                        borderLeft: '1px solid var(--bg-border)',
                        background: 'var(--bg-surface)',
                        display: 'flex',
                        flexDirection: 'column'
                    }}>
                        <CoachingSidebar coachingFeedback={coachingFeedback} />
                    </div>
                )}
            </div>
        </div>
    );
};

export default InterviewRoom;
