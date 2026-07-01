// ─────────────────────────────────────────────────────────────────────────────
// frontend/src/components/report/ReportViewer.jsx
//
// Renders a complete InterviewReport object as a visual performance dashboard.
// Maps all 6 dimension scores into color-coded progress meters with distinct
// evidence bullet points and italic rationale narrative sections.
// ─────────────────────────────────────────────────────────────────────────────

import React, { useState, useEffect } from 'react';
import jsPDF from "jspdf";
import html2canvas from "html2canvas";
import { getReport, generateReport } from '../../services/api';

// Dimension display configuration — human labels for camelCase schema keys
const DIMENSION_CONFIG = {
    communication_clarity: { label: 'Communication Clarity', icon: '🗣️' },
    technical_relevance:   { label: 'Technical Relevance',   icon: '⚙️' },
    problem_solving:       { label: 'Problem Solving',        icon: '🧩' },
    motivation_fit:        { label: 'Motivation & Culture Fit', icon: '🎯' },
    confidence:            { label: 'Confidence',             icon: '💪' },
    listening_comprehension: { label: 'Listening Comprehension', icon: '👂' },
};

const ScoreBar = ({ score }) => {
    const pct = ((score - 1) / 9) * 100;
    const color =
        score >= 8.0 ? 'bg-green-500'
        : score >= 6.0 ? 'bg-yellow-400'
        : 'bg-red-500';

    return (
        <div className="flex items-center gap-3">
            <div className="flex-1 bg-gray-100 rounded-full h-2.5 overflow-hidden">
                <div
                    className={`h-2.5 rounded-full transition-all duration-500 ${color}`}
                    style={{ width: `${pct}%` }}
                />
            </div>
            <span className={`text-sm font-bold w-12 text-right ${
                score >= 8.0 ? 'text-green-700' : score >= 6.0 ? 'text-yellow-600' : 'text-red-600'
            }`}>
                {score.toFixed(1)}/10
            </span>
        </div>
    );
};

const OverallScoreRing = ({ score }) => {
    const color =
        score >= 8.0 ? 'text-green-500' : score >= 6.0 ? 'text-yellow-500' : 'text-red-500';
    return (
        <div className={`flex flex-col items-center ${color}`}>
            <span className="text-6xl font-black">{score.toFixed(1)}</span>
            <span className="text-sm text-gray-500 font-medium mt-1">Overall Score / 10.0</span>
        </div>
    );
};

const ReportViewer = ({ sessionId }) => {
    const [report, setReport] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [generationStatus, setGenerationStatus] = useState('Fetching report...');

    useEffect(() => {
        let intervalId;
        const fetchOrGenerate = async () => {
            try {
                setLoading(true);
                // Trigger generation
                setGenerationStatus('Triggering report generation...');
                await generateReport(sessionId);

                setGenerationStatus('Generating report (this may take up to 30 seconds)...');
                
                const poll = async () => {
                    try {
                        const data = await getReport(sessionId);
                        setReport(data);
                        setLoading(false);
                        clearInterval(intervalId);
                    } catch (err) {
                        if (err.response?.status === 404) {
                            setGenerationStatus('Still generating report... please wait...');
                        } else {
                            throw err;
                        }
                    }
                };

                intervalId = setInterval(poll, 3000);
                poll(); // initial check

            } catch (err) {
                console.error('[ReportViewer] Failed to load/generate report:', err);
                setError('Could not load the interview report. Please try again.');
                setLoading(false);
                if (intervalId) clearInterval(intervalId);
            }
        };
        if (sessionId) fetchOrGenerate();

        return () => {
            if (intervalId) clearInterval(intervalId);
        };
    }, [sessionId]);

    if (loading) {
        return (
            <div className="flex flex-col justify-center items-center py-20 gap-4">
                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" />
                <p className="text-gray-600 font-medium">{generationStatus}</p>
            </div>
        );
    }
    if (error) {
        return (
            <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded max-w-4xl mx-auto mt-6">
                <p className="text-red-700">{error}</p>
            </div>
        );
    }
    if (!report) return null;

    const downloadPDF = async () => {
        const element = document.getElementById("report-content");
        const canvas = await html2canvas(element);
        const imgData = canvas.toDataURL("image/png");
        const pdf = new jsPDF("p", "mm", "a4");
        const pdfWidth = pdf.internal.pageSize.getWidth();
        const pdfHeight = (canvas.height * pdfWidth) / canvas.width;
        pdf.addImage(imgData, "PNG", 0, 0, pdfWidth, pdfHeight);
        pdf.save(`interview_report_${sessionId}.pdf`);
    };

    return (
        <div id="report-content" className="max-w-5xl mx-auto px-4 py-10 space-y-10">

            {/* ── Header card ─────────────────────────────────────────────────── */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 flex flex-col sm:flex-row items-center gap-8">
                <OverallScoreRing score={report.overallScore} />

                <div className="flex-1 space-y-2">
                    <h1 className="text-2xl font-bold text-gray-900">Interview Report</h1>
                    <div className="grid grid-cols-2 gap-2 text-sm text-gray-600">
                        <span><strong>Session:</strong> {report.sessionId}</span>
                        <span><strong>Candidate:</strong> {report.candidateId}</span>
                        <span className="capitalize"><strong>Mode:</strong> {report.interviewMode.replace(/_/g, ' ')}</span>
                        <span className="capitalize"><strong>Length:</strong> {report.interviewLength}</span>
                    </div>

                    {/* PDF download */}
                    <button
                        onClick={downloadPDF}
                        className="inline-flex items-center gap-2 mt-3 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition-colors"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 10v6m0 0l-3-3m3 3l3-3M3 17V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
                        </svg>
                        Download PDF Report
                    </button>
                </div>
            </div>

            {/* ── Executive Summary ────────────────────────────────────────────── */}
            <div className="bg-blue-50 border-l-4 border-blue-500 rounded-xl p-6 space-y-4">
                <h2 className="text-lg font-bold text-gray-800">Executive Summary</h2>
                <p className="text-gray-700 leading-relaxed">{report.executiveSummary}</p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-2">
                    <div>
                        <h3 className="text-sm font-semibold text-green-700 mb-2">✓ Top Strengths</h3>
                        <ul className="space-y-1">
                            {report.topStrengths.map((s, i) => (
                                <li key={i} className="text-sm text-gray-700 flex gap-2">
                                    <span className="text-green-500 mt-0.5">•</span> {s}
                                </li>
                            ))}
                        </ul>
                    </div>
                    <div>
                        <h3 className="text-sm font-semibold text-amber-700 mb-2">⚑ Areas for Improvement</h3>
                        <ul className="space-y-1">
                            {report.areasForImprovement.map((s, i) => (
                                <li key={i} className="text-sm text-gray-700 flex gap-2">
                                    <span className="text-amber-500 mt-0.5">•</span> {s}
                                </li>
                            ))}
                        </ul>
                    </div>
                </div>

                <div className="pt-2">
                    <h3 className="text-sm font-semibold text-blue-700 mb-1">→ Recommended Next Steps</h3>
                    <p className="text-sm text-gray-700">{report.recommendedNextSteps}</p>
                </div>
            </div>

            {/* ── Dimension Breakdown ──────────────────────────────────────────── */}
            <div>
                <h2 className="text-xl font-bold text-gray-900 mb-5">Dimension Breakdown</h2>
                <div className="space-y-5">
                    {Object.entries(report.dimensionScores).map(([dimKey, dimScore]) => {
                        const config = DIMENSION_CONFIG[dimKey] || { label: dimKey.replace(/_/g, ' '), icon: '📊' };
                        return (
                            <div key={dimKey} className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-4">
                                {/* Header row */}
                                <div className="flex items-center gap-3">
                                    <span className="text-xl">{config.icon}</span>
                                    <h3 className="font-semibold text-gray-900 capitalize text-base flex-1">
                                        {config.label}
                                    </h3>
                                </div>

                                {/* Score bar */}
                                <ScoreBar score={dimScore.score} />

                                {/* Italic rationale */}
                                <p className="text-sm text-gray-500 italic leading-relaxed border-l-2 border-gray-200 pl-3">
                                    "{dimScore.rationale}"
                                </p>

                                {/* Evidence bullets */}
                                {dimScore.evidence && dimScore.evidence.length > 0 && (
                                    <div>
                                        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                                            Evidence
                                        </p>
                                        <ul className="space-y-1">
                                            {dimScore.evidence.map((item, i) => (
                                                <li key={i} className="text-sm text-gray-600 flex gap-2">
                                                    <span className="text-blue-400 flex-shrink-0">▸</span>
                                                    {item}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>

        </div>
    );
};

export default ReportViewer;
