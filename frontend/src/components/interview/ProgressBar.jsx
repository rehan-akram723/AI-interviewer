import React from 'react';

const ProgressBar = ({ currentQuestionIndex, totalQuestions = 5 }) => {
    // Basic heuristic: if we don't know total questions, default to 5 or scale up
    const progress = Math.min(((currentQuestionIndex) / totalQuestions) * 100, 100);

    return (
        <div className="w-full max-w-3xl mx-auto mt-4 px-10">
            <div className="flex justify-between text-xs text-gray-500 font-medium mb-1">
                <span>Progress</span>
                <span>Question {currentQuestionIndex + 1}</span>
            </div>
            <div className="w-full bg-gray-800 rounded-full h-1.5">
                <div 
                    className="bg-blue-500 h-1.5 rounded-full transition-all duration-500 ease-out" 
                    style={{ width: `${progress}%` }}
                ></div>
            </div>
        </div>
    );
};

export default ProgressBar;
