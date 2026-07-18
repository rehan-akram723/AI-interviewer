import React, { useState, useEffect, useRef, useCallback } from 'react';
import jsPDF from "jspdf";
import html2canvas from "html2canvas";
import { getReport, generateReport } from '../../services/api';
import useWebSocket from '../../hooks/useWebSocket';
import { motion, AnimatePresence } from 'framer-motion';

const DIMENSION_CONFIG = {
    communication_clarity: { label: 'Communication Clarity', icon: '🗣️' },
    technical_relevance:   { label: 'Technical Relevance',   icon: '⚙️' },
    problem_solving:       { label: 'Problem Solving',        icon: '🧩' },
    motivation_fit:        { label: 'Culture Fit',            icon: '🎯' },
    confidence:            { label: 'Confidence',             icon: '💪' },
    listening_comprehension: { label: 'Comprehension',        icon: '👂' },
};

const ScoreBar = ({ score }) => {
    const pct = ((score - 1) / 9) * 100;
    const colorClass = score >= 8.0 ? 'from-accent-emerald to-emerald-400' 
                     : score >= 6.0 ? 'from-accent-amber to-amber-400' 
                     : 'from-accent-red to-red-400';
    const textColor = score >= 8.0 ? 'text-accent-emerald' : score >= 6.0 ? 'text-accent-amber' : 'text-accent-red';

    return (
        <div className="flex items-center gap-4">
            <div className="flex-1 bg-slate-800 rounded-full h-2 overflow-hidden shadow-inner relative">
                <motion.div
                    initial={{ width: 0 }}
                    whileInView={{ width: `${pct}%` }}
                    transition={{ duration: 1.5, ease: "easeOut" }}
                    viewport={{ once: true }}
                    className={`h-full rounded-full bg-gradient-to-r ${colorClass}`}
                />
            </div>
            <span className={`text-[15px] font-black w-14 text-right tracking-tight ${textColor} drop-shadow-sm`}>
                {score.toFixed(1)}/10
            </span>
        </div>
    );
};

const OverallScoreRing = ({ score }) => {
    const color = score >= 8.0 ? 'text-accent-emerald' : score >= 6.0 ? 'text-accent-amber' : 'text-accent-red';
    const glow = score >= 8.0 ? 'shadow-[0_0_40px_rgba(16,185,129,0.3)] border-accent-emerald/30' 
               : score >= 6.0 ? 'shadow-[0_0_40px_rgba(245,158,11,0.3)] border-accent-amber/30' 
               : 'shadow-[0_0_40px_rgba(239,68,68,0.3)] border-accent-red/30';

    return (
        <motion.div 
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: "spring", stiffness: 200, damping: 20 }}
            className={`w-40 h-40 rounded-full flex flex-col items-center justify-center border-4 bg-slate-900/80 backdrop-blur-md relative shrink-0 ${color} ${glow}`}
        >
            <div className="absolute inset-0 rounded-full bg-gradient-to-br from-white/5 to-transparent pointer-events-none" />
            <span className="text-[3.5rem] font-black leading-none tracking-tighter drop-shadow-md relative z-10">{score.toFixed(1)}</span>
            <span className="text-[10px] uppercase tracking-widest font-bold opacity-70 mt-1 relative z-10 text-slate-300">Overall</span>
        </motion.div>
    );
};

const ReportViewer = ({ sessionId }) => {
    const [report, setReport] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [generationStatus, setGenerationStatus] = useState('Generating your report...');

    const { isReportReady } = useWebSocket(sessionId);
    const pollIntervalRef = useRef(null);
    const pollDelayRef = useRef(5000);   
    const fetchedRef = useRef(false);

    const tryFetchReport = useCallback(async () => {
        if (fetchedRef.current) return;
        try {
            const data = await getReport(sessionId);
            fetchedRef.current = true;
            if (pollIntervalRef.current) clearTimeout(pollIntervalRef.current);
            setReport(data);
            setLoading(false);
        } catch (err) {
            if (err.response?.status === 404 || err.response?.status === 409) {
                const nextDelay = Math.min(pollDelayRef.current * 1.5, 15000);
                pollDelayRef.current = nextDelay;
                setGenerationStatus(`Analyzing performance...`);
                pollIntervalRef.current = setTimeout(tryFetchReport, nextDelay);
            } else {
                setError('Could not load the interview report. Please try again.');
                setLoading(false);
            }
        }
    }, [sessionId]);

    useEffect(() => {
        if (!sessionId) return;
        const start = async () => {
            try {
                await generateReport(sessionId);
                setGenerationStatus('AI is generating comprehensive feedback...');
                pollIntervalRef.current = setTimeout(tryFetchReport, 4000);
            } catch (err) {
                console.error('[ReportViewer] Failed to trigger generation:', err);
                setError('Could not start report generation. Please refresh.');
                setLoading(false);
            }
        };
        start();
        return () => { if (pollIntervalRef.current) clearTimeout(pollIntervalRef.current); };
    }, [sessionId, tryFetchReport]);

    useEffect(() => {
        if (isReportReady && !fetchedRef.current) {
            if (pollIntervalRef.current) clearTimeout(pollIntervalRef.current);
            setGenerationStatus('Report ready — rendering dashboard...');
            tryFetchReport();
        }
    }, [isReportReady, tryFetchReport]);

    if (loading) {
        return (
            <div className="min-h-[calc(100vh-64px)] flex flex-col justify-center items-center relative overflow-hidden bg-slate-950">
                <motion.div animate={{ rotate: 360 }} transition={{ duration: 20, repeat: Infinity, ease: "linear" }} className="absolute w-[800px] h-[800px] bg-accent-blue/5 rounded-full blur-[150px] pointer-events-none" />
                <motion.div animate={{ scale: [1, 1.2, 1], opacity: [0.5, 1, 0.5] }} transition={{ duration: 2, repeat: Infinity }} className="w-16 h-16 rounded-full border-4 border-slate-800 border-t-accent-blue animate-spin mb-8" />
                <p className="text-xl font-bold tracking-tight text-white drop-shadow-md">{generationStatus}</p>
                <p className="text-sm text-slate-500 mt-2 tracking-wide">Compiling dimensions and extracting insights...</p>
            </div>
        );
    }
    
    if (error) {
        return (
            <div className="p-6 bg-accent-red/10 border border-accent-red/30 rounded-[20px] max-w-4xl mx-auto mt-10 backdrop-blur-md">
                <p className="text-accent-red font-bold text-center">{error}</p>
            </div>
        );
    }
    
    if (!report) return null;

    const downloadPDF = async () => {
        const element = document.getElementById("report-content");
        const canvas = await html2canvas(element, { scale: 2, backgroundColor: '#020617' });
        const imgData = canvas.toDataURL("image/png");
        const pdf = new jsPDF("p", "mm", "a4");
        const pdfWidth = pdf.internal.pageSize.getWidth();
        const pdfHeight = (canvas.height * pdfWidth) / canvas.width;
        pdf.addImage(imgData, "PNG", 0, 0, pdfWidth, pdfHeight);
        pdf.save(`interview_report_${sessionId}.pdf`);
    };

    const containerVariants = { hidden: { opacity: 0 }, visible: { opacity: 1, transition: { staggerChildren: 0.1 } } };
    const itemVariants = { hidden: { opacity: 0, y: 30 }, visible: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } } };

    return (
        <div className="min-h-[calc(100vh-64px)] bg-slate-950 text-slate-50 py-12 relative overflow-hidden">
            {/* Background Orbs */}
            <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-accent-blue/10 rounded-full blur-[150px] pointer-events-none -translate-y-1/2 translate-x-1/3" />
            <div className="absolute bottom-0 left-0 w-[800px] h-[800px] bg-accent-purple/10 rounded-full blur-[150px] pointer-events-none translate-y-1/3 -translate-x-1/3" />

            <div className="max-w-6xl mx-auto px-6 relative z-10">
                <motion.div id="report-content" className="space-y-10" variants={containerVariants} initial="hidden" animate="visible">

                    {/* ── Header card ─────────────────────────────────────────────────── */}
                    <motion.div variants={itemVariants} className="glass-panel rounded-[2.5rem] p-10 lg:p-12 flex flex-col sm:flex-row items-center gap-10 lg:gap-14 shadow-2xl relative overflow-hidden group">
                        <div className="absolute inset-0 bg-gradient-to-r from-accent-blue/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" />
                        <OverallScoreRing score={report.overallScore} />

                        <div className="flex-1 space-y-6 text-center sm:text-left relative z-10">
                            <div>
                                <h1 className="text-4xl lg:text-5xl font-extrabold tracking-tight text-white mb-2 drop-shadow-sm">
                                    Performance Report
                                </h1>
                                <p className="text-sm text-slate-400 tracking-wide">ID: {report.sessionId}</p>
                            </div>

                            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-sm bg-slate-900/50 rounded-2xl p-4 border border-slate-800/50 shadow-inner">
                                <div className="flex flex-col gap-1">
                                    <span className="text-[10px] uppercase tracking-widest text-slate-500 font-bold">Candidate</span>
                                    <span className="font-semibold text-slate-200 truncate" title={report.candidateId}>{report.candidateId}</span>
                                </div>
                                <div className="flex flex-col gap-1">
                                    <span className="text-[10px] uppercase tracking-widest text-slate-500 font-bold">Role</span>
                                    <span className="font-semibold text-slate-200 truncate">{report.jobDescription?.substring(0,20) || 'General Role'}...</span>
                                </div>
                                <div className="flex flex-col gap-1">
                                    <span className="text-[10px] uppercase tracking-widest text-slate-500 font-bold">Mode</span>
                                    <span className="font-semibold text-slate-200 capitalize">{report.interviewMode.replace(/_/g, ' ')}</span>
                                </div>
                                <div className="flex flex-col gap-1">
                                    <span className="text-[10px] uppercase tracking-widest text-slate-500 font-bold">Length</span>
                                    <span className="font-semibold text-slate-200 capitalize">{report.interviewLength}</span>
                                </div>
                            </div>

                            <button
                                onClick={downloadPDF}
                                className="inline-flex items-center gap-2.5 px-6 py-3 bg-white text-slate-900 hover:bg-slate-200 hover:scale-105 transition-all duration-300 font-bold tracking-wide rounded-full shadow-[0_0_30px_rgba(255,255,255,0.15)] group/btn"
                            >
                                <svg className="w-5 h-5 group-hover/btn:-translate-y-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                </svg>
                                Export as PDF
                            </button>
                        </div>
                    </motion.div>

                    {/* ── Executive Summary ────────────────────────────────────────────── */}
                    <motion.div variants={itemVariants} className="bg-gradient-to-br from-accent-blue/10 to-transparent border border-accent-blue/20 rounded-[2.5rem] p-10 lg:p-12 space-y-8 relative overflow-hidden backdrop-blur-sm">
                        <div className="absolute top-0 right-0 w-64 h-64 bg-accent-blue/20 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/2 pointer-events-none" />
                        
                        <div>
                            <h2 className="text-xs uppercase tracking-[0.2em] font-black text-accent-blue mb-4">Executive Summary</h2>
                            <p className="text-lg lg:text-xl text-slate-200 leading-relaxed font-medium">
                                {report.executiveSummary}
                            </p>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 lg:gap-12 pt-6">
                            <div className="bg-slate-950/50 rounded-[20px] p-6 border border-slate-800">
                                <h3 className="text-[11px] font-black uppercase tracking-widest text-accent-emerald mb-4 flex items-center gap-2">
                                    <span className="w-5 h-5 rounded-full bg-accent-emerald/20 flex items-center justify-center text-accent-emerald">✓</span>
                                    Top Strengths
                                </h3>
                                <ul className="space-y-3 m-0 p-0">
                                    {report.topStrengths.map((s, i) => (
                                        <li key={i} className="text-sm text-slate-300 flex items-start gap-3">
                                            <span className="text-accent-emerald font-bold mt-0.5 shrink-0">✦</span> 
                                            <span className="leading-relaxed">{s}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                            <div className="bg-slate-950/50 rounded-[20px] p-6 border border-slate-800">
                                <h3 className="text-[11px] font-black uppercase tracking-widest text-accent-amber mb-4 flex items-center gap-2">
                                    <span className="w-5 h-5 rounded-full bg-accent-amber/20 flex items-center justify-center text-accent-amber">!</span>
                                    Areas for Growth
                                </h3>
                                <ul className="space-y-3 m-0 p-0">
                                    {report.areasForImprovement.map((s, i) => (
                                        <li key={i} className="text-sm text-slate-300 flex items-start gap-3">
                                            <span className="text-accent-amber font-bold mt-0.5 shrink-0">✦</span> 
                                            <span className="leading-relaxed">{s}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>

                        <div className="pt-4 border-t border-white/10">
                            <h3 className="text-[11px] font-black uppercase tracking-widest text-accent-purple mb-3">→ Recommended Next Steps</h3>
                            <p className="text-sm text-slate-300 leading-relaxed max-w-4xl">{report.recommendedNextSteps}</p>
                        </div>
                    </motion.div>

                    {/* ── Dimension Breakdown ──────────────────────────────────────────── */}
                    <motion.div variants={itemVariants} className="space-y-6 pt-4">
                        <div className="flex items-center gap-4 mb-8">
                            <h2 className="text-2xl font-extrabold tracking-tight text-white">Dimension Breakdown</h2>
                            <div className="h-px flex-1 bg-gradient-to-r from-slate-700 to-transparent" />
                        </div>
                        
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            {Object.entries(report.dimensionScores).map(([dimKey, dimScore]) => {
                                const config = DIMENSION_CONFIG[dimKey] || { label: dimKey.replace(/_/g, ' '), icon: '📊' };
                                return (
                                    <motion.div 
                                        key={dimKey} 
                                        whileHover={{ y: -5 }}
                                        transition={{ type: "spring", stiffness: 300 }}
                                        className="glass-panel rounded-[2rem] p-8 space-y-6 border border-slate-700/50 hover:border-slate-500 transition-colors duration-300 shadow-lg"
                                    >
                                        <div className="flex items-center gap-4">
                                            <div className="w-12 h-12 rounded-2xl bg-slate-800/80 flex items-center justify-center text-2xl shadow-inner border border-white/5">
                                                {config.icon}
                                            </div>
                                            <h3 className="font-bold text-slate-100 text-lg flex-1 tracking-tight">
                                                {config.label}
                                            </h3>
                                        </div>

                                        <ScoreBar score={dimScore.score} />

                                        <div className="bg-slate-900/50 rounded-xl p-4 border-l-2 border-accent-blue">
                                            <p className="text-sm text-slate-300 italic leading-relaxed font-serif">
                                                "{dimScore.rationale}"
                                            </p>
                                        </div>

                                        {dimScore.evidence && dimScore.evidence.length > 0 && (
                                            <div className="pt-2">
                                                <p className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-3">
                                                    Evidence points
                                                </p>
                                                <ul className="space-y-2 m-0 p-0">
                                                    {dimScore.evidence.map((item, i) => (
                                                        <li key={i} className="text-[13px] text-slate-400 flex items-start gap-2.5">
                                                            <span className="text-accent-blue shrink-0 mt-[2px]">▸</span>
                                                            <span className="leading-relaxed">{item}</span>
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                    </motion.div>
                                );
                            })}
                        </div>
                    </motion.div>

                </motion.div>
            </div>
        </div>
    );
};

export default ReportViewer;
