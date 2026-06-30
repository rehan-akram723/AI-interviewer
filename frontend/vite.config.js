import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],

    // Dev server proxy: Forwards /api and /ws calls to the FastAPI backend.
    // This eliminates CORS issues during local development without requiring
    // changes to either server. In production (Vercel/Render), the backend
    // URL is injected as VITE_API_BASE_URL env var.
    server: {
        port: 5173,
        proxy: {
            '/api': {
                target: 'http://localhost:8000',
                changeOrigin: true,
                secure: false,
            },
            '/ws': {
                target: 'ws://localhost:8000',
                ws: true,
                changeOrigin: true,
            },
        },
    },

    // Production build output
    build: {
        outDir: 'dist',
        sourcemap: false,        // No sourcemaps in production (faster deploys)
        chunkSizeWarningLimit: 1200, // Adjust for vendor chunk visibility
        rollupOptions: {
            output: {
                manualChunks: {
                    vendor: ['react', 'react-dom', 'axios'],
                },
            },
        },
    },

    // Environment variable prefix for client-side exposure
    // Usage: import.meta.env.VITE_API_BASE_URL
    envPrefix: 'VITE_',
});
