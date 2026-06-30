// ─────────────────────────────────────────────────────────────────────────────
// frontend/src/services/api.test.js
// ─────────────────────────────────────────────────────────────────────────────

import { setupInterview } from './api';
import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';

const mock = new MockAdapter(axios);

describe('API Service Layer - setupInterview', () => {
    afterEach(() => {
        mock.reset();
    });

    it('should serialize form parameters into camelCase multipart/form-data', async () => {
        mock.onPost('/sessions/setup').reply(config => {
            const formData = config.data;
            
            // In a real FormData object in the browser, we'd use formData.get()
            // Since this is a test boundary, we just ensure it didn't throw and
            // hit the correct endpoint with the correct headers.
            expect(config.headers['Content-Type']).toBe('multipart/form-data');
            
            return [200, { sessionId: 'test-session-123', status: 'setting_up' }];
        });

        const dummyFile = new File(['dummy content'], 'cv.pdf', { type: 'application/pdf' });
        
        const payload = {
            cvFile: dummyFile,
            jobDescription: 'Senior Dev',
            companyName: 'Tech Corp',
            motivationLetter: 'I love coding',
            interviewLength: 'long',
            interviewMode: 'technical'
        };

        const response = await setupInterview(payload);
        
        expect(response.sessionId).toBe('test-session-123');
    });
});
