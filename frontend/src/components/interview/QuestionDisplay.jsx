import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const PHASE_ICONS = {
    icebreaker: '🌊',
    cv_deep_dive: '🔍',
    dynamic_followup: '↩️',
    closing: '🏁',
};

const textVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 200, damping: 20 } },
    exit: { opacity: 0, y: -20, transition: { duration: 0.2 } }
};

const skeletonVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { duration: 0.5 } },
    exit: { opacity: 0, transition: { duration: 0.3 } }
};

const QuestionDisplay = ({ currentQuestion, connectionError, submitError, phaseConfig, isLoading, isSpeechEnabled = true }) => {
    const questionKey = currentQuestion?.index ?? 'loading';
    const utteranceRef = useRef(null);

    // Speak the question using browser's Web Speech API when a new question arrives
    useEffect(() => {
        if (!isSpeechEnabled || !currentQuestion?.text || !window.speechSynthesis) return;

        // Cancel any in-progress speech
        window.speechSynthesis.cancel();

        const utterance = new SpeechSynthesisUtterance(currentQuestion.text);
        utterance.rate = 0.95;
        utterance.pitch = 1.0;
        utterance.volume = 1.0;

        // Try to pick a natural English voice if available
        const voices = window.speechSynthesis.getVoices();
        const preferred = voices.find(v =>
            v.lang.startsWith('en') && (v.name.includes('Google') || v.name.includes('Natural') || v.name.includes('Neural'))
        ) || voices.find(v => v.lang.startsWith('en')) || null;
        if (preferred) utterance.voice = preferred;

        utteranceRef.current = utterance;
        window.speechSynthesis.speak(utterance);

        return () => {
            window.speechSynthesis.cancel();
        };
    }, [currentQuestion?.index, isSpeechEnabled]);

    return (
        <div className="flex flex-col gap-6 relative">
            <AnimatePresence>
                {connectionError && (
                    <motion.div 
                        initial={{ opacity: 0, height: 0, marginBottom: 0 }}
                        animate={{ opacity: 1, height: 'auto', marginBottom: 8 }}
                        exit={{ opacity: 0, height: 0, marginBottom: 0 }}
                        className="px-4 py-3 rounded-xl bg-accent-red/10 border border-accent-red/25 text-accent-red text-sm flex items-center gap-2 overflow-hidden"
                    >
                        <span>⚠️</span> {connectionError}
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Phase badge + difficulty */}
            <div className="flex items-center justify-between flex-wrap gap-4 relative z-10">
                <div className="flex items-center gap-4">
                    <motion.span
                        key={phaseConfig.label}
                        initial={{ scale: 0.8, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        className="inline-flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.15em] px-4 py-2 rounded-full"
                        style={{
                            background: phaseConfig.color,
                            color: phaseConfig.text,
                            border: `1px solid ${phaseConfig.text}40`,
                            boxShadow: `0 0 20px ${phaseConfig.color}`
                        }}
                    >
                        <span className="text-sm">{PHASE_ICONS[currentQuestion?.phase] || '💬'}</span>
                        {phaseConfig.label}
                    </motion.span>
                    {currentQuestion && (
                        <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-xs uppercase tracking-widest text-slate-500 font-bold flex items-center gap-2">
                            Level <span className="text-slate-300 bg-slate-800/50 px-2 py-0.5 rounded-md">{currentQuestion.difficulty}/5</span>
                        </motion.span>
                    )}
                </div>

                <AnimatePresence>
                    {isLoading && (
                        <motion.span 
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: 20 }}
                            className="flex items-center gap-2 text-xs uppercase tracking-widest text-accent-blue font-bold ml-auto"
                        >
                            <span className="w-2 h-2 rounded-full bg-accent-blue animate-pulse inline-block shadow-[0_0_8px_rgba(59,130,246,0.8)]" />
                            Thinking...
                        </motion.span>
                    )}
                </AnimatePresence>
            </div>

            {/* Question text — spring animated transitions */}
            <div className="relative min-h-[140px]">
                <AnimatePresence mode="wait">
                    {currentQuestion ? (
                        <motion.div 
                            key={questionKey}
                            variants={textVariants}
                            initial="hidden"
                            animate="visible"
                            exit="exit"
                            className="flex flex-col gap-4 relative z-10"
                        >
                            <h2 className="text-3xl lg:text-4xl font-extrabold leading-[1.3] text-white tracking-tight drop-shadow-sm">
                                {currentQuestion.text}
                            </h2>
                            {currentQuestion.category && (
                                <p className="text-sm text-slate-400 font-medium tracking-wide uppercase">
                                    Category: <span className="text-accent-blue ml-1 drop-shadow-[0_0_10px_rgba(59,130,246,0.3)]">{currentQuestion.category}</span>
                                </p>
                            )}
                        </motion.div>
                    ) : (
                        <motion.div 
                            key="skeleton"
                            variants={skeletonVariants}
                            initial="hidden"
                            animate="visible"
                            exit="exit"
                            className="flex flex-col gap-4 mt-2 w-full absolute inset-0"
                        >
                            <div className="h-10 bg-slate-800/50 rounded-xl w-[90%] relative overflow-hidden">
                                <motion.div className="absolute inset-0 bg-gradient-to-r from-transparent via-slate-700/30 to-transparent w-[200%]" animate={{ x: ['-100%', '100%'] }} transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }} />
                            </div>
                            <div className="h-10 bg-slate-800/50 rounded-xl w-[75%] relative overflow-hidden">
                                <motion.div className="absolute inset-0 bg-gradient-to-r from-transparent via-slate-700/30 to-transparent w-[200%]" animate={{ x: ['-100%', '100%'] }} transition={{ duration: 1.5, repeat: Infinity, ease: 'linear', delay: 0.2 }} />
                            </div>
                            <div className="h-4 bg-slate-800/30 rounded-md w-[30%] mt-2 relative overflow-hidden">
                                <motion.div className="absolute inset-0 bg-gradient-to-r from-transparent via-slate-700/30 to-transparent w-[200%]" animate={{ x: ['-100%', '100%'] }} transition={{ duration: 1.5, repeat: Infinity, ease: 'linear', delay: 0.4 }} />
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            <AnimatePresence>
                {submitError && (
                    <motion.div 
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="px-5 py-4 rounded-[14px] bg-accent-red/10 border border-accent-red/30 text-accent-red text-sm font-medium overflow-hidden"
                    >
                        {submitError}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default QuestionDisplay;
