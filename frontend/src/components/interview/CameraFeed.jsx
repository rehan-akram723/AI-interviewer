import React from 'react';

const CameraFeed = ({ isDemo, cameraRef, difficultyMetrics }) => {
    return (
        <aside className="w-64 flex-shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col items-center justify-center p-4 space-y-6">
            {isDemo ? (
                <div className="w-full aspect-video rounded-xl bg-gray-800 border-2 border-dashed border-gray-600 flex flex-col items-center justify-center space-y-2 shadow-inner">
                    <svg className="w-10 h-10 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M3 8a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z" />
                    </svg>
                    <p className="text-xs text-gray-500 text-center font-medium">Camera disabled in demo mode</p>
                </div>
            ) : (
                <video
                    ref={cameraRef}
                    className="w-full aspect-video rounded-xl bg-black object-cover shadow-lg border border-gray-700"
                    autoPlay
                    muted
                    playsInline
                />
            )}

            {/* Difficulty axis pills */}
            {difficultyMetrics && Object.keys(difficultyMetrics.difficultyDimensions || {}).length > 0 && (
                <div className="w-full space-y-2 mt-4 bg-gray-800/50 p-3 rounded-lg border border-gray-700">
                    <p className="text-xs text-gray-400 font-semibold uppercase tracking-wider mb-2">Difficulty Axes</p>
                    {Object.entries(difficultyMetrics.difficultyDimensions).map(([dim, val]) => (
                        <div key={dim} className="flex items-center justify-between text-xs">
                            <span className="text-gray-300 capitalize">{dim}</span>
                            <div className="flex items-center gap-2">
                                <div className="w-16 bg-gray-700 rounded-full h-1.5">
                                    <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: `${(val / 5) * 100}%` }}></div>
                                </div>
                                <span className="text-white font-mono">{val}/5</span>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </aside>
    );
};

export default CameraFeed;
