import React from "react";
import { motion, AnimatePresence } from "framer-motion";

const ScoreChip = ({ score }) => {
    const color =
        score >= 8 ? "text-accent-emerald bg-accent-emerald/10 border-accent-emerald/30 shadow-[0_0_10px_rgba(16,185,129,0.3)]"
        : score >= 6 ? "text-accent-amber bg-accent-amber/10 border-accent-amber/30 shadow-[0_0_10px_rgba(245,158,11,0.3)]"
        : "text-accent-red bg-accent-red/10 border-accent-red/30 shadow-[0_0_10px_rgba(239,68,68,0.3)]";
    return (
        <span className={`text-[11px] font-black tracking-widest px-2.5 py-1 rounded-full border uppercase ${color}`}>
            {score} / 10
        </span>
    );
};

const ShimmerCard = () => (
    <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="glass-panel rounded-2xl p-5 flex flex-col gap-4 relative overflow-hidden"
    >
        <motion.div className="absolute inset-0 bg-gradient-to-r from-transparent via-slate-700/20 to-transparent w-[200%]" animate={{ x: ['-100%', '100%'] }} transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }} />
        <div className="flex items-center justify-between relative z-10">
            <div className="h-3 bg-slate-800 rounded w-20" />
            <div className="h-5 bg-slate-800 rounded-full w-14" />
        </div>
        <div className="h-3 bg-slate-800/80 rounded w-full mt-2 relative z-10" />
        <div className="h-3 bg-slate-800/60 rounded w-4/5 relative z-10" />
        <div className="h-3 bg-slate-800/40 rounded w-3/5 relative z-10" />
    </motion.div>
);

const itemVariants = {
    hidden: { opacity: 0, x: 20 },
    visible: { opacity: 1, x: 0, transition: { type: "spring", stiffness: 300, damping: 25 } }
};

const CoachingCard = ({ fb, index }) => (
    <motion.div
        layout
        variants={itemVariants}
        initial="hidden"
        animate="visible"
        className="glass-panel rounded-[20px] p-5 flex flex-col gap-5 group hover:shadow-[0_8px_30px_rgba(0,0,0,0.4)] transition-shadow duration-300"
    >
        {/* Header */}
        <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500 group-hover:text-accent-blue transition-colors duration-300">
                Answer {(fb.answer_index ?? 0) + 1}
            </span>
            <ScoreChip score={fb.score_preview} />
        </div>

        {/* Feedback text */}
        <p className="text-sm text-slate-300 leading-relaxed font-medium m-0">
            {fb.feedback_text}
        </p>

        <div className="flex flex-col gap-4">
            {/* Strengths */}
            {fb.strengths?.length > 0 && (
                <div className="bg-accent-emerald/5 border border-accent-emerald/10 rounded-xl p-3.5">
                    <p className="text-[10px] font-black uppercase tracking-widest text-accent-emerald mb-2.5 m-0 flex items-center gap-2">
                        <span className="w-4 h-4 rounded-full bg-accent-emerald/20 flex items-center justify-center text-[8px]">✓</span>
                        Strengths
                    </p>
                    <ul className="m-0 p-0 list-none flex flex-col gap-2">
                        {fb.strengths.map((s, i) => (
                            <li key={i} className="text-xs text-slate-400 font-medium flex items-start gap-2">
                                <span className="text-accent-emerald mt-px shrink-0 opacity-50">✦</span>
                                <span>{s}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Improvements */}
            {fb.improvements?.length > 0 && (
                <div className="bg-accent-amber/5 border border-accent-amber/10 rounded-xl p-3.5">
                    <p className="text-[10px] font-black uppercase tracking-widest text-accent-amber mb-2.5 m-0 flex items-center gap-2">
                        <span className="w-4 h-4 rounded-full bg-accent-amber/20 flex items-center justify-center text-[8px]">!</span>
                        Improve
                    </p>
                    <ul className="m-0 p-0 list-none flex flex-col gap-2">
                        {fb.improvements.map((s, i) => (
                            <li key={i} className="text-xs text-slate-400 font-medium flex items-start gap-2">
                                <span className="text-accent-amber mt-px shrink-0 opacity-50">✦</span>
                                <span>{s}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    </motion.div>
);

const CoachingSidebar = ({ coachingFeedback = [], isProcessing = false }) => {
    return (
        <div className="h-full flex flex-col overflow-hidden">
            {/* Header */}
            <div className="px-6 py-5 border-b border-white/5 bg-slate-900/40 backdrop-blur-md shrink-0 z-10 relative">
                {/* Glowing edge effect */}
                <div className="absolute bottom-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-accent-purple/30 to-transparent" />
                
                <div className="flex items-center gap-3">
                    <div className="relative flex items-center justify-center">
                        <span className="w-2.5 h-2.5 rounded-full bg-accent-emerald shadow-[0_0_10px_rgba(16,185,129,0.8)] z-10" />
                        <span className="w-2.5 h-2.5 rounded-full bg-accent-emerald absolute animate-ping opacity-75" />
                    </div>
                    <h3 className="m-0 text-[11px] font-black uppercase tracking-[0.2em] text-slate-300">
                        Live AI Coaching
                    </h3>
                    {coachingFeedback.length > 0 && (
                        <motion.span 
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            className="ml-auto text-[10px] font-black text-slate-400 bg-slate-800 px-2.5 py-0.5 rounded-full border border-slate-700/50 shadow-inner"
                        >
                            {coachingFeedback.length}
                        </motion.span>
                    )}
                </div>
            </div>

            {/* Feed */}
            <div className="flex-1 overflow-y-auto px-5 py-6 flex flex-col gap-5 hide-scrollbar relative z-0">
                <AnimatePresence mode="popLayout">
                    {/* Shimmer card while processing */}
                    {isProcessing && <ShimmerCard key="processing" />}

                    {coachingFeedback.length === 0 && !isProcessing ? (
                        <motion.div 
                            key="empty"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="flex flex-col items-center justify-center h-full gap-5 py-20 text-center"
                        >
                            <div className="w-16 h-16 rounded-[20px] bg-slate-800/50 border border-slate-700/50 flex items-center justify-center text-2xl shadow-inner group-hover:scale-110 transition-transform duration-500">
                                🤖
                            </div>
                            <div className="space-y-1">
                                <p className="text-sm font-bold text-slate-300 m-0">Awaiting your answer</p>
                                <p className="text-xs text-slate-500 leading-relaxed max-w-[200px] m-0">
                                    Coaching insights will appear here in real-time.
                                </p>
                            </div>
                        </motion.div>
                    ) : (
                        [...coachingFeedback].reverse().map((fb, idx) => (
                            <CoachingCard key={fb.answer_index ?? idx} fb={fb} index={idx} />
                        ))
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
};

export default CoachingSidebar;
