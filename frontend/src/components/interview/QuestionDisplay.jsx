import React from 'react';

const QuestionDisplay = ({ currentQuestion, connectionError, submitError, phaseConfig }) => {
    return (
        <div className="space-y-6">
            {connectionError && (
                <div className="bg-red-900/50 border border-red-700 rounded-lg p-3 text-sm text-red-300">
                    {connectionError}
                </div>
            )}

            {/* Phase badge + question index */}
            <div className="flex items-center gap-3">
                <span className={`text-xs font-semibold px-3 py-1 rounded-full ${phaseConfig.color}`}>
                    {phaseConfig.label}
                </span>
                {currentQuestion && (
                    <span className="text-xs text-gray-500">
                        Difficulty Level {currentQuestion.difficulty}/5
                    </span>
                )}
            </div>

            {/* Question text */}
            <div className="space-y-2">
                {currentQuestion ? (
                    <>
                        <h2 className="text-2xl font-semibold leading-snug text-white">
                            {currentQuestion.text}
                        </h2>
                        {currentQuestion.category && (
                            <p className="text-sm text-gray-500 capitalize">
                                Category: {currentQuestion.category}
                            </p>
                        )}
                    </>
                ) : (
                    <div className="space-y-3 animate-pulse">
                        <div className="h-7 bg-gray-700 rounded w-3/4"></div>
                        <div className="h-5 bg-gray-800 rounded w-1/2"></div>
                    </div>
                )}
            </div>

            {/* Submission error */}
            {submitError && (
                <div className="bg-red-900/50 border border-red-700 rounded-lg p-3 text-sm text-red-300">
                    {submitError}
                </div>
            )}
        </div>
    );
};

export default QuestionDisplay;
