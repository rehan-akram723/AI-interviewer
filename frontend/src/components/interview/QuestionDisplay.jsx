import React from 'react';

const QuestionDisplay = ({ currentQuestion, connectionError, submitError, phaseConfig }) => {
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {connectionError && (
                <div style={{
                    background: 'rgba(239, 68, 68, 0.1)',
                    border: '1px solid rgba(239, 68, 68, 0.3)',
                    borderRadius: '8px',
                    padding: '12px 16px',
                    fontSize: '0.85rem',
                    color: '#fca5a5'
                }}>
                    {connectionError}
                </div>
            )}

            {/* Phase badge + question index */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                    padding: '4px 10px',
                    borderRadius: '99px',
                    background: phaseConfig.color,
                    color: phaseConfig.text,
                    border: `1px solid ${phaseConfig.text}33`
                }}>
                    {phaseConfig.label}
                </span>
                {currentQuestion && (
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                        Difficulty Level {currentQuestion.difficulty}/5
                    </span>
                )}
            </div>

            {/* Question text */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {currentQuestion ? (
                    <>
                        <h2 style={{
                            fontSize: '1.75rem',
                            fontWeight: 700,
                            lineHeight: 1.4,
                            color: 'var(--text-primary)',
                            margin: 0,
                            letterSpacing: '-0.5px'
                        }}>
                            {currentQuestion.text}
                        </h2>
                        {currentQuestion.category && (
                            <p style={{
                                fontSize: '0.9rem',
                                color: 'var(--text-secondary)',
                                textTransform: 'capitalize',
                                margin: 0,
                                fontWeight: 500
                            }}>
                                Category: <span style={{ color: 'var(--text-primary)' }}>{currentQuestion.category}</span>
                            </p>
                        )}
                    </>
                ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', animation: 'pulse-dot 2s infinite' }}>
                        <div style={{ height: '32px', background: 'var(--bg-muted)', borderRadius: '6px', width: '85%' }}></div>
                        <div style={{ height: '32px', background: 'var(--bg-muted)', borderRadius: '6px', width: '60%' }}></div>
                    </div>
                )}
            </div>

            {/* Submission error */}
            {submitError && (
                <div style={{
                    background: 'rgba(239, 68, 68, 0.1)',
                    border: '1px solid rgba(239, 68, 68, 0.3)',
                    borderRadius: '8px',
                    padding: '12px 16px',
                    fontSize: '0.85rem',
                    color: '#fca5a5'
                }}>
                    {submitError}
                </div>
            )}
        </div>
    );
};

export default QuestionDisplay;
