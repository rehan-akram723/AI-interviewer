// ─────────────────────────────────────────────────────────────────────────────
// frontend/src/hooks/useAudioRecorder.js
//
// Manages the microphone capture lifecycle using MediaRecorder API.
//
// Demo mode: isDemo=true — all handlers are no-ops, no permissions requested.
// Production: Manages isRecording state, accumulates audio chunks, and
//             compiles a clean Blob when recording stops.
//
// FIX: Removed conditional early return that violated Rules of Hooks.
//      All hooks are now called unconditionally; isDemo gates behaviour inside.
// ─────────────────────────────────────────────────────────────────────────────

import { useState, useRef, useCallback } from 'react';

const useAudioRecorder = (isDemo = true) => {
    const [isRecording, setIsRecording] = useState(false);
    const [audioBlob, setAudioBlob] = useState(null);
    const [permissionError, setPermissionError] = useState(null);

    const mediaRecorderRef = useRef(null);
    const audioChunksRef = useRef([]);
    const streamRef = useRef(null);
    const isRecordingRef = useRef(false); // mirrors state for use inside closures

    // ── Start recording ───────────────────────────────────────────────────────
    const startRecording = useCallback(async () => {
        if (isDemo) return;
        if (isRecordingRef.current) return;

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

            mediaRecorder.start(250); // Emit a chunk every 250 ms
            isRecordingRef.current = true;
            setIsRecording(true);
        } catch (err) {
            console.error('[useAudioRecorder] Microphone access denied:', err);
            setPermissionError(
                'Microphone access was denied. Please allow microphone access and try again.'
            );
        }
    }, [isDemo]); // stable — no longer depends on isRecording state

    // ── Stop recording ────────────────────────────────────────────────────────
    const stopRecording = useCallback(() => {
        if (isDemo) return;
        if (!isRecordingRef.current || !mediaRecorderRef.current) return;

        if (mediaRecorderRef.current.state !== 'inactive') {
            mediaRecorderRef.current.stop();
        }
        isRecordingRef.current = false;
        setIsRecording(false);
    }, [isDemo]);

    // ── Clear blob ────────────────────────────────────────────────────────────
    const clearAudioBlob = useCallback(() => {
        setAudioBlob(null);
    }, []);

    // ── Demo short-circuit output (hooks already ran above) ───────────────────
    if (isDemo) {
        return {
            isRecording: false,
            audioBlob: null,
            permissionError: null,
            startRecording,
            stopRecording,
            clearAudioBlob,
        };
    }

    return {
        isRecording,
        audioBlob,
        permissionError,
        startRecording,
        stopRecording,
        clearAudioBlob,
    };
};

export default useAudioRecorder;
