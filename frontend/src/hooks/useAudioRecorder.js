// ─────────────────────────────────────────────────────────────────────────────
// frontend/src/hooks/useAudioRecorder.js
//
// Manages the microphone capture lifecycle using MediaRecorder API.
//
// Demo mode: Completely short-circuits — no device permissions requested,
//            no MediaRecorder instantiated. All returned handlers are no-ops.
// Production: Manages isRecording state, accumulates audio chunks, and
//             compiles a clean Blob when recording stops.
// ─────────────────────────────────────────────────────────────────────────────

import { useState, useRef, useCallback } from 'react';

const useAudioRecorder = (isDemo = true) => {
    const [isRecording, setIsRecording] = useState(false);
    const [audioBlob, setAudioBlob] = useState(null);
    const [permissionError, setPermissionError] = useState(null);

    const mediaRecorderRef = useRef(null);
    const audioChunksRef = useRef([]);
    const streamRef = useRef(null);

    // ── Demo mode short-circuit ────────────────────────────────────────────────
    if (isDemo) {
        return {
            isRecording: false,
            audioBlob: null,
            permissionError: null,
            startRecording: () => {},
            stopRecording: () => {},
            clearAudioBlob: () => {}
        };
    }

    // ── Production recording state machine ────────────────────────────────────
    const startRecording = useCallback(async () => {
        if (isRecording) return;

        try {
            setPermissionError(null);
            audioChunksRef.current = [];
            setAudioBlob(null);

            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            streamRef.current = stream;

            const mediaRecorder = new MediaRecorder(stream);
            mediaRecorderRef.current = mediaRecorder;

            mediaRecorder.ondataavailable = (event) => {
                if (event.data && event.data.size > 0) {
                    audioChunksRef.current.push(event.data);
                }
            };

            mediaRecorder.onstop = () => {
                const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
                setAudioBlob(blob);
                audioChunksRef.current = [];

                // Stop all mic tracks to release the device
                if (streamRef.current) {
                    streamRef.current.getTracks().forEach((track) => track.stop());
                    streamRef.current = null;
                }
            };

            mediaRecorder.start(250); // Emit a chunk every 250ms
            setIsRecording(true);
        } catch (err) {
            console.error('[useAudioRecorder] Microphone access denied:', err);
            setPermissionError(
                'Microphone access was denied. Please allow microphone access and try again.'
            );
        }
    }, [isRecording]);

    const stopRecording = useCallback(() => {
        if (!isRecording || !mediaRecorderRef.current) return;

        if (mediaRecorderRef.current.state !== 'inactive') {
            mediaRecorderRef.current.stop();
        }
        setIsRecording(false);
    }, [isRecording]);

    const clearAudioBlob = useCallback(() => {
        setAudioBlob(null);
    }, []);

    return {
        isRecording,
        audioBlob,
        permissionError,
        startRecording,
        stopRecording,
        clearAudioBlob
    };
};

export default useAudioRecorder;
