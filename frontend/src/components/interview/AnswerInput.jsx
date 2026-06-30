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
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <p style={{
                    margin: 0,
                    fontSize: '0.8rem',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                    color: 'var(--text-muted)'
                }}>
                    Your Answer
                </p>
                <textarea
                    style={{
                        width: '100%',
                        height: '140px',
                        background: 'var(--bg-surface)',
                        border: '1px solid var(--bg-border)',
                        borderRadius: '12px',
                        padding: '16px',
                        fontSize: '0.95rem',
                        color: 'var(--text-primary)',
                        resize: 'none',
                        outline: 'none',
                        transition: 'border-color 0.2s',
                        fontFamily: 'inherit',
                        lineHeight: 1.5,
                        boxSizing: 'border-box'
                    }}
                    placeholder="Type your answer here... (Press Enter to submit)"
                    value={textAnswer}
                    onChange={(e) => setTextAnswer(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={isSubmitting}
                    onFocus={(e) => e.target.style.borderColor = 'var(--accent-blue)'}
                    onBlur={(e) => e.target.style.borderColor = 'var(--bg-border)'}
                />
                <button
                    onClick={handleTextSubmit}
                    disabled={!textAnswer.trim() || isSubmitting}
                    style={{
                        width: '100%',
                        background: (!textAnswer.trim() || isSubmitting) ? 'var(--bg-muted)' : 'var(--accent-blue)',
                        color: (!textAnswer.trim() || isSubmitting) ? 'var(--text-muted)' : '#fff',
                        border: 'none',
                        borderRadius: '10px',
                        padding: '14px',
                        fontSize: '0.95rem',
                        fontWeight: 600,
                        cursor: (!textAnswer.trim() || isSubmitting) ? 'not-allowed' : 'pointer',
                        transition: 'all 0.2s',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '8px'
                    }}
                >
                    {isSubmitting ? (
                        <>
                            <svg style={{ width: '18px', height: '18px', animation: 'spin 1s linear infinite' }} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle style={{ opacity: 0.25 }} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path style={{ opacity: 0.75 }} fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            Analyzing Answer...
                        </>
                    ) : 'Submit Answer →'}
                </button>
            </div>
        );
    }

    // ── Production mode: Voice recording panel ────────────────────────────────
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', alignItems: 'center' }}>
            {permissionError && (
                <div style={{
                    background: 'rgba(239, 68, 68, 0.1)',
                    border: '1px solid rgba(239, 68, 68, 0.3)',
                    borderRadius: '8px',
                    padding: '12px 16px',
                    fontSize: '0.85rem',
                    color: '#fca5a5',
                    width: '100%',
                    boxSizing: 'border-box',
                    textAlign: 'center'
                }}>
                    {permissionError}
                </div>
            )}

            <button
                onClick={isRecording ? stopRecording : startRecording}
                disabled={isSubmitting}
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '12px',
                    padding: '16px 32px',
                    borderRadius: '99px',
                    fontSize: '1rem',
                    fontWeight: 700,
                    color: '#fff',
                    background: isRecording ? '#ef4444' : 'var(--accent-blue)',
                    border: 'none',
                    cursor: isSubmitting ? 'not-allowed' : 'pointer',
                    opacity: isSubmitting ? 0.5 : 1,
                    transition: 'all 0.3s ease',
                    boxShadow: isRecording ? '0 0 20px rgba(239, 68, 68, 0.5)' : '0 10px 20px rgba(59, 130, 246, 0.2)',
                    animation: isRecording ? 'pulse-dot 2s infinite' : 'none'
                }}
            >
                {isRecording ? (
                    <>
                        <div style={{ width: '12px', height: '12px', background: '#fff', borderRadius: '2px' }}></div>
                        Stop Recording
                    </>
                ) : (
                    <>
                        <svg style={{ width: '20px', height: '20px' }} fill="currentColor" viewBox="0 0 20 20">
                            <path d="M7 4a3 3 0 016 0v4a3 3 0 01-6 0V4zm-1 4a4 4 0 008 0V4a4 4 0 00-8 0v4z" />
                            <path d="M3.5 9a1 1 0 00-1 1 7.5 7.5 0 0015 0 1 1 0 00-2 0 5.5 5.5 0 01-11 0 1 1 0 00-1-1z" />
                        </svg>
                        Start Recording
                    </>
                )}
            </button>

            {isRecording && (
                <p style={{ color: '#ef4444', fontSize: '0.85rem', fontWeight: 600, animation: 'pulse-dot 2s infinite', margin: 0 }}>
                    🔴 Recording in progress...
                </p>
            )}

            {isSubmitting && (
                <p style={{ color: 'var(--accent-blue)', fontSize: '0.85rem', fontWeight: 600, margin: 0 }}>
                    Submitting your answer...
                </p>
            )}
        </div>
    );
};

export default AnswerInput;
