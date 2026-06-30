import React from 'react';

const CoachingSidebar = ({ coachingFeedback }) => {
    return (
        <aside className="w-80 flex-shrink-0 bg-gray-900 border-l border-gray-800 flex flex-col">
            <div className="px-5 py-4 border-b border-gray-800">
                <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">
                    Live Coaching
                </h3>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {coachingFeedback.length === 0 ? (
                    <div className="text-center py-8 space-y-2">
                        <svg className="w-8 h-8 text-gray-700 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                        </svg>
                        <p className="text-sm text-gray-600">Coaching insights will appear here after each answer.</p>
                    </div>
                ) : (
                    [...coachingFeedback].reverse().map((fb, idx) => (
                        <div key={idx} className="bg-gray-800 rounded-lg p-4 space-y-3 border border-gray-700 shadow-md">
                            {/* Score preview */}
                            <div className="flex items-center justify-between">
                                <span className="text-xs text-gray-400 font-medium">Answer {fb.answerIndex + 1}</span>
                                <span className={`text-sm font-bold ${
                                    fb.scorePreview >= 8 ? 'text-green-400' :
                                    fb.scorePreview >= 6 ? 'text-yellow-400' :
                                    'text-red-400'
                                }`}>
                                    {fb.scorePreview}/10
                                </span>
                            </div>

                            {/* Feedback text */}
                            <p className="text-sm text-gray-300 leading-relaxed">
                                {fb.feedbackText}
                            </p>

                            {/* Strengths */}
                            {fb.strengths?.length > 0 && (
                                <div>
                                    <p className="text-xs text-green-400 font-semibold mb-1">✓ Strengths</p>
                                    <ul className="space-y-0.5">
                                        {fb.strengths.map((s, i) => (
                                            <li key={i} className="text-xs text-gray-400 truncate">• {s}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {/* Improvements */}
                            {fb.improvements?.length > 0 && (
                                <div>
                                    <p className="text-xs text-amber-400 font-semibold mb-1">⚑ Improve</p>
                                    <ul className="space-y-0.5">
                                        {fb.improvements.map((s, i) => (
                                            <li key={i} className="text-xs text-gray-400 truncate">• {s}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    ))
                )}
            </div>
        </aside>
    );
};

export default CoachingSidebar;
