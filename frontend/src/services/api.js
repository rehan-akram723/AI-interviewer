// ─────────────────────────────────────────────────────────────────────────────
// frontend/src/services/api.js
// ─────────────────────────────────────────────────────────────────────────────

import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

const apiClient = axios.create({
    baseURL: API_BASE_URL,
});

/**
 * Initializes a new interview session by uploading the candidate's CV and configuring
 * the session constraints (mode, length).
 * 
 * Uses multipart/form-data because the CV is uploaded as a PDF file.
 * The keys use camelCase naming convention as requested by the architecture.
 */
export const setupInterview = async (setupData) => {
    const formData = new FormData();
    
    // File upload
    if (setupData.cvFile) {
        formData.append('cvFile', setupData.cvFile);
    }
    
    // Raw text configurations
    formData.append('jobDescription', setupData.jobDescription || '');
    formData.append('companyName', setupData.companyName || '');
    formData.append('motivationLetter', setupData.motivationLetter || '');
    
    // Interview configuration dropdowns
    formData.append('interviewLength', setupData.interviewLength || 'medium');
    formData.append('interviewMode', setupData.interviewMode || 'mixed');

    const response = await apiClient.post('/sessions/setup', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });
    return response.data;
};

/**
 * Polls the backend for the status of the setup process (e.g. CV parsing).
 */
export const getSetupStatus = async (sessionId) => {
    const response = await apiClient.get(`/sessions/${sessionId}/status`);
    return response.data;
};

/**
 * Retrieves the history of all sessions for a specific candidate dashboard.
 */
export const getCandidateSessions = async (candidateId) => {
    const response = await apiClient.get(`/candidates/${candidateId}/sessions`);
    return response.data;
};
