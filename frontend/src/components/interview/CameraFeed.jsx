// ─────────────────────────────────────────────────────────────────────────────
// frontend/src/components/interview/CameraFeed.jsx
//
// Camera feed — renders a live webcam stream.
// When `fullscreen` prop is true, fills the entire parent container.
// ─────────────────────────────────────────────────────────────────────────────

import React, { useEffect, useRef, useImperativeHandle, forwardRef, useState } from "react";

const CameraFeed = forwardRef(({ isDemo = true, fullscreen = false }, ref) => {
    const videoRef = useRef(null);
    const canvasRef = useRef(null);
    const streamRef = useRef(null);
    const [hasCamera, setHasCamera] = useState(false);
    const [error, setError] = useState(null);

    useImperativeHandle(ref, () => ({
        captureFrame: () => {
            if (!videoRef.current || !canvasRef.current || !hasCamera) return null;
            const video = videoRef.current;
            const canvas = canvasRef.current;
            canvas.width = video.videoWidth || 320;
            canvas.height = video.videoHeight || 240;
            canvas.getContext("2d").drawImage(video, 0, 0);
            return canvas.toDataURL("image/jpeg", 0.7);
        },
    }));

    useEffect(() => {
        if (isDemo) return;
        let active = true;

        const startCamera = async () => {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({
                    video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" },
                    audio: false,
                });
                if (!active) { stream.getTracks().forEach(t => t.stop()); return; }
                streamRef.current = stream;
                if (videoRef.current) {
                    videoRef.current.srcObject = stream;
                    videoRef.current.onloadedmetadata = () => {
                        videoRef.current.play().catch(() => {});
                        setHasCamera(true);
                    };
                }
            } catch (err) {
                if (active) setError(err.name === "NotFoundError" ? "No camera found." : "Camera access denied.");
            }
        };

        startCamera();
        return () => {
            active = false;
            streamRef.current?.getTracks().forEach(t => t.stop());
        };
    }, [isDemo]);

    const containerClass = fullscreen
        ? "absolute inset-0 w-full h-full"
        : "relative w-full h-full rounded-2xl overflow-hidden";

    if (isDemo) {
        return (
            <div className={containerClass} style={{ background: "linear-gradient(135deg, #0a0f1e 0%, #0d1530 50%, #070c1a 100%)" }}>
                {/* Animated placeholder grid */}
                <svg className="absolute inset-0 w-full h-full opacity-[0.04]" xmlns="http://www.w3.org/2000/svg">
                    <defs>
                        <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="white" strokeWidth="0.5" />
                        </pattern>
                    </defs>
                    <rect width="100%" height="100%" fill="url(#grid)" />
                </svg>
                {/* Demo silhouette */}
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
                    <div className="w-28 h-28 rounded-full bg-white/5 border border-white/10 flex items-center justify-center">
                        <svg width="56" height="56" fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth="1.5" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                    </div>
                    <p className="text-[11px] text-white/20 font-medium tracking-wider uppercase">Demo Mode</p>
                </div>
                {/* Subtle corner glow */}
                <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-96 h-48 bg-blue-600/10 blur-[80px] rounded-full pointer-events-none" />
            </div>
        );
    }

    return (
        <div className={containerClass} style={fullscreen ? {} : { background: "#000" }}>
            {error ? (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-slate-950">
                    <div className="w-12 h-12 rounded-xl bg-red-500/10 flex items-center justify-center">
                        <svg width="22" height="22" fill="none" stroke="#f87171" strokeWidth="2" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M15 10l4.553-2.069A1 1 0 0121 8.868v6.264a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                    </div>
                    <p className="text-[12px] text-red-400 font-medium">{error}</p>
                </div>
            ) : (
                <video
                    ref={videoRef}
                    autoPlay
                    muted
                    playsInline
                    className="absolute inset-0 w-full h-full object-cover"
                    style={{ transform: "scaleX(-1)" }}  // mirror
                />
            )}
            <canvas ref={canvasRef} className="hidden" />
        </div>
    );
});

CameraFeed.displayName = "CameraFeed";
export default CameraFeed;
