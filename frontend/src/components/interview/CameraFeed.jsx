import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const CameraFeed = ({ isDemo, cameraRef, coachingFeedback = [], difficultyMetrics = {} }) => {
    // Only show the latest 3 feedback items in the floating overlay
    const recentFeedback = coachingFeedback.slice(-3);
    const streamRef = useRef(null);

    // Start camera in production mode
    useEffect(() => {
        if (isDemo) return;
        let cancelled = false;

        navigator.mediaDevices.getUserMedia({ video: true, audio: false })
            .then((stream) => {
                if (cancelled) { stream.getTracks().forEach(t => t.stop()); return; }
                streamRef.current = stream;
                // Attach to the <video> element once it exists
                if (cameraRef?.current) {
                    cameraRef.current.srcObject = stream;
                }
            })
            .catch((err) => {
                console.warn('[CameraFeed] Camera access denied or unavailable:', err);
            });

        return () => {
            cancelled = true;
            streamRef.current?.getTracks().forEach(t => t.stop());
        };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isDemo]);

    return (
        <div className="w-full aspect-video relative rounded-[2rem] overflow-hidden bg-slate-950 border border-white/10 shadow-[0_20px_50px_rgba(0,0,0,0.5)] group">
            
            {/* Ambient inner glow */}
            <div className="absolute inset-0 bg-gradient-to-t from-slate-900/80 via-transparent to-transparent pointer-events-none z-10" />

            {isDemo ? (
                // ── Demo Placeholder ──
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-900/50 backdrop-blur-md z-0">
                    <motion.div 
                        animate={{ scale: [1, 1.05, 1], opacity: [0.5, 0.8, 0.5] }}
                        transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                        className="absolute inset-0 bg-accent-blue/10 rounded-full blur-[100px]"
                    />
                    
                    <div className="relative flex flex-col items-center z-10">
                        <div className="w-20 h-20 rounded-full bg-slate-800/80 border border-slate-700/50 flex items-center justify-center mb-6 shadow-inner relative overflow-hidden">
                            <motion.div className="absolute inset-0 bg-gradient-to-r from-transparent via-slate-600/30 to-transparent w-[200%]" animate={{ x: ['-100%', '100%'] }} transition={{ duration: 3, repeat: Infinity, ease: 'linear' }} />
                            <svg className="w-8 h-8 text-slate-400 relative z-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M3 8a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z" />
                            </svg>
                        </div>
                        <div className="px-6 py-2 rounded-full glass border border-white/5 flex items-center gap-3">
                            <span className="w-2 h-2 rounded-full bg-accent-amber animate-pulse shadow-[0_0_8px_rgba(245,158,11,0.8)]" />
                            <span className="text-[11px] font-bold uppercase tracking-widest text-slate-300">
                                Camera disabled in Demo
                            </span>
                        </div>
                    </div>
                </div>
            ) : (
                // ── Production Camera ──
                <>
                    <video
                        ref={cameraRef}
                        autoPlay
                        muted
                        playsInline
                        className="w-full h-full object-cover bg-black absolute inset-0 z-0"
                    />
                    
                    {/* Floating Coaching Feedback Overlay */}
                    <div className="absolute inset-x-0 bottom-0 p-8 flex flex-col justify-end items-start gap-4 z-20 pointer-events-none">
                        <AnimatePresence>
                            {recentFeedback.map((fb, idx) => {
                                const color = fb.score_preview >= 8 ? 'emerald' : fb.score_preview >= 6 ? 'amber' : 'red';
                                const colorClasses = {
                                    emerald: 'border-accent-emerald bg-accent-emerald/10 shadow-[0_0_20px_rgba(16,185,129,0.15)] text-accent-emerald',
                                    amber: 'border-accent-amber bg-accent-amber/10 shadow-[0_0_20px_rgba(245,158,11,0.15)] text-accent-amber',
                                    red: 'border-accent-red bg-accent-red/10 shadow-[0_0_20px_rgba(239,68,68,0.15)] text-accent-red'
                                };
                                return (
                                    <motion.div 
                                        key={fb.answer_index ?? idx}
                                        initial={{ opacity: 0, x: -20, y: 10 }}
                                        animate={{ opacity: 1, x: 0, y: 0 }}
                                        exit={{ opacity: 0, x: -20 }}
                                        transition={{ type: "spring", stiffness: 300, damping: 25 }}
                                        className="bg-slate-950/80 backdrop-blur-xl border border-slate-800 rounded-2xl p-4 max-w-[80%] flex items-start gap-4 pointer-events-auto"
                                    >
                                        <div className={`w-1 shrink-0 rounded-full self-stretch ${color === 'emerald' ? 'bg-accent-emerald shadow-[0_0_8px_rgba(16,185,129,0.5)]' : color === 'amber' ? 'bg-accent-amber shadow-[0_0_8px_rgba(245,158,11,0.5)]' : 'bg-accent-red shadow-[0_0_8px_rgba(239,68,68,0.5)]'}`} />
                                        <div className="flex flex-col gap-1.5 py-1">
                                            <div className={`text-[10px] font-black uppercase tracking-[0.2em] ${colorClasses[color].split(' ')[3]}`}>
                                                Live Insight
                                            </div>
                                            <div className="text-sm font-medium text-slate-200 leading-relaxed drop-shadow-sm">
                                                {fb.feedback_text}
                                            </div>
                                        </div>
                                    </motion.div>
                                );
                            })}
                        </AnimatePresence>
                    </div>

                    {/* Difficulty Overlay (Top Right) */}
                    <AnimatePresence>
                        {difficultyMetrics && Object.keys(difficultyMetrics.difficultyDimensions || {}).length > 0 && (
                            <motion.div 
                                initial={{ opacity: 0, y: -20 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="absolute top-6 right-6 glass-panel backdrop-blur-xl p-4 rounded-2xl border border-white/10 w-[220px] z-20 transition-opacity duration-300 opacity-50 group-hover:opacity-100"
                            >
                                <div className="text-[10px] font-black tracking-[0.2em] text-slate-500 uppercase mb-4 flex items-center justify-between">
                                    Telemetry
                                    <span className="w-1.5 h-1.5 rounded-full bg-accent-blue animate-pulse" />
                                </div>
                                <div className="flex flex-col gap-3">
                                    {Object.entries(difficultyMetrics.difficultyDimensions).map(([dim, val]) => (
                                        <div key={dim} className="flex items-center justify-between gap-4">
                                            <span className="text-[11px] font-bold text-slate-300 capitalize tracking-wide truncate">{dim}</span>
                                            <div className="flex items-center gap-2 shrink-0">
                                                <div className="w-10 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                                                    <motion.div 
                                                        initial={{ width: 0 }}
                                                        animate={{ width: `${(val/5)*100}%` }}
                                                        transition={{ duration: 1, ease: "easeOut" }}
                                                        className="h-full bg-gradient-to-r from-accent-blue to-accent-purple rounded-full"
                                                    />
                                                </div>
                                                <span className="text-[10px] font-bold text-accent-blue font-mono w-3 text-right">{val}</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </>
            )}
        </div>
    );
};

export default CameraFeed;
