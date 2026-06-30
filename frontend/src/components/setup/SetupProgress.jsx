import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useSession } from '../../context/SessionContext';

const SetupProgress = () => {
    const { sessionId, setCurrentPhase } = useSession();
    const [status, setStatus] = useState('setting_up');
    const [lastStep, setLastStep] = useState('Initialising…');
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!sessionId) return;

        const interval = setInterval(async () => {
            try {
                const response = await axios.get(`http://localhost:8000/api/sessions/${sessionId}/status`);
                const data = response.data;
                
                setStatus(data.status);
                if (data.last_step) {
                    setLastStep(data.last_step);
                }
                if (data.error) {
                    setError(data.error);
                    clearInterval(interval);
                }
                
                if (data.status === 'ready') {
                    clearInterval(interval);
                    // Give a slight delay so user can see it finished
                    setTimeout(() => setCurrentPhase('interview'), 1500);
                } else if (data.status === 'error') {
                    clearInterval(interval);
                }
            } catch (err) {
                console.error("Failed to fetch setup status", err);
                setError("Failed to connect to backend");
                clearInterval(interval);
            }
        }, 1000);

        return () => clearInterval(interval);
    }, [sessionId, setCurrentPhase]);

    // Simple progress percentage heuristic based on step logs or just an animated indeterminate bar
    return (
        <div className="bg-white p-8 rounded-xl shadow-lg max-w-md mx-auto mt-20 space-y-6">
            <div className="text-center">
                <h2 className="text-2xl font-bold text-gray-800">Preparing Interview</h2>
                <p className="text-sm text-gray-500 mt-2">Our AI is analyzing your CV and generating questions...</p>
            </div>

            {error ? (
                <div className="bg-red-50 text-red-700 p-4 rounded-md text-sm border border-red-200">
                    <p className="font-semibold">Setup Failed</p>
                    <p>{error}</p>
                    <button 
                        onClick={() => setCurrentPhase('setup')}
                        className="mt-3 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
                    >
                        Go Back
                    </button>
                </div>
            ) : (
                <div className="space-y-4">
                    <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                        <div className={`h-full bg-blue-600 rounded-full transition-all duration-500 ease-in-out ${status === 'ready' ? 'w-full' : 'w-2/3 animate-pulse'}`}></div>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-700 font-medium">{lastStep}</span>
                        <span className="text-gray-400">
                            {status === 'ready' ? 'Complete' : 'Processing...'}
                        </span>
                    </div>
                </div>
            )}
        </div>
    );
};

export default SetupProgress;
