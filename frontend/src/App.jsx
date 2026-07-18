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

import { AnimatePresence, motion } from 'framer-motion';

const pageVariants = {
    initial: { opacity: 0, y: 15, scale: 0.98 },
    animate: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } },
    exit: { opacity: 0, y: -15, scale: 0.98, transition: { duration: 0.3, ease: [0.16, 1, 0.3, 1] } }
};

const App = () => {
    const {
        sessionId,
        setSessionId,
        setCandidateId,
        appMode,
        setAppMode,
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
            data.append('appMode', config.appMode || 'live');

            const res = await axios.post('http://localhost:8000/api/sessions/setup', data, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });

            setSessionId(res.data.session_id);
            setCandidateId(res.data.candidate_id);
            setInterviewLength(config.interviewLength);
            setInterviewMode(config.interviewMode);
            setAppMode(config.appMode || 'demo');
            setCurrentPhase('waiting');
        } catch (err) {
            console.error('Setup failed:', err);
            setStartError(err.response?.data?.detail || 'Failed to connect to server. Is the backend running?');
        } finally {
            setIsStarting(false);
        }
    };

    return (
        <div className="min-h-screen bg-slate-950 text-slate-50 relative overflow-hidden font-sans selection:bg-accent-blue/30">
            {/* Global background glow */}
            <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-glow-radial from-accent-blue/10 via-transparent to-transparent opacity-50 blur-[120px] pointer-events-none" />
            <div className="absolute bottom-[-20%] right-[-10%] w-[60%] h-[60%] bg-glow-radial from-accent-purple/10 via-transparent to-transparent opacity-50 blur-[150px] pointer-events-none" />

            {/* ── Global Nav Bar ─────────────────────────────────────────────── */}
            <header className="relative flex items-center justify-between px-8 h-16 border-b border-white/5 bg-slate-900/50 backdrop-blur-md z-50">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-[10px] bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center shrink-0 shadow-lg shadow-accent-blue/20">
                        <svg width="18" height="18" fill="none" stroke="white" strokeWidth="2" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                        </svg>
                    </div>
                    <span className="font-extrabold text-[15px] tracking-[-0.03em] gradient-text drop-shadow-sm">
                        AI Interviewer
                    </span>
                </div>

                {/* Phase breadcrumb */}
                <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.15em] font-bold">
                    {['Setup', 'Processing', 'Interview', 'Report'].map((label, i) => {
                        const phases = ['setup', 'waiting', 'interview', 'report'];
                        const currentIdx = phases.indexOf(currentPhase);
                        const isActive = phases[i] === currentPhase;
                        const isDone = i < currentIdx;
                        return (
                            <React.Fragment key={label}>
                                <span className={`transition-colors duration-500 ${
                                    isActive ? 'text-accent-blue glow-text' : 
                                    isDone ? 'text-slate-400' : 
                                    'text-slate-600'
                                }`}>
                                    {isDone ? '✓ ' : ''}{label}
                                </span>
                                {i < 3 && <span className="text-slate-700/50">/</span>}
                            </React.Fragment>
                        );
                    })}
                </div>
            </header>

            {/* ── State Machine Router ───────────────────────────────────────── */}
            <main className="flex-1 relative z-10">
                <AnimatePresence mode="wait">
                    {currentPhase === 'setup' && (
                        <motion.div key="setup" variants={pageVariants} initial="initial" animate="animate" exit="exit" className="h-full">
                            <SetupPage
                                onSubmit={handleStartSetup}
                                isLoading={isStarting}
                                error={startError}
                            />
                        </motion.div>
                    )}
                    {currentPhase === 'waiting' && (
                        <motion.div key="waiting" variants={pageVariants} initial="initial" animate="animate" exit="exit" className="h-full">
                            <SetupProgress />
                        </motion.div>
                    )}
                    {currentPhase === 'interview' && (
                        <motion.div key="interview" variants={pageVariants} initial="initial" animate="animate" exit="exit" className="h-full">
                            <InterviewRoom sessionId={sessionId} isDemo={appMode !== 'production'} />
                        </motion.div>
                    )}
                    {currentPhase === 'report' && (
                        <motion.div key="report" variants={pageVariants} initial="initial" animate="animate" exit="exit" className="h-full">
                            <ReportViewer sessionId={sessionId} />
                        </motion.div>
                    )}
                </AnimatePresence>
            </main>
        </div>
    );
};

export default App;
