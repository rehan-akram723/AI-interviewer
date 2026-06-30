import React, { createContext, useContext, useState } from 'react';

const SessionContext = createContext();

export const SessionProvider = ({ children }) => {
    const [sessionId, setSessionId] = useState(null);
    const [candidateId, setCandidateId] = useState(null);
    const [appMode, setAppMode] = useState('demo');
    const [currentPhase, setCurrentPhase] = useState('setup'); // setup -> waiting -> interview -> report
    const [interviewLength, setInterviewLength] = useState('medium');
    const [interviewMode, setInterviewMode] = useState('mixed');
    const [candidateName, setCandidateName] = useState('');

    const value = {
        sessionId,
        setSessionId,
        candidateId,
        setCandidateId,
        appMode,
        setAppMode,
        currentPhase,
        setCurrentPhase,
        interviewLength,
        setInterviewLength,
        interviewMode,
        setInterviewMode,
        candidateName,
        setCandidateName,
    };

    return (
        <SessionContext.Provider value={value}>
            {children}
        </SessionContext.Provider>
    );
};

export const useSession = () => useContext(SessionContext);
