// ─────────────────────────────────────────────────────────────────────────────
// frontend/src/components/report/ComparisonViewer.jsx
//
// Side-by-side ProgressComparison visualizer.
// Maps dimension_deltas into signed delta badges, and separately presents
// strengths_improved vs regressions_detected in clearly differentiated panels.
// ─────────────────────────────────────────────────────────────────────────────

import React, { useState, useEffect } from 'react';
import { compareReports } from '../../services/api';

const DeltaBadge = ({ delta }) => {
    if (delta === 0) {
        return (
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-500">
                No Change
            </span>
        );
    }
    const isPositive = delta > 0;
    return (
        <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
            isPositive
                ? 'bg-green-100 text-green-700'
                : 'bg-red-100 text-red-700'
        }`}>
            {isPositive ? '+' : ''}{delta.toFixed(1)}
        </span>
    );
};

const DIMENSION_LABELS = {
    communication_clarity: 'Communication Clarity',
    technical_relevance: 'Technical Relevance',
    problem_solving: 'Problem Solving',
    motivation_fit: 'Motivation & Culture Fit',
    confidence: 'Confidence',
    listening_comprehension: 'Listening Comprehension',
};

const ComparisonViewer = ({ previousSessionId, currentSessionId }) => {
    const [comparison, setComparison] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchComparison = async () => {
            if (!previousSessionId || !currentSessionId) return;
            try {
                setLoading(true);
                const data = await compareReports(previousSessionId, currentSessionId);
                setComparison(data);
            } catch (err) {
                console.error('[ComparisonViewer] Failed to load comparison:', err);
                setError('Could not load the comparison report. Please try again.');
            } finally {
                setLoading(false);
            }
        };
        fetchComparison();
    }, [previousSessionId, currentSessionId]);

    if (loading) {
        return (
            <div className="flex justify-center items-center py-20">
                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-purple-600" />
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
    if (!comparison) return null;

    const isPositiveOverall = comparison.overallScoreDelta > 0;

    return (
        <div className="max-w-5xl mx-auto px-4 py-10 space-y-10">

            {/* ── Overall Delta Header ─────────────────────────────────────────── */}
            <div className={`rounded-2xl p-8 text-center border-2 ${
                isPositiveOverall
                    ? 'bg-green-50 border-green-300'
                    : comparison.overallScoreDelta < 0
                        ? 'bg-red-50 border-red-300'
                        : 'bg-gray-50 border-gray-200'
            }`}>
                <h1 className="text-2xl font-bold text-gray-800 mb-3">Progress Comparison</h1>
                <p className="text-sm text-gray-500 mb-4">
                    Session <code className="bg-gray-200 px-1 rounded">{previousSessionId.slice(0, 8)}</code>
                    {' → '}
                    Session <code className="bg-gray-200 px-1 rounded">{currentSessionId.slice(0, 8)}</code>
                </p>
                <div className={`text-6xl font-black ${
                    isPositiveOverall ? 'text-green-600'
                    : comparison.overallScoreDelta < 0 ? 'text-red-600'
                    : 'text-gray-500'
                }`}>
                    {isPositiveOverall ? '+' : ''}{comparison.overallScoreDelta.toFixed(1)}
                </div>
                <p className="text-sm text-gray-500 mt-2">Overall Score Shift</p>
            </div>

            {/* ── Comparison Narrative ─────────────────────────────────────────── */}
            <div className="bg-purple-50 border-l-4 border-purple-500 rounded-xl p-6">
                <h2 className="text-lg font-bold text-gray-800 mb-3">Progress Narrative</h2>
                <p className="text-gray-700 leading-relaxed italic">
                    "{comparison.comparisonNarrative}"
                </p>
            </div>

            {/* ── Dimension Delta Table ────────────────────────────────────────── */}
            <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-100">
                    <h2 className="text-lg font-bold text-gray-800">Dimension Shifts</h2>
                </div>
                <div className="divide-y divide-gray-50">
                    {Object.entries(comparison.dimensionDeltas).map(([dimKey, delta]) => (
                        <div key={dimKey} className="flex items-center justify-between px-6 py-4">
                            <span className="text-sm font-medium text-gray-700">
                                {DIMENSION_LABELS[dimKey] || dimKey.replace(/_/g, ' ')}
                            </span>
                            <DeltaBadge delta={delta} />
                        </div>
                    ))}
                </div>
            </div>

            {/* ── Three-panel qualitative grid ────────────────────────────────── */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">

                {/* Strengths Improved */}
                <div className="bg-white rounded-xl border-t-4 border-green-500 shadow-sm p-5 space-y-3">
                    <h3 className="text-sm font-bold text-green-700 uppercase tracking-wide">
                        ✓ Strengths Improved
                    </h3>
                    {comparison.strengthsImproved.length > 0 ? (
                        <ul className="space-y-2">
                            {comparison.strengthsImproved.map((item, i) => (
                                <li key={i} className="text-sm text-gray-700 flex gap-2">
                                    <span className="text-green-500 flex-shrink-0">▸</span> {item}
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <p className="text-sm text-gray-400 italic">No major positive shifts detected.</p>
                    )}
                </div>

                {/* Prior Weaknesses Addressed */}
                <div className="bg-white rounded-xl border-t-4 border-blue-500 shadow-sm p-5 space-y-3">
                    <h3 className="text-sm font-bold text-blue-700 uppercase tracking-wide">
                        ⭐ Weaknesses Resolved
                    </h3>
                    {comparison.weaknessesImproved.length > 0 ? (
                        <ul className="space-y-2">
                            {comparison.weaknessesImproved.map((item, i) => (
                                <li key={i} className="text-sm text-gray-700 flex gap-2">
                                    <span className="text-blue-500 flex-shrink-0">▸</span> {item}
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <p className="text-sm text-gray-400 italic">No prior weaknesses fully resolved yet.</p>
                    )}
                </div>

                {/* Regressions Detected */}
                <div className="bg-white rounded-xl border-t-4 border-red-500 shadow-sm p-5 space-y-3">
                    <h3 className="text-sm font-bold text-red-700 uppercase tracking-wide">
                        ✗ Regressions Detected
                    </h3>
                    {comparison.regressionsDetected.length > 0 ? (
                        <ul className="space-y-2">
                            {comparison.regressionsDetected.map((item, i) => (
                                <li key={i} className="text-sm text-gray-700 flex gap-2">
                                    <span className="text-red-500 flex-shrink-0 font-bold">!</span>
                                    <span className="font-medium text-red-800">{item}</span>
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <p className="text-sm text-gray-400 italic">No regressions detected. Excellent!</p>
                    )}
                </div>

            </div>

        </div>
    );
};

export default ComparisonViewer;
