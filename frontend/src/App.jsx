// ─────────────────────────────────────────────────────────────────────────────
// frontend/src/App.jsx
// Root application — dark shell with state machine routing
// ─────────────────────────────────────────────────────────────────────────────

import React, { useState } from 'react';
import axios from 'axios';
import { useSession } from './context/SessionContext';
import SetupPage from './pages/SetupPage';
import SetupProgress from './components/setup/SetupProgress';
import InterviewRoom from './components/interview/InterviewRoom';
import ReportViewer from './components/report/ReportViewer';

const App = () => {
    const {
        sessionId,
        setSessionId,
        setCandidateId,
        currentPhase,
        setCurrentPhase,
        setInterviewLength,
        setInterviewMode,
    } = useSession();

    const [isStarting, setIsStarting] = useState(false);
    const [startError, setStartError] = useState(null);

    const handleStartSetup = async (formData, config) => {
        setIsStarting(true);
        setStartError(null);
        try {
            const data = new FormData();
            data.append('cvFile', formData.cvFile);
            data.append('jobDescription', formData.jobDescription || '');
            data.append('companyName', formData.companyName || '');
            data.append('motivationLetter', formData.motivationLetter || '');
            data.append('interviewLength', config.interviewLength || 'medium');
            data.append('interviewMode', config.interviewMode || 'mixed');

            const res = await axios.post('http://localhost:8000/api/sessions/setup', data, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });

            setSessionId(res.data.session_id);
            setCandidateId(res.data.candidate_id);
            setInterviewLength(config.interviewLength);
            setInterviewMode(config.interviewMode);
            setCurrentPhase('waiting');
        } catch (err) {
            console.error('Setup failed:', err);
            setStartError(err.response?.data?.detail || 'Failed to connect to server. Is the backend running?');
        } finally {
            setIsStarting(false);
        }
    };

    return (
        <div style={{ minHeight: '100vh', background: 'var(--bg-primary)', color: 'var(--text-primary)' }}>
            {/* ── Global Nav Bar ─────────────────────────────────────────────── */}
            <header style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0 2rem',
                height: '56px',
                borderBottom: '1px solid var(--bg-border)',
                background: 'var(--bg-surface)',
                position: 'sticky',
                top: 0,
                zIndex: 100,
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div style={{
                        width: 30, height: 30, borderRadius: 8,
                        background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        flexShrink: 0,
                    }}>
                        <svg width="16" height="16" fill="none" stroke="white" strokeWidth="2" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                        </svg>
                    </div>
                    <span style={{ fontWeight: 700, fontSize: '1rem', letterSpacing: '-0.3px' }}>
                        AI Interviewer
                    </span>
                </div>

                {/* Phase breadcrumb */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    {['Setup', 'Processing', 'Interview', 'Report'].map((label, i) => {
                        const phases = ['setup', 'waiting', 'interview', 'report'];
                        const currentIdx = phases.indexOf(currentPhase);
                        const isActive = phases[i] === currentPhase;
                        const isDone = i < currentIdx;
                        return (
                            <React.Fragment key={label}>
                                <span style={{
                                    color: isActive ? 'var(--accent-blue)' : isDone ? 'var(--text-secondary)' : 'var(--text-muted)',
                                    fontWeight: isActive ? 600 : 400,
                                }}>
                                    {isDone ? '✓ ' : ''}{label}
                                </span>
                                {i < 3 && <span style={{ color: 'var(--bg-muted)' }}>›</span>}
                            </React.Fragment>
                        );
                    })}
                </div>
            </header>

            {/* ── State Machine Router ───────────────────────────────────────── */}
            <main style={{ flex: 1 }}>
                {currentPhase === 'setup' && (
                    <SetupPage
                        onSubmit={handleStartSetup}
                        isLoading={isStarting}
                        error={startError}
                    />
                )}
                {currentPhase === 'waiting' && (
                    <SetupProgress />
                )}
                {currentPhase === 'interview' && (
                    <InterviewRoom sessionId={sessionId} isDemo={true} />
                )}
                {currentPhase === 'report' && (
                    <ReportViewer sessionId={sessionId} />
                )}
            </main>
        </div>
    );
};

export default App;
