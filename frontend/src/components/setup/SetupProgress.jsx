import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useSession } from '../../context/SessionContext';
import { motion, AnimatePresence } from 'framer-motion';

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

        let consecutiveErrors = 0;
        const MAX_ERRORS = 5;

        const interval = setInterval(async () => {
            try {
                const res = await axios.get(`http://localhost:8000/api/sessions/${sessionId}/status`);
                const data = res.data;

                // Reset error counter on success
                consecutiveErrors = 0;

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
                if (data.status === 'completed') {
                    clearInterval(interval);
                    setCompletedSteps(STEPS.map(s => s.key));
                    setTimeout(() => setCurrentPhase('report'), 1200);
                }
                if (data.status === 'error') {
                    clearInterval(interval);
                    setError(data.error || 'An unexpected error occurred during setup.');
                }
            } catch (err) {
                consecutiveErrors += 1;
                const detail = err.response?.data?.message || err.response?.data?.detail || err.message;
                console.warn(`[SetupProgress] Poll error #${consecutiveErrors}:`, detail);

                // Only give up after several consecutive failures
                if (consecutiveErrors >= MAX_ERRORS) {
                    setError(`Connection lost after ${MAX_ERRORS} attempts. ${detail || 'Is the backend running?'}`);
                    clearInterval(interval);
                }
            }
        }, 1200);

        return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [sessionId]);

    const progressPct = status === 'ready' || status === 'completed'
        ? 100
        : Math.max(8, (completedSteps.length / STEPS.length) * 90);

    return (
        <div className="h-full flex items-center justify-center p-8 relative">
            {/* Glowing orb background */}
            <motion.div 
                animate={{ scale: [1, 1.2, 1], opacity: [0.3, 0.5, 0.3] }}
                transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-accent-blue/10 rounded-full blur-[100px] pointer-events-none" 
            />

            <motion.div 
                initial={{ opacity: 0, scale: 0.95, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                className="w-full max-w-lg glass-panel rounded-[2rem] p-10 flex flex-col gap-8 relative z-10"
            >
                {/* Header */}
                <div className="text-center flex flex-col items-center">
                    {error ? (
                        <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} className="w-16 h-16 rounded-full bg-accent-red/10 flex items-center justify-center mb-4">
                            <svg width="32" height="32" fill="none" stroke="var(--accent-red)" strokeWidth="2" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </motion.div>
                    ) : (
                        <div className="relative w-16 h-16 mb-4">
                            <motion.svg 
                                animate={{ rotate: 360 }} 
                                transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
                                className="w-full h-full text-accent-blue opacity-20" 
                                viewBox="0 0 100 100"
                            >
                                <circle cx="50" cy="50" r="48" fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray="20 10" />
                            </motion.svg>
                            <div className="absolute inset-0 flex items-center justify-center">
                                <motion.svg 
                                    animate={{ scale: [1, 1.1, 1] }} 
                                    transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                                    width="28" height="28" fill="none" stroke="var(--accent-blue)" strokeWidth="2" viewBox="0 0 24 24"
                                >
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                                </motion.svg>
                            </div>
                        </div>
                    )}
                    <h2 className="text-2xl font-extrabold tracking-tight text-white mb-2">
                        {error ? 'Setup Failed' : (status === 'ready' || status === 'completed') ? 'Ready to Start!' : 'Preparing Interview'}
                    </h2>
                    <p className="text-sm text-slate-400">
                        {error ? 'See the error below.' : 'This takes about 20–60 seconds depending on your CV.'}
                    </p>
                </div>

                {!error && (
                    <div className="flex flex-col gap-8">
                        {/* Progress bar */}
                        <div className="relative w-full h-2 bg-slate-800/50 rounded-full overflow-hidden">
                            <motion.div 
                                className="absolute top-0 left-0 h-full bg-gradient-to-r from-accent-blue to-accent-purple"
                                initial={{ width: '8%' }}
                                animate={{ width: `${progressPct}%` }}
                                transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                            />
                        </div>

                        {/* Step list */}
                        <div className="flex flex-col gap-4">
                            {STEPS.map((s, index) => {
                                const done = completedSteps.includes(s.key);
                                const active = !done && lastStep.includes(s.key.replace('Agent', '').toLowerCase());
                                return (
                                    <motion.div 
                                        key={s.key} 
                                        initial={{ opacity: 0, x: -10 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ delay: index * 0.1 }}
                                        className="flex items-center gap-4"
                                    >
                                        <div className="relative w-6 h-6 flex items-center justify-center shrink-0">
                                            <AnimatePresence mode="wait">
                                                {done ? (
                                                    <motion.div 
                                                        key="done"
                                                        initial={{ scale: 0 }} animate={{ scale: 1 }} exit={{ scale: 0 }}
                                                        className="w-6 h-6 rounded-full bg-accent-emerald/20 flex items-center justify-center border border-accent-emerald/50"
                                                    >
                                                        <svg width="12" height="12" fill="none" stroke="var(--accent-emerald)" strokeWidth="3" viewBox="0 0 24 24">
                                                            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                                                        </svg>
                                                    </motion.div>
                                                ) : active ? (
                                                    <motion.div 
                                                        key="active"
                                                        initial={{ scale: 0 }} animate={{ scale: 1 }} exit={{ scale: 0 }}
                                                        className="w-5 h-5 rounded-full border-2 border-accent-blue border-t-transparent animate-spin"
                                                    />
                                                ) : (
                                                    <motion.div 
                                                        key="pending"
                                                        initial={{ scale: 0 }} animate={{ scale: 1 }} exit={{ scale: 0 }}
                                                        className="w-3 h-3 rounded-full bg-slate-700"
                                                    />
                                                )}
                                            </AnimatePresence>
                                        </div>
                                        <span className={`text-sm transition-colors duration-300 font-medium ${
                                            done ? 'text-slate-300' : active ? 'text-accent-blue font-bold tracking-tight' : 'text-slate-600'
                                        }`}>
                                            {s.label}
                                        </span>
                                    </motion.div>
                                );
                            })}
                        </div>

                        {/* Terminal log output */}
                        <div className="bg-slate-900/80 rounded-xl p-4 border border-slate-800/50 relative overflow-hidden">
                            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-accent-blue/50 to-transparent" />
                            <div className="text-[11px] font-mono text-slate-400 opacity-80 mb-2 uppercase tracking-widest">System Log</div>
                            <div className="text-xs font-mono text-accent-blue break-all">
                                {'>'} {lastStep}
                                <motion.span 
                                    animate={{ opacity: [1, 0] }} 
                                    transition={{ duration: 0.8, repeat: Infinity, ease: "linear" }}
                                >
                                    _
                                </motion.span>
                            </div>
                        </div>
                    </div>
                )}

                {error && (
                    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="p-4 bg-accent-red/10 border border-accent-red/30 rounded-xl text-accent-red text-sm font-medium">
                        {error}
                    </motion.div>
                )}
            </motion.div>
        </div>
    );
};

export default SetupProgress;
