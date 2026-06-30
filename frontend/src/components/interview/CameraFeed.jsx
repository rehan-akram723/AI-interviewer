import React from 'react';

const CameraFeed = ({ isDemo, cameraRef, coachingFeedback = [], difficultyMetrics = {} }) => {
    // Only show the latest 3 feedback items in the floating overlay
    const recentFeedback = coachingFeedback.slice(-3);

    return (
        <div style={{
            width: '100%',
            aspectRatio: '16/9',
            position: 'relative',
            borderRadius: '16px',
            overflow: 'hidden',
            background: '#000',
            border: '1px solid var(--bg-border)',
            boxShadow: '0 10px 40px rgba(0,0,0,0.4)',
        }}>
            {isDemo ? (
                // ── Demo Placeholder ──
                <div style={{
                    width: '100%',
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: 'var(--bg-elevated)',
                    border: '2px dashed var(--bg-muted)',
                }}>
                    {/* Fixed size SVG so it doesn't cover the screen */}
                    <svg style={{ width: '48px', height: '48px', color: 'var(--text-muted)' }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M3 8a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z" />
                    </svg>
                    <p style={{ marginTop: '12px', fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
                        Camera disabled in Demo Mode
                    </p>
                </div>
            ) : (
                // ── Production Camera ──
                <>
                    <video
                        ref={cameraRef}
                        autoPlay
                        muted
                        playsInline
                        style={{
                            width: '100%',
                            height: '100%',
                            objectFit: 'cover',
                            background: '#000'
                        }}
                    />
                    
                    {/* Floating Coaching Feedback Overlay */}
                    <div style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        pointerEvents: 'none',
                        padding: '1.5rem',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'flex-end',
                        alignItems: 'flex-start',
                        gap: '10px'
                    }}>
                        {recentFeedback.map((fb, idx) => (
                            <div key={idx} style={{
                                background: 'rgba(0, 0, 0, 0.65)',
                                backdropFilter: 'blur(8px)',
                                borderLeft: `4px solid ${fb.score_preview >= 8 ? '#10b981' : fb.score_preview >= 6 ? '#f59e0b' : '#ef4444'}`,
                                padding: '12px 16px',
                                borderRadius: '8px',
                                color: '#fff',
                                maxWidth: '80%',
                                animation: 'fadeInUp 0.3s ease forwards',
                            }}>
                                <div style={{ fontSize: '0.75rem', fontWeight: 600, opacity: 0.8, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>
                                    Live Insight
                                </div>
                                <div style={{ fontSize: '0.9rem', lineHeight: 1.4 }}>
                                    {fb.feedback_text}
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Difficulty Overlay (Top Right) */}
                    {difficultyMetrics && Object.keys(difficultyMetrics.difficultyDimensions || {}).length > 0 && (
                        <div style={{
                            position: 'absolute',
                            top: '1.5rem',
                            right: '1.5rem',
                            background: 'rgba(0, 0, 0, 0.5)',
                            backdropFilter: 'blur(10px)',
                            padding: '12px',
                            borderRadius: '10px',
                            border: '1px solid rgba(255,255,255,0.1)',
                            width: '200px'
                        }}>
                            <div style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '8px' }}>
                                Telemetry
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                {Object.entries(difficultyMetrics.difficultyDimensions).map(([dim, val]) => (
                                    <div key={dim} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                                        <span style={{ color: '#fff', textTransform: 'capitalize' }}>{dim}</span>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                            <div style={{ width: '40px', height: '4px', background: 'rgba(255,255,255,0.2)', borderRadius: '2px' }}>
                                                <div style={{ width: `${(val/5)*100}%`, height: '100%', background: '#3b82f6', borderRadius: '2px' }}></div>
                                            </div>
                                            <span style={{ color: 'var(--accent-blue)', fontWeight: 600, fontFamily: 'monospace' }}>{val}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </>
            )}
        </div>
    );
};

export default CameraFeed;
