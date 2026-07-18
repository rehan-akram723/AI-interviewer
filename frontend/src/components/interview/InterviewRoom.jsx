import React, { useState, useRef, useCallback, useEffect } from "react";
import useWebSocket from "../../hooks/useWebSocket";
import AnswerInput from "./AnswerInput";
import CameraFeed from "./CameraFeed";
import QuestionDisplay from "./QuestionDisplay";
import CoachingSidebar from "./CoachingSidebar";
import axios from "axios";
import { useSession } from "../../context/SessionContext";
import { motion, AnimatePresence } from "framer-motion";

const PHASE_LABELS = {
    icebreaker:       { label: "Icebreaker",   color: "rgba(20,184,166,0.12)",  text: "#10b981" },
    cv_deep_dive:     { label: "CV Deep Dive", color: "rgba(59,130,246,0.12)",  text: "#3b82f6" },
    dynamic_followup: { label: "Follow-up",    color: "rgba(168,85,247,0.12)",  text: "#8b5cf6" },
    closing:          { label: "Closing",      color: "rgba(156,163,175,0.12)", text: "#94a3b8" },
};

const DifficultyBar = ({ level }) => {
    const bars = [1, 2, 3, 4, 5];
    return (
        <div className="flex items-center gap-1.5">
            {bars.map(b => (
                <motion.div
                    key={b}
                    initial={{ scaleY: 0 }}
                    animate={{ scaleY: 1 }}
                    transition={{ delay: b * 0.1, type: "spring" }}
                    className={`h-[4px] w-5 rounded-full transition-colors duration-500 ${
                        b <= level ? "bg-accent-blue shadow-[0_0_8px_rgba(59,130,246,0.5)]" : "bg-slate-800"
                    }`}
                />
            ))}
        </div>
    );
};

const InterviewRoom = ({ sessionId, isDemo = true, sessionMeta = {} }) => {
    const { setCurrentPhase } = useSession();
    const [currentQuestion, setCurrentQuestion] = useState(null);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [submitError, setSubmitError] = useState(null);
    const cameraRef = useRef(null);

    const { isConnected, coachingFeedback, difficultyMetrics, connectionError, nextQuestion, isInterviewComplete } =
        useWebSocket(sessionId);

    // Immediately unlock and display next question when WS event arrives
    useEffect(() => {
        if (isInterviewComplete) {
            setCurrentPhase("report");
        } else if (nextQuestion && nextQuestion.asked_at !== currentQuestion?.asked_at) {
            setCurrentQuestion(nextQuestion);
            setIsSubmitting(false);  // Unlock input the moment the question arrives
        }
    }, [nextQuestion, isInterviewComplete, currentQuestion, setCurrentPhase]);

    // Fetch first question on mount
    useEffect(() => {
        if (!sessionId) return;
        const fetchInitialQuestion = async () => {
            try {
                const res = await axios.get(`http://localhost:8000/api/sessions/${sessionId}/question`);
                if (res.data.status === "completed") {
                    setCurrentPhase("report");
                } else {
                    setCurrentQuestion(res.data.question);
                }
            } catch (err) {
                console.error("[InterviewRoom] Failed to fetch initial question", err);
                setSubmitError("Failed to load the first question. Please try refreshing.");
            }
        };
        fetchInitialQuestion();
    }, [sessionId, setCurrentPhase]);

    const handleSubmitAnswer = useCallback(async ({ audioBlob, textAnswer }) => {
        if (isSubmitting || !currentQuestion) return;
        setIsSubmitting(true);
        setSubmitError(null);

        try {
            let audioBase64 = null;
            if (audioBlob) {
                audioBase64 = await new Promise((resolve, reject) => {
                    const reader = new FileReader();
                    reader.onloadend = () => resolve(reader.result.split(",")[1]);
                    reader.onerror = reject;
                    reader.readAsDataURL(audioBlob);
                });
            }

            const payload = {
                questionIndex: currentQuestion.index,
                text: textAnswer || "",
                audioBase64,
                facialData: null,
            };

            const res = await axios.post(
                `http://localhost:8000/api/sessions/${sessionId}/answer`,
                payload,
                { headers: { "Content-Type": "application/json" } }
            );

            // Status=processing means the async pipeline is running — WS will push next_question
            if (res.data.is_complete || res.data.status === "completed") {
                setCurrentPhase("report");
            } else if (res.data.next_question) {
                // Sync fallback (shouldn"t normally happen)
                setCurrentQuestion(res.data.next_question);
                setIsSubmitting(false);
            }
        } catch (err) {
            console.error("[InterviewRoom] Failed to submit answer:", err);
            setSubmitError("Failed to submit your answer. Please try again.");
            setIsSubmitting(false);
        }
    }, [sessionId, currentQuestion, isSubmitting, setCurrentPhase]);

    const phaseConfig = PHASE_LABELS[currentQuestion?.phase] || PHASE_LABELS.icebreaker;
    const questionNum = (currentQuestion?.index ?? 0) + 1;

    return (
        <div className="flex flex-col h-[calc(100vh-64px)] relative overflow-hidden">
            
            {/* Global dynamic background elements specific to Interview Room */}
            <motion.div 
                animate={{ rotate: 360, scale: [1, 1.1, 1] }} 
                transition={{ duration: 30, repeat: Infinity, ease: "linear" }}
                className="absolute -top-[20%] -right-[10%] w-[800px] h-[800px] bg-accent-purple/5 rounded-full blur-[150px] pointer-events-none -z-10"
            />
            <motion.div 
                animate={{ rotate: -360, scale: [1, 1.2, 1] }} 
                transition={{ duration: 40, repeat: Infinity, ease: "linear" }}
                className="absolute -bottom-[20%] -left-[10%] w-[600px] h-[600px] bg-accent-blue/10 rounded-full blur-[120px] pointer-events-none -z-10"
            />

            {/* -- Top Status Bar -- */}
            <motion.div 
                initial={{ y: -20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
                className="flex items-center justify-between px-8 py-4 border-b border-white/5 glass shrink-0 z-20"
            >
                <div className="flex items-center gap-4">
                    {/* Connection indicator */}
                    <div className="flex items-center gap-2.5 glass-panel px-3 py-1.5 rounded-full">
                        <motion.span 
                            animate={!isConnected ? { opacity: [1, 0.3, 1] } : {}}
                            transition={{ duration: 1, repeat: Infinity }}
                            className={`w-2 h-2 rounded-full inline-block ${isConnected ? "bg-accent-emerald shadow-[0_0_10px_rgba(16,185,129,0.8)]" : "bg-accent-red"}`} 
                        />
                        <span className="text-[10px] uppercase tracking-widest text-slate-300 font-bold">
                            {isConnected ? "Live Session" : "Reconnecting"}
                        </span>
                    </div>
                    {isDemo && (
                        <div className="px-3 py-1.5 text-[10px] font-bold bg-accent-amber/10 text-accent-amber border border-accent-amber/20 rounded-full tracking-widest uppercase">
                            Demo Mode
                        </div>
                    )}
                </div>

                {/* Right: question counter + difficulty */}
                <div className="flex items-center gap-6 glass-panel px-4 py-1.5 rounded-full">
                    <div className="flex items-center gap-3">
                        <span className="text-[10px] uppercase tracking-[0.15em] text-slate-400 font-bold">Difficulty</span>
                        <DifficultyBar level={difficultyMetrics.difficultyLevel || 2} />
                    </div>
                    <div className="w-px h-4 bg-slate-700/50" />
                    <div className="text-[10px] uppercase tracking-[0.1em] text-slate-400 font-bold flex items-center gap-1.5">
                        Question
                        <span className="text-white text-sm font-black bg-slate-800 px-2 py-0.5 rounded-md">
                            {questionNum}
                        </span>
                    </div>
                </div>
            </motion.div>

            {/* -- Main Content -- */}
            <div className="flex flex-1 overflow-hidden relative z-10">

                {/* -- Center: Question + Answer -- */}
                <div className="flex-1 flex flex-col overflow-y-auto p-6 lg:p-10 hide-scrollbar">
                    <motion.div 
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.6, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
                        className={`w-full mx-auto flex flex-col gap-6 relative ${isDemo ? "max-w-[800px]" : "max-w-[960px]"}`}
                    >
                        {/* Camera / Demo Info */}
                        <CameraFeed
                            isDemo={isDemo}
                            cameraRef={cameraRef}
                            coachingFeedback={coachingFeedback}
                            difficultyMetrics={difficultyMetrics}
                        />

                        {/* Question + Answer Card */}
                        <div className="glass-panel rounded-[2rem] p-8 lg:p-10 flex flex-col gap-8 shadow-2xl relative overflow-hidden group">
                            {/* Subtle internal glow on hover */}
                            <div className="absolute inset-0 bg-gradient-to-b from-white/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" />

                            <QuestionDisplay
                                currentQuestion={currentQuestion}
                                connectionError={connectionError}
                                submitError={submitError}
                                phaseConfig={phaseConfig}
                                isLoading={isSubmitting}
                                isSpeechEnabled={!isDemo}
                            />

                            {/* Fluid Divider */}
                            <div className="h-px w-full bg-gradient-to-r from-transparent via-slate-700/50 to-transparent relative">
                                {isSubmitting && (
                                    <motion.div 
                                        className="absolute top-0 left-0 h-full w-1/3 bg-gradient-to-r from-transparent via-accent-blue to-transparent"
                                        animate={{ x: ['-100%', '300%'] }}
                                        transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                                    />
                                )}
                            </div>

                            <AnswerInput
                                isDemo={isDemo}
                                onSubmitAnswer={handleSubmitAnswer}
                                isSubmitting={isSubmitting}
                            />
                        </div>

                    </motion.div>
                </div>

                {/* -- Right Sidebar (always visible) -- */}
                <motion.div 
                    initial={{ x: "100%", opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    transition={{ type: "spring", stiffness: 200, damping: 25 }}
                    className="w-[340px] xl:w-[380px] border-l border-white/5 bg-slate-900/40 backdrop-blur-xl flex flex-col shrink-0 shadow-[-20px_0_40px_rgba(0,0,0,0.2)] z-20"
                >
                    <CoachingSidebar
                        coachingFeedback={coachingFeedback}
                        isProcessing={isSubmitting}
                    />
                </motion.div>
            </div>
        </div>
    );
};

export default InterviewRoom;
