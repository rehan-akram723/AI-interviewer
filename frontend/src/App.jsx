import React, { useState } from 'react';
import axios from 'axios';
import { useSession } from './context/SessionContext';
import UploadPanel from './components/setup/UploadPanel';
import SetupProgress from './components/setup/SetupProgress';
import InterviewRoom from './components/interview/InterviewRoom';
import ReportViewer from './components/report/ReportViewer';
import ComparisonViewer from './components/report/ComparisonViewer';

const App = () => {
    const { 
        sessionId, 
        setSessionId, 
        setCandidateId, 
        currentPhase, 
        setCurrentPhase 
    } = useSession();

    const [formData, setFormData] = useState(null);
    const [isStarting, setIsStarting] = useState(false);

    const handleStartSetup = async () => {
        if (!formData || !formData.cvFile) {
            alert('Please select a CV PDF file to start.');
            return;
        }

        setIsStarting(true);
        try {
            const data = new FormData();
            data.append('cvFile', formData.cvFile);
            data.append('jobDescription', formData.jobDescription || '');
            data.append('companyName', formData.companyName || '');
            data.append('motivationLetter', formData.motivationLetter || '');
            // Using defaults for length and mode for now, or could come from context
            data.append('interviewLength', 'medium');
            data.append('interviewMode', 'mixed');

            const res = await axios.post('http://localhost:8000/api/sessions/setup', data, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            
            setSessionId(res.data.session_id);
            setCandidateId(res.data.candidate_id);
            setCurrentPhase('waiting');
        } catch (err) {
            console.error('Failed to start setup:', err);
            alert('Failed to connect to the server.');
        } finally {
            setIsStarting(false);
        }
    };

    return (
        <div className="min-h-screen bg-gray-100 flex flex-col font-sans">
            {/* Header */}
            <header className="bg-white border-b border-gray-200 px-6 py-4 shadow-sm flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                        <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                        </svg>
                    </div>
                    <h1 className="text-xl font-bold text-gray-800 tracking-tight">AI Interviewer</h1>
                </div>
            </header>

            {/* Main Content Area via State Machine Routing */}
            <main className="flex-1 p-6 flex items-center justify-center">
                {currentPhase === 'setup' && (
                    <div className="w-full max-w-3xl flex flex-col items-center">
                        <div className="w-full">
                            <UploadPanel onFormDataChange={setFormData} />
                        </div>
                        <button 
                            onClick={handleStartSetup}
                            disabled={!formData?.cvFile || isStarting}
                            className={`mt-8 px-8 py-3 rounded-lg text-white font-semibold text-lg transition-all shadow-md ${
                                !formData?.cvFile || isStarting 
                                ? 'bg-blue-300 cursor-not-allowed' 
                                : 'bg-blue-600 hover:bg-blue-700 hover:shadow-lg active:transform active:scale-95'
                            }`}
                        >
                            {isStarting ? 'Uploading...' : 'Begin Interview Setup'}
                        </button>
                    </div>
                )}

                {currentPhase === 'waiting' && (
                    <SetupProgress />
                )}

                {currentPhase === 'interview' && (
                    <div className="w-full h-full max-w-7xl mx-auto rounded-2xl overflow-hidden shadow-2xl border border-gray-800">
                        <InterviewRoom sessionId={sessionId} isDemo={true} />
                    </div>
                )}

                {currentPhase === 'report' && (
                    <div className="w-full max-w-5xl mx-auto bg-white rounded-xl shadow-xl overflow-hidden p-6 border border-gray-200">
                        <ReportViewer sessionId={sessionId} />
                    </div>
                )}
            </main>
        </div>
    );
};

export default App;
