// ─────────────────────────────────────────────────────────────────────────────
// frontend/src/hooks/useWebSocket.js
//
// Resilient WebSocket connection manager for the live interview session.
// Automatically reconnects on dropped handshakes with exponential backoff.
// Parses server-push message types and hydrates local state accordingly.
// ─────────────────────────────────────────────────────────────────────────────

import { useState, useEffect, useRef, useCallback } from 'react';

const WS_BASE_URL = 'ws://localhost:8000/ws/interview';
const MAX_RETRY_ATTEMPTS = 5;
const INITIAL_RETRY_DELAY_MS = 1000;

const useWebSocket = (sessionId) => {
    const [isConnected, setIsConnected] = useState(false);
    const [coachingFeedback, setCoachingFeedback] = useState([]);
    const [difficultyMetrics, setDifficultyMetrics] = useState({
        difficultyLevel: 1,
        difficultyDimensions: {}
    });
    const [connectionError, setConnectionError] = useState(null);

    const socketRef = useRef(null);
    const retryCountRef = useRef(0);
    const retryTimerRef = useRef(null);
    const isMountedRef = useRef(true);

    const handleMessage = useCallback((event) => {
        try {
            const message = JSON.parse(event.data);
            const { type, payload } = message;

            if (type === 'coaching_feedback') {
                setCoachingFeedback((prev) => [...prev, payload]);
            } else if (type === 'difficulty_update') {
                setDifficultyMetrics({
                    difficultyLevel: payload.difficultyLevel ?? 1,
                    difficultyDimensions: payload.difficultyDimensions ?? {}
                });
            }
        } catch (err) {
            console.error('[useWebSocket] Failed to parse server message:', err);
        }
    }, []);

    const connect = useCallback(() => {
        if (!sessionId || !isMountedRef.current) return;

        const wsUrl = `${WS_BASE_URL}/${sessionId}`;
        const socket = new WebSocket(wsUrl);
        socketRef.current = socket;

        socket.onopen = () => {
            if (!isMountedRef.current) return;
            console.log('[useWebSocket] Connected to', wsUrl);
            setIsConnected(true);
            setConnectionError(null);
            retryCountRef.current = 0;
        };

        socket.onmessage = handleMessage;

        socket.onclose = (event) => {
            if (!isMountedRef.current) return;
            setIsConnected(false);

            // Do not retry if closed cleanly or max attempts reached
            if (event.wasClean || retryCountRef.current >= MAX_RETRY_ATTEMPTS) {
                if (retryCountRef.current >= MAX_RETRY_ATTEMPTS) {
                    setConnectionError(
                        `Connection lost after ${MAX_RETRY_ATTEMPTS} attempts. Please refresh.`
                    );
                }
                return;
            }

            // Exponential backoff: 1s, 2s, 4s, 8s, 16s
            const delay = INITIAL_RETRY_DELAY_MS * Math.pow(2, retryCountRef.current);
            retryCountRef.current += 1;
            console.log(
                `[useWebSocket] Disconnected. Retry ${retryCountRef.current}/${MAX_RETRY_ATTEMPTS} in ${delay}ms.`
            );

            retryTimerRef.current = setTimeout(connect, delay);
        };

        socket.onerror = (err) => {
            console.error('[useWebSocket] WebSocket error:', err);
        };
    }, [sessionId, handleMessage]);

    useEffect(() => {
        isMountedRef.current = true;
        connect();

        return () => {
            isMountedRef.current = false;
            clearTimeout(retryTimerRef.current);
            if (socketRef.current) {
                // Force a clean close so the onclose handler does not trigger reconnect
                socketRef.current.close(1000, 'Component unmounted');
            }
        };
    }, [connect]);

    const sendMessage = useCallback((messageObj) => {
        if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
            socketRef.current.send(JSON.stringify(messageObj));
        } else {
            console.warn('[useWebSocket] Cannot send — socket is not open.');
        }
    }, []);

    return {
        isConnected,
        coachingFeedback,
        difficultyMetrics,
        connectionError,
        sendMessage
    };
};

export default useWebSocket;
