import React from 'react';

const CoachingSidebar = ({ coachingFeedback = [] }) => {
    return (
        <div style={{
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
        }}>
            <div style={{
                padding: '1.25rem 1.5rem',
                borderBottom: '1px solid var(--bg-border)',
                background: 'var(--bg-elevated)',
            }}>
                <h3 style={{
                    margin: 0,
                    fontSize: '0.85rem',
                    fontWeight: 700,
                    color: 'var(--text-secondary)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px'
                }}>
                    Live Coaching
                </h3>
            </div>
            
            <div style={{
                flex: 1,
                overflowY: 'auto',
                padding: '1.5rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '1.25rem',
            }}>
                {coachingFeedback.length === 0 ? (
                    <div style={{
                        textAlign: 'center',
                        padding: '3rem 1rem',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        gap: '12px'
                    }}>
                        {/* Fixed size SVG so it doesn't cover the screen */}
                        <svg style={{ width: '40px', height: '40px', color: 'var(--bg-muted)' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                        </svg>
                        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                            Coaching insights will appear here after each answer.
                        </p>
                    </div>
                ) : (
                    [...coachingFeedback].reverse().map((fb, idx) => (
                        <div key={idx} style={{
                            background: 'var(--bg-elevated)',
                            borderRadius: '12px',
                            padding: '1.25rem',
                            border: '1px solid var(--bg-border)',
                            boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                            animation: 'fadeInUp 0.3s ease',
                        }}>
                            {/* Score preview */}
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                                    Answer {fb.answer_index + 1}
                                </span>
                                <span style={{
                                    fontSize: '0.9rem',
                                    fontWeight: 800,
                                    color: fb.score_preview >= 8 ? 'var(--accent-emerald)' : fb.score_preview >= 6 ? 'var(--accent-amber)' : 'var(--accent-red)'
                                }}>
                                    {fb.score_preview}/10
                                </span>
                            </div>

                            {/* Feedback text */}
                            <p style={{ fontSize: '0.9rem', color: 'var(--text-primary)', lineHeight: 1.5, margin: '0 0 16px 0' }}>
                                {fb.feedback_text}
                            </p>

                            {/* Strengths */}
                            {fb.strengths?.length > 0 && (
                                <div style={{ marginBottom: '10px' }}>
                                    <p style={{ fontSize: '0.75rem', color: 'var(--accent-emerald)', fontWeight: 700, margin: '0 0 4px 0', textTransform: 'uppercase' }}>✓ Strengths</p>
                                    <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                        {fb.strengths.map((s, i) => (
                                            <li key={i} style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>• {s}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {/* Improvements */}
                            {fb.improvements?.length > 0 && (
                                <div>
                                    <p style={{ fontSize: '0.75rem', color: 'var(--accent-amber)', fontWeight: 700, margin: '0 0 4px 0', textTransform: 'uppercase' }}>⚑ Improve</p>
                                    <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                        {fb.improvements.map((s, i) => (
                                            <li key={i} style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>• {s}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};

export default CoachingSidebar;
