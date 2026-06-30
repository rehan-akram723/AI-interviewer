// ─────────────────────────────────────────────────────────────────────────────
// frontend/src/components/setup/SetupProgress.jsx
// Processing screen — polls backend status, animated progress
// ─────────────────────────────────────────────────────────────────────────────

import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useSession } from '../../context/SessionContext';

const STEPS = [
    { key: 'cvParserAgent',            label: 'Parsing CV & extracting skills' },
    { key: 'companyResearchAgent',     label: 'Researching company & role context' },
    { key: 'interviewPlannerAgent',    label: 'Designing your question roadmap' },
];

const SetupProgress = () => {
    const { sessionId, setCurrentPhase } = useSession();
    const [lastStep, setLastStep] = useState('Initialising…');
    const [status, setStatus] = useState('setting_up');
    const [error, setError] = useState(null);
    const [completedSteps, setCompletedSteps] = useState([]);

    useEffect(() => {
        if (!sessionId) return;

        const interval = setInterval(async () => {
            try {
                const res = await axios.get(`http://localhost:8000/api/sessions/${sessionId}/status`);
                const data = res.data;

                setStatus(data.status);

                if (data.last_step) {
                    setLastStep(data.last_step);
                    // Detect which STEPS completed from the log text
                    STEPS.forEach(s => {
                        if (data.last_step.includes(s.key) && !completedSteps.includes(s.key)) {
                            setCompletedSteps(prev => [...prev, s.key]);
                        }
                    });
                }

                if (data.status === 'ready') {
                    clearInterval(interval);
                    setCompletedSteps(STEPS.map(s => s.key));
                    setTimeout(() => setCurrentPhase('interview'), 1200);
                }
                if (data.status === 'error') {
                    clearInterval(interval);
                    setError(data.error || 'An unexpected error occurred during setup.');
                }
            } catch (err) {
                setError('Failed to connect to backend.');
                clearInterval(interval);
            }
        }, 1200);

        return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [sessionId]);

    const progressPct = status === 'ready'
        ? 100
        : Math.max(8, (completedSteps.length / STEPS.length) * 90);

    return (
        <div style={{
            minHeight: 'calc(100vh - 56px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '3rem 2rem',
            background: 'var(--bg-primary)',
        }}>
            <div style={{
                width: '100%',
                maxWidth: 480,
                background: 'var(--bg-elevated)',
                border: '1px solid var(--bg-border)',
                borderRadius: '18px',
                padding: '2.5rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '2rem',
                animation: 'fadeInUp 0.4s ease both',
            }}>
                {/* Header */}
                <div style={{ textAlign: 'center' }}>
                    {error ? (
                        <div style={{
                            width: 56, height: 56, borderRadius: '50%',
                            background: 'rgba(239,68,68,0.12)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            margin: '0 auto 1rem',
                        }}>
                            <svg width="26" height="26" fill="none" stroke="#ef4444" strokeWidth="2" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </div>
                    ) : (
                        <div style={{
                            width: 56, height: 56, borderRadius: '50%',
                            background: 'rgba(59,130,246,0.12)',
                            border: '2px solid rgba(59,130,246,0.3)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            margin: '0 auto 1rem',
                            animation: status !== 'ready' ? 'pulse-dot 2s ease infinite' : 'none',
                        }}>
                            <svg width="26" height="26" fill="none" stroke="var(--accent-blue)" strokeWidth="2" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                            </svg>
                        </div>
                    )}
                    <h2 style={{ margin: 0, fontSize: '1.3rem', fontWeight: 700, letterSpacing: '-0.4px' }}>
                        {error ? 'Setup Failed' : status === 'ready' ? 'Ready to Start!' : 'Preparing Your Interview'}
                    </h2>
                    <p style={{ margin: '8px 0 0', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                        {error ? 'See the error below.' : 'This takes about 20–60 seconds depending on your CV.'}
                    </p>
                </div>

                {!error && (
                    <>
                        {/* Progress bar */}
                        <div>
                            <div style={{
                                width: '100%', height: '6px',
                                background: 'var(--bg-surface)',
                                borderRadius: '99px',
                                overflow: 'hidden',
                            }}>
                                <div style={{
                                    width: `${progressPct}%`,
                                    height: '100%',
                                    background: 'linear-gradient(90deg, #3b82f6, #8b5cf6)',
                                    borderRadius: '99px',
                                    transition: 'width 0.8s ease',
                                }}></div>
                            </div>
                        </div>

                        {/* Step list */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                            {STEPS.map((s) => {
                                const done = completedSteps.includes(s.key);
                                const active = !done && lastStep.includes(s.key.replace('Agent', '').toLowerCase());
                                return (
                                    <div key={s.key} style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '12px',
                                        padding: '10px 14px',
                                        background: done ? 'rgba(16,185,129,0.07)' : active ? 'rgba(59,130,246,0.07)' : 'transparent',
                                        border: `1px solid ${done ? 'rgba(16,185,129,0.2)' : active ? 'rgba(59,130,246,0.2)' : 'transparent'}`,
                                        borderRadius: '9px',
                                        transition: 'all 0.3s',
                                    }}>
                                        <div style={{
                                            width: 22, height: 22, borderRadius: '50%', flexShrink: 0,
                                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                                            background: done ? '#10b981' : active ? 'rgba(59,130,246,0.2)' : 'var(--bg-surface)',
                                            border: `1.5px solid ${done ? '#10b981' : active ? 'var(--accent-blue)' : 'var(--bg-border)'}`,
                                        }}>
                                            {done ? (
                                                <svg width="12" height="12" fill="none" stroke="white" strokeWidth="2.5" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                                                </svg>
                                            ) : active ? (
                                                <div style={{
                                                    width: 8, height: 8, borderRadius: '50%',
                                                    background: 'var(--accent-blue)',
                                                    animation: 'pulse-dot 1.5s ease infinite',
                                                }}></div>
                                            ) : null}
                                        </div>
                                        <span style={{
                                            fontSize: '0.875rem',
                                            fontWeight: done || active ? 500 : 400,
                                            color: done ? 'var(--accent-emerald)' : active ? 'var(--text-primary)' : 'var(--text-muted)',
                                        }}>
                                            {s.label}
                                        </span>
                                    </div>
                                );
                            })}
                        </div>

                        {/* Current operation text */}
                        <div style={{
                            padding: '10px 14px',
                            background: 'var(--bg-surface)',
                            borderRadius: '8px',
                            fontSize: '0.8125rem',
                            color: 'var(--text-muted)',
                            fontFamily: 'monospace',
                            wordBreak: 'break-all',
                        }}>
                            {lastStep}
                        </div>
                    </>
                )}

                {error && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        <div style={{
                            padding: '0.875rem 1rem',
                            background: 'rgba(239,68,68,0.07)',
                            border: '1px solid rgba(239,68,68,0.25)',
                            borderRadius: '9px',
                            fontSize: '0.875rem',
                            color: '#fca5a5',
                            lineHeight: 1.6,
                        }}>
                            {error}
                        </div>
                        <button
                            onClick={() => window.location.reload()}
                            style={{
                                padding: '0.75rem',
                                background: 'var(--bg-elevated)',
                                border: '1px solid var(--bg-border)',
                                borderRadius: '9px',
                                color: 'var(--text-primary)',
                                fontFamily: 'inherit',
                                fontSize: '0.9rem',
                                cursor: 'pointer',
                                fontWeight: 500,
                            }}>
                            ← Start Over
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
};

export default SetupProgress;
