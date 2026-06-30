// ─────────────────────────────────────────────────────────────────────────────
// frontend/src/components/setup/InterviewConfig.jsx
// ─────────────────────────────────────────────────────────────────────────────

import React, { useState } from 'react';

const LENGTH_OPTIONS = [
    { value: 'short', label: 'Short (5-7 questions, ~5-10 min)' },
    { value: 'medium', label: 'Medium (10-15 questions, ~15-25 min)' },
    { value: 'long', label: 'Long (18-25 questions, ~30-45 min)' }
];

const MODE_OPTIONS = [
    { value: 'mixed', label: 'Mixed (Balanced)' },
    { value: 'technical', label: 'Technical (80% Tech, 20% Behavioral)' },
    { value: 'behavioral', label: 'Behavioral (80% Behavioral, 20% Tech)' },
    { value: 'hrCultureFit', label: 'HR / Culture Fit (70% Culture, 30% Behavioral)' },
    { value: 'systemDesign', label: 'System Design (90% Design, 10% Behavioral)' }
];

const InterviewConfig = ({ onConfigChange, initialData = {} }) => {
    const [interviewLength, setInterviewLength] = useState(initialData.interviewLength || 'medium');
    const [interviewMode, setInterviewMode] = useState(initialData.interviewMode || 'mixed');

    const handleLengthChange = (e) => {
        const val = e.target.value;
        setInterviewLength(val);
        if (onConfigChange) {
            onConfigChange({ interviewLength: val, interviewMode });
        }
    };

    const handleModeChange = (e) => {
        const val = e.target.value;
        setInterviewMode(val);
        if (onConfigChange) {
            onConfigChange({ interviewLength, interviewMode: val });
        }
    };

    return (
        <div className="bg-white p-6 rounded-lg shadow-md max-w-3xl mx-auto space-y-6 mt-6">
            <h2 className="text-2xl font-bold text-gray-800">Interview Settings</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                
                {/* Interview Length */}
                <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-700">Interview Length</label>
                    <div className="relative">
                        <select 
                            className="block appearance-none w-full bg-white border border-gray-300 hover:border-gray-400 px-4 py-2 pr-8 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all cursor-pointer"
                            value={interviewLength}
                            onChange={handleLengthChange}
                        >
                            {LENGTH_OPTIONS.map(opt => (
                                <option key={opt.value} value={opt.value}>{opt.label}</option>
                            ))}
                        </select>
                        <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-700">
                            <svg className="fill-current h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
                                <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z"/>
                            </svg>
                        </div>
                    </div>
                </div>

                {/* Interview Mode */}
                <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-700">Interview Mode</label>
                    <div className="relative">
                        <select 
                            className="block appearance-none w-full bg-white border border-gray-300 hover:border-gray-400 px-4 py-2 pr-8 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all cursor-pointer"
                            value={interviewMode}
                            onChange={handleModeChange}
                        >
                            {MODE_OPTIONS.map(opt => (
                                <option key={opt.value} value={opt.value}>{opt.label}</option>
                            ))}
                        </select>
                        <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-700">
                            <svg className="fill-current h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
                                <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z"/>
                            </svg>
                        </div>
                    </div>
                </div>

            </div>
        </div>
    );
};

export default InterviewConfig;
