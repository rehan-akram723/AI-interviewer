import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import useAudioRecorder from "../../hooks/useAudioRecorder";

const WaveformVisualizer = () => (
    <div className="flex items-end justify-center gap-[4px] h-10 px-4">
        {[1, 0.5, 0.8, 0.3, 1, 0.6, 0.4, 0.9, 0.5, 0.7, 1, 0.4, 0.6, 0.8, 0.3].map((delay, i) => (
            <motion.div
                key={i}
                animate={{ height: ["20%", "100%", "20%"] }}
                transition={{ duration: 1, repeat: Infinity, ease: "easeInOut", delay: delay * 0.4 }}
                className="w-1.5 rounded-t-sm bg-accent-red shadow-[0_0_8px_rgba(239,68,68,0.6)]"
            />
        ))}
    </div>
);

const ThinkingDots = () => (
    <div className="flex items-center gap-1.5">
        {[0, 0.2, 0.4].map((delay, i) => (
            <motion.span
                key={i}
                animate={{ scale: [1, 1.5, 1], opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 1, repeat: Infinity, ease: "easeInOut", delay }}
                className="w-2.5 h-2.5 rounded-full bg-accent-blue shadow-[0_0_8px_rgba(59,130,246,0.6)]"
            />
        ))}
    </div>
);

const AnswerInput = ({ isDemo = true, onSubmitAnswer, isSubmitting = false }) => {
    const [textAnswer, setTextAnswer] = useState("");
    const [isFocused, setIsFocused] = useState(false);
    const { isRecording, audioBlob, permissionError, startRecording, stopRecording, clearAudioBlob } =
        useAudioRecorder(isDemo);

    useEffect(() => {
        if (audioBlob && !isDemo) {
            onSubmitAnswer({ audioBlob, textAnswer: "" });
            clearAudioBlob();
        }
    }, [audioBlob, isDemo, onSubmitAnswer, clearAudioBlob]);

    const handleTextSubmit = () => {
        const trimmed = textAnswer.trim();
        if (!trimmed) return;
        onSubmitAnswer({ audioBlob: null, textAnswer: trimmed });
        setTextAnswer("");
    };

    const handleKeyDown = (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleTextSubmit();
        }
    };

    if (isDemo) {
        return (
            <div className="flex flex-col gap-4 relative z-10 w-full mt-auto">
                <div className="flex items-center justify-between px-1">
                    <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">
                        Your Answer
                    </p>
                    {isFocused && !isSubmitting && (
                        <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-[10px] text-accent-blue uppercase tracking-widest font-bold">
                            Press Enter to submit
                        </motion.span>
                    )}
                </div>

                <div className="relative group">
                    {/* Glowing animated border effect */}
                    <div className={`absolute -inset-[2px] rounded-[18px] transition-opacity duration-500 ${isFocused && !isSubmitting ? 'opacity-100' : 'opacity-0'} pointer-events-none`}>
                        <div className="absolute inset-0 bg-gradient-to-r from-accent-blue to-accent-purple rounded-[18px] blur-sm opacity-50" />
                        <div className="absolute inset-0 bg-gradient-to-r from-accent-blue to-accent-purple rounded-[18px] opacity-20" />
                    </div>

                    <div className={`relative rounded-[16px] bg-slate-900/80 backdrop-blur-md overflow-hidden border border-slate-700/50 transition-all duration-300 ${isSubmitting ? "opacity-60 grayscale-[50%]" : ""}`}>
                        <textarea
                            className="w-full h-32 lg:h-40 bg-transparent text-slate-100 placeholder:text-slate-600 text-[15px] leading-relaxed resize-none p-5 focus:outline-none hide-scrollbar"
                            placeholder={isSubmitting ? "" : "Type your answer here..."}
                            value={textAnswer}
                            onChange={(e) => setTextAnswer(e.target.value)}
                            onKeyDown={handleKeyDown}
                            onFocus={() => setIsFocused(true)}
                            onBlur={() => setIsFocused(false)}
                            disabled={isSubmitting}
                        />

                        <AnimatePresence>
                            {isSubmitting && (
                                <motion.div 
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    exit={{ opacity: 0 }}
                                    className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-slate-950/80 backdrop-blur-md z-10"
                                >
                                    <ThinkingDots />
                                    <p className="text-xs uppercase tracking-widest text-slate-300 font-bold">
                                        Coaching AI is analyzing...
                                    </p>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </div>

                <div className="flex justify-end mt-2">
                    <button
                        onClick={handleTextSubmit}
                        disabled={!textAnswer.trim() || isSubmitting}
                        className={`group relative overflow-hidden px-8 py-3.5 rounded-full font-bold tracking-wide text-sm transition-all duration-300 flex items-center justify-center gap-3 ${
                            textAnswer.trim() && !isSubmitting
                                ? "bg-white text-slate-900 shadow-[0_0_30px_rgba(255,255,255,0.2)] hover:scale-105 hover:shadow-[0_0_40px_rgba(255,255,255,0.3)] cursor-pointer"
                                : "bg-slate-800/50 text-slate-500 cursor-not-allowed border border-slate-700/50"
                        }`}
                    >
                        {textAnswer.trim() && !isSubmitting && (
                            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent -translate-x-full group-hover:animate-[shimmer_1.5s_infinite]" />
                        )}
                        <span className="relative z-10">Submit Answer</span>
                        {!isSubmitting && textAnswer.trim() && (
                            <span className="relative z-10 text-slate-500 font-normal">↵</span>
                        )}
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-6 items-center w-full mt-auto">
            {permissionError && (
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="px-5 py-4 rounded-xl bg-accent-red/10 border border-accent-red/30 text-accent-red text-sm w-full text-center font-medium">
                    {permissionError}
                </motion.div>
            )}
            
            <div className="flex flex-col items-center gap-6 w-full">
                <AnimatePresence mode="wait">
                    {isRecording && (
                        <motion.div 
                            initial={{ opacity: 0, height: 0 }} 
                            animate={{ opacity: 1, height: 'auto' }} 
                            exit={{ opacity: 0, height: 0 }}
                            className="w-full flex justify-center overflow-hidden"
                        >
                            <WaveformVisualizer />
                        </motion.div>
                    )}
                </AnimatePresence>

                <button
                    onClick={isRecording ? stopRecording : startRecording}
                    disabled={isSubmitting}
                    className={`group relative overflow-hidden flex items-center justify-center gap-3 px-10 py-5 rounded-full text-sm uppercase tracking-widest font-black transition-all duration-300 border-0 ${
                        isRecording
                            ? "bg-accent-red text-white hover:bg-red-600 shadow-[0_0_40px_rgba(239,68,68,0.4)] scale-105"
                            : isSubmitting
                            ? "bg-slate-800/50 text-slate-500 cursor-not-allowed border border-slate-700/50"
                            : "bg-white text-slate-900 cursor-pointer shadow-[0_0_30px_rgba(255,255,255,0.2)] hover:scale-105 hover:shadow-[0_0_50px_rgba(255,255,255,0.3)]"
                    }`}
                >
                    {isRecording ? (
                        <>
                            <div className="absolute inset-0 bg-accent-red animate-pulse opacity-50" />
                            <span className="relative z-10 w-3 h-3 rounded-sm bg-white inline-block shadow-sm" />
                            <span className="relative z-10">Stop & Submit</span>
                        </>
                    ) : isSubmitting ? (
                        <><ThinkingDots /><span className="ml-2 text-slate-400">Analyzing...</span></>
                    ) : (
                        <>
                            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent -translate-x-full group-hover:animate-[shimmer_1.5s_infinite]" />
                            <svg className="relative z-10" width="20" height="20" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M7 4a3 3 0 016 0v4a3 3 0 01-6 0V4zm-1 4a4 4 0 008 0V4a4 4 0 00-8 0v4z" />
                                <path d="M3.5 9a1 1 0 00-1 1 7.5 7.5 0 0015 0 1 1 0 00-2 0 5.5 5.5 0 01-11 0 1 1 0 00-1-1z" />
                            </svg>
                            <span className="relative z-10">Start Recording</span>
                        </>
                    )}
                </button>
                
                <AnimatePresence>
                    {isRecording && (
                        <motion.p 
                            initial={{ opacity: 0 }} 
                            animate={{ opacity: 1 }} 
                            exit={{ opacity: 0 }}
                            className="text-accent-red text-[11px] uppercase tracking-widest font-bold m-0"
                        >
                            <motion.span animate={{ opacity: [1, 0.3, 1] }} transition={{ duration: 1.5, repeat: Infinity }}>
                                Recording in progress - speak clearly
                            </motion.span>
                        </motion.p>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
};

export default AnswerInput;
