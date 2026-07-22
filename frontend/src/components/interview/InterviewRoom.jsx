// ─────────────────────────────────────────────────────────────────────────────
// frontend/src/components/interview/InterviewRoom.jsx
//
// Fullscreen immersive interview room.
// Camera fills the entire viewport; UI panels float as glass overlays.
//
// Layout:
//   ┌──────────────────────────────────────────────────────────┐
//   │  [Insights top-left]              [Coach AI top-right]   │
//   │                                                          │
//   │              CAMERA (full viewport)                      │
//   │                                                          │
//   │  ┌─────────────── Bottom overlay ──────────────────────┐ │
//   │  │  Phase pill  ·  Question text                       │ │
//   │  │  [● Rec / ■ Stop & Submit]   Progress: 3/6          │ │
//   │  └────────────────────────────────────────────────────-┘ │
//   └──────────────────────────────────────────────────────────┘
// ─────────────────────────────────────────────────────────────────────────────

import React, { useState, useRef, useCallback, useEffect } from "react";
import useWebSocket from "../../hooks/useWebSocket";
import useAudioRecorder from "../../hooks/useAudioRecorder";
import CameraFeed from "./CameraFeed";
import axios from "axios";
import { useSession } from "../../context/SessionContext";
import { motion, AnimatePresence } from "framer-motion";

// ── Phase config ───────────────────────────────────────────────────────────────
const PHASE_CONFIG = {
    icebreaker:       { label: "Icebreaker",   color: "#34d399", bg: "rgba(52,211,153,0.15)"  },
    cv_deep_dive:     { label: "CV Deep Dive", color: "#4f8ef7", bg: "rgba(79,142,247,0.15)"  },
    dynamic_followup: { label: "Follow-up",    color: "#a78bfa", bg: "rgba(167,139,250,0.15)" },
    closing:          { label: "Closing",      color: "#94a3b8", bg: "rgba(148,163,184,0.12)" },
};

// ── Waveform bars ──────────────────────────────────────────────────────────────
const Waveform = () => (
    <div className="flex items-end gap-[3px] h-5">
        {[0.4, 0.7, 1, 0.6, 0.9, 0.5, 0.8, 0.4, 1, 0.6, 0.5, 0.8].map((d, i) => (
            <div
                key={i}
                className="wavebar bg-red-400"
                style={{ height: "100%", animationDelay: `${i * 0.07}s`, opacity: 0.6 + d * 0.4 }}
            />
        ))}
    </div>
);

// ── Insights panel (top-left) ──────────────────────────────────────────────────
const InsightsPanel = ({ feedback }) => {
    if (!feedback) return null;

    const scores = feedback.dimension_scores || {};
    const dims = Object.entries(scores)
        .sort(([, a], [, b]) => Math.abs(5 - b) - Math.abs(5 - a))  // most interesting first
        .slice(0, 2);

    if (dims.length === 0) return null;

    const scoreColor = (s) => s >= 8 ? "#34d399" : s >= 6 ? "#fbbf24" : "#f87171";
    const scoreLabel = (s) => s >= 8 ? "Strong" : s >= 6 ? "Good" : "Needs work";

    return (
        <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ type: "spring", stiffness: 300, damping: 28 }}
            className="glass-heavy rounded-2xl p-4 w-56 flex flex-col gap-3"
        >
            <p className="text-[9px] font-black uppercase tracking-[0.18em] text-blue-400/70">
                Previous Answer
            </p>
            {dims.map(([dim, val]) => (
                <div key={dim} className="flex flex-col gap-1.5">
                    <div className="flex items-center justify-between">
                        <span className="text-[11px] text-slate-300 capitalize font-medium">
                            {dim}
                        </span>
                        <span className="text-[11px] font-bold" style={{ color: scoreColor(val) }}>
                            {val}/10
                        </span>
                    </div>
                    <div className="h-1 rounded-full bg-white/10 overflow-hidden">
                        <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${val * 10}%` }}
                            transition={{ duration: 0.8, ease: "easeOut" }}
                            className="h-full rounded-full"
                            style={{ background: scoreColor(val) }}
                        />
                    </div>
                    <p className="text-[9px]" style={{ color: scoreColor(val) }}>
                        {scoreLabel(val)}
                    </p>
                </div>
            ))}
        </motion.div>
    );
};

// ── Coach panel (top-right) ────────────────────────────────────────────────────
const CoachPanel = ({ feedback, isOpen, onToggle }) => {
    const latest = feedback?.[feedback.length - 1];

    return (
        <div className="flex flex-col items-end gap-2">
            <button
                onClick={onToggle}
                className="flex items-center gap-2 glass-heavy rounded-full px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest text-blue-300 hover:text-white transition-colors"
            >
                <div className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                Coach AI
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d={isOpen ? "M5 15l7-7 7 7" : "M19 9l-7 7-7-7"} />
                </svg>
            </button>
            <AnimatePresence>
                {isOpen && latest && (
                    <motion.div
                        initial={{ opacity: 0, y: -10, scale: 0.96 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: -10, scale: 0.96 }}
                        transition={{ type: "spring", stiffness: 350, damping: 28 }}
                        className="glass-heavy rounded-2xl p-4 w-64 flex flex-col gap-3"
                    >
                        <div className="flex items-center gap-2">
                            <div className="w-6 h-6 rounded-lg bg-blue-500/20 flex items-center justify-center shrink-0">
                                <svg width="12" height="12" fill="none" stroke="#4f8ef7" strokeWidth="2" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                                </svg>
                            </div>
                            <p className="text-[10px] font-bold uppercase tracking-wider text-blue-300">
                                Live Coaching
                            </p>
                            {latest.score_preview != null && (
                                <span className="ml-auto text-xs font-black text-white">
                                    {latest.score_preview}/10
                                </span>
                            )}
                        </div>
                        <p className="text-[12px] text-slate-200 leading-relaxed">
                            {latest.feedback_text}
                        </p>
                        {latest.strengths?.length > 0 && (
                            <div>
                                <p className="text-[9px] font-bold uppercase tracking-widest text-emerald-400 mb-1">
                                    Strengths
                                </p>
                                {latest.strengths.map((s, i) => (
                                    <p key={i} className="text-[11px] text-slate-300 flex items-start gap-1.5">
                                        <span className="text-emerald-400 mt-0.5">✓</span>{s}
                                    </p>
                                ))}
                            </div>
                        )}
                        {latest.improvements?.length > 0 && (
                            <div>
                                <p className="text-[9px] font-bold uppercase tracking-widest text-amber-400 mb-1">
                                    Improve
                                </p>
                                {latest.improvements.map((s, i) => (
                                    <p key={i} className="text-[11px] text-slate-300 flex items-start gap-1.5">
                                        <span className="text-amber-400 mt-0.5">→</span>{s}
                                    </p>
                                ))}
                            </div>
                        )}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

// ── Main InterviewRoom ─────────────────────────────────────────────────────────
const InterviewRoom = ({ sessionId, isDemo = true }) => {
    const { setCurrentPhase } = useSession();
    const [currentQuestion, setCurrentQuestion] = useState(null);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [submitError, setSubmitError] = useState(null);
    const [coachOpen, setCoachOpen] = useState(false);
    const [questionPlanLength, setQuestionPlanLength] = useState(null);
    const cameraRef = useRef(null);

    const {
        isConnected, coachingFeedback, difficultyMetrics,
        connectionError, nextQuestion, isInterviewComplete,
    } = useWebSocket(sessionId);

    const {
        isRecording, audioBlob, permissionError, startRecording, stopRecording, clearAudioBlob,
    } = useAudioRecorder(isDemo);

    // Update current question when WS pushes a new one
    useEffect(() => {
        if (isInterviewComplete) {
            setCurrentPhase("report");
        } else if (nextQuestion) {
            // Use index as primary key; fall back to asked_at if available
            const isNew = nextQuestion.index !== currentQuestion?.index ||
                          nextQuestion.asked_at !== currentQuestion?.asked_at;
            if (isNew) {
                setCurrentQuestion(nextQuestion);
                setIsSubmitting(false);
                setCoachOpen(false);
            }
        }
    }, [nextQuestion, isInterviewComplete, currentQuestion, setCurrentPhase]);


    // Fetch first question on mount
    useEffect(() => {
        if (!sessionId) return;
        const fetchInitial = async () => {
            try {
                // Fetch question plan length from status
                const statusRes = await axios.get(`http://localhost:8000/api/sessions/${sessionId}/status`);
                if (statusRes.data.question_plan_length) {
                    setQuestionPlanLength(statusRes.data.question_plan_length);
                }

                // Fetch (or deliver) the first question via the /question endpoint
                const qRes = await axios.get(`http://localhost:8000/api/sessions/${sessionId}/question`);
                if (qRes.data.question) {
                    setCurrentQuestion(qRes.data.question);
                }
                if (qRes.data.status === "completed") {
                    setCurrentPhase("report");
                }
            } catch (err) {
                console.error("[InterviewRoom] Failed to fetch initial question:", err.response?.data || err.message);
            }
        };
        fetchInitial();
    }, [sessionId, setCurrentPhase]);

    // Auto-submit when audio recording stops
    useEffect(() => {
        if (audioBlob && !isDemo) {
            handleSubmitAnswer({ audioBlob, textAnswer: "" });
            clearAudioBlob();
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [audioBlob, isDemo]);

    // Open coach panel automatically when new feedback arrives
    useEffect(() => {
        if (coachingFeedback?.length > 0) {
            setCoachOpen(true);
        }
    }, [coachingFeedback]);

    const handleSubmitAnswer = useCallback(async ({ audioBlob: blob, textAnswer }) => {
        if (!currentQuestion || isSubmitting) return;
        setIsSubmitting(true);
        setSubmitError(null);

        try {
            let audioBase64 = null;
            if (blob) {
                const buffer = await blob.arrayBuffer();
                const bytes = new Uint8Array(buffer);
                let bin = "";
                bytes.forEach(b => bin += String.fromCharCode(b));
                audioBase64 = btoa(bin);
            }

            const facialData = cameraRef.current?.captureFrame?.() ?? null;
            const payload = {
                questionIndex: currentQuestion.index,
                text: textAnswer || "",
                audioBase64,
                facialData,
                durationSeconds: 0,
            };
            await axios.post(`http://localhost:8000/api/sessions/${sessionId}/answer`, payload);
        } catch (err) {
            setSubmitError(err.response?.data?.detail || "Failed to submit answer.");
            setIsSubmitting(false);
        }
    }, [currentQuestion, isSubmitting, sessionId]);

    const phaseConf = PHASE_CONFIG[currentQuestion?.phase] ?? PHASE_CONFIG.icebreaker;
    const questionNumber = currentQuestion ? (currentQuestion.index + 1) : 0;
    const prevFeedback = coachingFeedback?.length > 0 ? coachingFeedback[coachingFeedback.length - 1] : null;

    return (
        <div className="fixed inset-0 bg-black overflow-hidden">
            {/* ── CAMERA: fullscreen background ─────────────────────────────── */}
            <CameraFeed ref={cameraRef} isDemo={isDemo} fullscreen />

            {/* ── Dark vignette overlay ─────────────────────────────────────── */}
            <div className="absolute inset-0 bg-gradient-to-b from-black/50 via-transparent to-black/80 pointer-events-none" />
            <div className="absolute inset-0 bg-gradient-to-r from-black/30 via-transparent to-black/30 pointer-events-none" />

            {/* ── TOP ROW: Insights (left) + connection + coach (right) ──────── */}
            <div className="absolute top-0 left-0 right-0 flex items-start justify-between p-5 z-20">
                {/* Left: Live Insights from prev answer */}
                <AnimatePresence>
                    {prevFeedback && (
                        <InsightsPanel feedback={prevFeedback} />
                    )}
                </AnimatePresence>

                {/* Right: connection badge + Coach panel */}
                <div className="flex flex-col items-end gap-3">
                    {/* Connection indicator */}
                    <div className={`flex items-center gap-1.5 glass-heavy rounded-full px-3 py-1.5 text-[9px] font-bold uppercase tracking-widest ${
                        isConnected ? "text-emerald-400" : "text-red-400"
                    }`}>
                        <div className={`w-1.5 h-1.5 rounded-full ${isConnected ? "bg-emerald-400 animate-pulse" : "bg-red-400"}`} />
                        {isConnected ? "Live" : "Reconnecting…"}
                    </div>

                    {/* Difficulty */}
                    {difficultyMetrics?.difficultyLevel > 0 && (
                        <div className="glass-heavy rounded-full px-3 py-1.5 flex items-center gap-2">
                            <span className="text-[9px] font-bold uppercase tracking-widest text-slate-400">Difficulty</span>
                            <div className="flex gap-0.5">
                                {[1,2,3,4,5].map(b => (
                                    <div key={b} className={`w-4 h-1 rounded-full transition-all duration-500 ${
                                        b <= difficultyMetrics.difficultyLevel ? "bg-blue-400 shadow-[0_0_6px_rgba(79,142,247,0.6)]" : "bg-white/10"
                                    }`} />
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Coach AI panel */}
                    <CoachPanel
                        feedback={coachingFeedback}
                        isOpen={coachOpen}
                        onToggle={() => setCoachOpen(o => !o)}
                    />
                </div>
            </div>

            {/* ── BOTTOM OVERLAY: Question + Controls ───────────────────────── */}
            <div className="absolute bottom-0 left-0 right-0 z-20 p-5">
                <motion.div
                    layout
                    className="glass-heavy rounded-3xl p-5 flex flex-col gap-4 max-w-4xl mx-auto"
                    style={{ boxShadow: "0 -8px 64px rgba(0,0,0,0.6), 0 8px 32px rgba(0,0,0,0.4)" }}
                >
                    {/* Question section */}
                    <div className="flex items-start gap-4">
                        {/* Phase pill + number */}
                        <div className="shrink-0 mt-0.5 flex flex-col items-center gap-2">
                            <div
                                className="rounded-full px-2.5 py-1 text-[9px] font-black uppercase tracking-[0.18em]"
                                style={{ background: phaseConf.bg, color: phaseConf.color }}
                            >
                                {phaseConf.label}
                            </div>
                            {questionPlanLength && (
                                <span className="text-[9px] text-slate-500 font-bold">
                                    {questionNumber}/{questionPlanLength}
                                </span>
                            )}
                        </div>

                        {/* Question text */}
                        <AnimatePresence mode="wait">
                            <motion.p
                                key={currentQuestion?.asked_at || "loading"}
                                initial={{ opacity: 0, y: 10, filter: "blur(4px)" }}
                                animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                                exit={{ opacity: 0, y: -8, filter: "blur(4px)" }}
                                transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
                                className="text-[15px] text-white font-medium leading-relaxed"
                            >
                                {currentQuestion
                                    ? currentQuestion.text
                                    : isDemo
                                        ? "Tell me about yourself and what brought you to this role."
                                        : "Waiting for your first question…"}
                            </motion.p>
                        </AnimatePresence>
                    </div>

                    {/* Controls row */}
                    <div className="flex items-center justify-between gap-4">
                        {/* Left: errors / waveform */}
                        <div className="flex items-center gap-3">
                            {(permissionError || submitError || connectionError) && (
                                <p className="text-[11px] text-red-400 font-medium">
                                    {permissionError || submitError || connectionError}
                                </p>
                            )}
                            {isRecording && <Waveform />}
                            {isSubmitting && !isRecording && (
                                <div className="flex items-center gap-2 text-[11px] text-blue-300 font-medium">
                                    <svg className="animate-spin" width="14" height="14" fill="none" viewBox="0 0 24 24">
                                        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2.5" className="opacity-25" />
                                        <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" className="opacity-75" />
                                    </svg>
                                    Analysing…
                                </div>
                            )}
                        </div>

                        {/* Right: demo text input OR production record button */}
                        {isDemo ? (
                            <DemoTextInput onSubmit={(text) => handleSubmitAnswer({ audioBlob: null, textAnswer: text })} isSubmitting={isSubmitting} />
                        ) : (
                            <RecordButton
                                isRecording={isRecording}
                                isSubmitting={isSubmitting}
                                onStart={startRecording}
                                onStop={stopRecording}
                            />
                        )}
                    </div>
                </motion.div>
            </div>

            {/* ── Error / disconnection banner ───────────────────────────────── */}
            <AnimatePresence>
                {connectionError && (
                    <motion.div
                        initial={{ opacity: 0, y: -20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        className="absolute top-20 left-1/2 -translate-x-1/2 z-30 glass-heavy rounded-xl px-6 py-3 flex items-center gap-3 border border-red-500/30"
                    >
                        <div className="w-2 h-2 rounded-full bg-red-400 animate-pulse" />
                        <p className="text-[12px] text-red-300 font-medium">{connectionError}</p>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

// ── Demo text input ────────────────────────────────────────────────────────────
const DemoTextInput = ({ onSubmit, isSubmitting }) => {
    const [text, setText] = useState("");
    const handleSubmit = () => {
        const t = text.trim();
        if (!t || isSubmitting) return;
        onSubmit(t);
        setText("");
    };
    return (
        <div className="flex items-center gap-2 flex-1 max-w-md">
            <input
                className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-[13px] text-white placeholder:text-slate-600 focus:outline-none focus:border-blue-500/50 transition-colors"
                placeholder="Type your answer…"
                value={text}
                onChange={e => setText(e.target.value)}
                onKeyDown={e => e.key === "Enter" && !e.shiftKey && handleSubmit()}
                disabled={isSubmitting}
            />
            <button
                onClick={handleSubmit}
                disabled={!text.trim() || isSubmitting}
                className="px-5 py-2.5 rounded-xl text-[12px] font-bold uppercase tracking-wider transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed bg-white text-slate-900 hover:scale-105"
            >
                Submit
            </button>
        </div>
    );
};

// ── Record button ──────────────────────────────────────────────────────────────
const RecordButton = ({ isRecording, isSubmitting, onStart, onStop }) => (
    <button
        onClick={isRecording ? onStop : onStart}
        disabled={isSubmitting}
        className={`relative flex items-center gap-2.5 px-7 py-3 rounded-full text-[12px] font-black uppercase tracking-widest transition-all duration-300 overflow-hidden disabled:opacity-40 disabled:cursor-not-allowed ${
            isRecording
                ? "bg-red-500 text-white record-pulse hover:bg-red-600"
                : "bg-white text-slate-900 hover:scale-105 hover:shadow-[0_0_30px_rgba(255,255,255,0.2)]"
        }`}
    >
        {!isRecording && (
            <div className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/30 to-transparent hover:animate-[shimmer_1.5s_infinite]" />
        )}
        {isRecording ? (
            <>
                <span className="w-3 h-3 rounded-sm bg-white inline-block" />
                Stop & Submit
            </>
        ) : (
            <>
                <svg width="16" height="16" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M7 4a3 3 0 016 0v4a3 3 0 01-6 0V4zm-1 4a4 4 0 008 0V4a4 4 0 00-8 0v4z" />
                    <path d="M3.5 9a1 1 0 00-1 1 7.5 7.5 0 0015 0 1 1 0 00-2 0 5.5 5.5 0 01-11 0 1 1 0 00-1-1z" />
                </svg>
                Start Recording
            </>
        )}
    </button>
);

export default InterviewRoom;
