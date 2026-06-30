// ─────────────────────────────────────────────────────────────────────────────
// frontend/src/components/setup/UploadPanel.jsx
// ─────────────────────────────────────────────────────────────────────────────

import React, { useState, useRef } from 'react';

const UploadPanel = ({ onFormDataChange, initialData = {} }) => {
    const [cvFile, setCvFile] = useState(initialData.cvFile || null);
    const [companyName, setCompanyName] = useState(initialData.companyName || '');
    const [jobDescription, setJobDescription] = useState(initialData.jobDescription || '');
    const [motivationLetter, setMotivationLetter] = useState(initialData.motivationLetter || '');
    const [isDragging, setIsDragging] = useState(false);
    const fileInputRef = useRef(null);

    const handleFileChange = (file) => {
        if (file && file.type === 'application/pdf') {
            setCvFile(file);
            notifyParent(file, companyName, jobDescription, motivationLetter);
        } else {
            alert('Please upload a valid PDF file for the CV.');
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setIsDragging(false);
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleFileChange(e.dataTransfer.files[0]);
        }
    };

    const handleDragOver = (e) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = (e) => {
        e.preventDefault();
        setIsDragging(false);
    };

    const notifyParent = (file, company, jd, motivation) => {
        if (onFormDataChange) {
            onFormDataChange({
                cvFile: file,
                companyName: company,
                jobDescription: jd,
                motivationLetter: motivation,
            });
        }
    };

    return (
        <div className="bg-white p-6 rounded-lg shadow-md max-w-3xl mx-auto space-y-6">
            <h2 className="text-2xl font-bold text-gray-800">Candidate Setup</h2>
            
            {/* CV Drop Zone */}
            <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">Upload CV (PDF)</label>
                <div 
                    className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer ${isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-blue-400 bg-gray-50'}`}
                    onDrop={handleDrop}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onClick={() => fileInputRef.current?.click()}
                >
                    <input 
                        type="file" 
                        accept="application/pdf"
                        className="hidden" 
                        ref={fileInputRef}
                        onChange={(e) => handleFileChange(e.target.files[0])}
                    />
                    <div className="flex flex-col items-center space-y-2">
                        <svg className="w-10 h-10 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                        </svg>
                        <p className="text-sm text-gray-600">
                            <span className="font-semibold text-blue-600">Click to upload</span> or drag and drop
                        </p>
                        {cvFile && (
                            <p className="text-sm font-semibold text-green-600 mt-2">
                                Selected: {cvFile.name}
                            </p>
                        )}
                    </div>
                </div>
            </div>

            {/* Company Name */}
            <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">Company Name (Optional)</label>
                <input 
                    type="text" 
                    className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
                    placeholder="e.g. OpenAI"
                    value={companyName}
                    onChange={(e) => {
                        setCompanyName(e.target.value);
                        notifyParent(cvFile, e.target.value, jobDescription, motivationLetter);
                    }}
                />
            </div>

            {/* Job Description */}
            <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">Job Description (Raw Text)</label>
                <textarea 
                    className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all h-32 resize-y"
                    placeholder="Paste the target job description here..."
                    value={jobDescription}
                    onChange={(e) => {
                        setJobDescription(e.target.value);
                        notifyParent(cvFile, companyName, e.target.value, motivationLetter);
                    }}
                />
            </div>

            {/* Motivation Letter */}
            <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">Motivation Letter (Optional)</label>
                <textarea 
                    className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all h-32 resize-y"
                    placeholder="Paste any cover letter or motivational text..."
                    value={motivationLetter}
                    onChange={(e) => {
                        setMotivationLetter(e.target.value);
                        notifyParent(cvFile, companyName, jobDescription, e.target.value);
                    }}
                />
            </div>
        </div>
    );
};

export default UploadPanel;
