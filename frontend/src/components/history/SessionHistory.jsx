// ─────────────────────────────────────────────────────────────────────────────
// frontend/src/components/history/SessionHistory.jsx
// ─────────────────────────────────────────────────────────────────────────────

import React, { useState, useEffect } from 'react';
import { getCandidateSessions } from '../../services/api';

const SessionHistory = ({ candidateId, onCompareSelected }) => {
    const [sessions, setSessions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedForComparison, setSelectedForComparison] = useState([]);

    useEffect(() => {
        const fetchHistory = async () => {
            if (!candidateId) return;
            try {
                setLoading(true);
                const data = await getCandidateSessions(candidateId);
                // Assuming data is an array of sessions, sorted by date desc
                setSessions(data || []);
            } catch (err) {
                console.error("Failed to load session history:", err);
                setError("Could not load your interview history. Please try again later.");
            } finally {
                setLoading(false);
            }
        };

        fetchHistory();
    }, [candidateId]);

    const handleSelectForCompare = (sessionId) => {
        setSelectedForComparison((prev) => {
            if (prev.includes(sessionId)) {
                return prev.filter(id => id !== sessionId);
            }
            if (prev.length >= 2) {
                alert("You can only select exactly 2 sessions to compare.");
                return prev;
            }
            return [...prev, sessionId];
        });
    };

    const handleTriggerComparison = () => {
        if (selectedForComparison.length !== 2) {
            alert("Please select exactly two sessions to trigger a comparison.");
            return;
        }
        if (onCompareSelected) {
            onCompareSelected(selectedForComparison[0], selectedForComparison[1]);
        }
    };

    if (loading) {
        return (
            <div className="flex justify-center items-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
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

    return (
        <div className="bg-white p-6 rounded-lg shadow-md max-w-5xl mx-auto space-y-6 mt-6">
            <div className="flex justify-between items-center">
                <h2 className="text-2xl font-bold text-gray-800">Interview History Dashboard</h2>
                {selectedForComparison.length > 0 && (
                    <button 
                        onClick={handleTriggerComparison}
                        disabled={selectedForComparison.length !== 2}
                        className={`px-4 py-2 rounded shadow-sm transition-colors text-white font-medium ${
                            selectedForComparison.length === 2 
                                ? 'bg-purple-600 hover:bg-purple-700' 
                                : 'bg-gray-400 cursor-not-allowed'
                        }`}
                    >
                        Compare Selected ({selectedForComparison.length}/2)
                    </button>
                )}
            </div>

            {sessions.length === 0 ? (
                <div className="text-center py-12 border-2 border-dashed border-gray-200 rounded-lg bg-gray-50">
                    <p className="text-gray-500">No past interviews found. Ready for your first session?</p>
                </div>
            ) : (
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="bg-gray-50 border-b border-gray-200">
                                <th className="p-4 text-sm font-semibold text-gray-600 w-12">Compare</th>
                                <th className="p-4 text-sm font-semibold text-gray-600">Date</th>
                                <th className="p-4 text-sm font-semibold text-gray-600">Mode</th>
                                <th className="p-4 text-sm font-semibold text-gray-600">Length</th>
                                <th className="p-4 text-sm font-semibold text-gray-600 text-center">Overall Score</th>
                                <th className="p-4 text-sm font-semibold text-gray-600 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {sessions.map((session) => (
                                <tr key={session.sessionId} className="hover:bg-blue-50 transition-colors">
                                    <td className="p-4">
                                        <input 
                                            type="checkbox"
                                            className="w-4 h-4 text-purple-600 rounded focus:ring-purple-500 cursor-pointer"
                                            checked={selectedForComparison.includes(session.sessionId)}
                                            onChange={() => handleSelectForCompare(session.sessionId)}
                                        />
                                    </td>
                                    <td className="p-4 text-sm text-gray-800">
                                        {new Date(session.createdAt).toLocaleDateString(undefined, {
                                            year: 'numeric', month: 'short', day: 'numeric'
                                        })}
                                    </td>
                                    <td className="p-4 text-sm text-gray-600 capitalize">
                                        {session.interviewMode.replace(/([A-Z])/g, ' $1').trim()}
                                    </td>
                                    <td className="p-4 text-sm text-gray-600 capitalize">
                                        {session.interviewLength}
                                    </td>
                                    <td className="p-4 text-center">
                                        {session.finalReport ? (
                                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-sm font-medium ${
                                                session.finalReport.overallScore >= 8.0 ? 'bg-green-100 text-green-800' : 
                                                session.finalReport.overallScore >= 6.0 ? 'bg-yellow-100 text-yellow-800' : 
                                                'bg-red-100 text-red-800'
                                            }`}>
                                                {session.finalReport.overallScore.toFixed(1)} / 10
                                            </span>
                                        ) : (
                                            <span className="text-gray-400 italic text-sm">Processing...</span>
                                        )}
                                    </td>
                                    <td className="p-4 text-right">
                                        <button 
                                            disabled={!session.pdfPath}
                                            className="text-blue-600 hover:text-blue-800 text-sm font-medium disabled:text-gray-400 disabled:cursor-not-allowed transition-colors"
                                            onClick={() => {
                                                // Assuming API routes serve the PDF statically
                                                window.open(`http://localhost:8000/api/reports/${session.sessionId}/pdf`, '_blank');
                                            }}
                                        >
                                            View Report &rarr;
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
};

export default SessionHistory;
