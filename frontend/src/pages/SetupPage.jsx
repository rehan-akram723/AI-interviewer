// ─────────────────────────────────────────────────────────────────────────────
// frontend/src/pages/SetupPage.jsx
//
// The full setup page — two-column layout:
//   Left:  Hero copy + feature bullets
//   Right: Tabbed form (Upload → Configure → Launch)
// ─────────────────────────────────────────────────────────────────────────────

import React, { useState, useRef } from 'react';

const LENGTH_OPTIONS = [
    { value: 'short',  label: 'Short',  sub: '5–7 questions · ~10 min' },
    { value: 'medium', label: 'Medium', sub: '10–15 questions · ~20 min' },
    { value: 'long',   label: 'Long',   sub: '18–25 questions · ~40 min' },
];

const MODE_OPTIONS = [
    { value: 'mixed',         label: 'Mixed',          icon: '⚡', desc: 'Balanced across all question types' },
    { value: 'technical',     label: 'Technical',      icon: '💻', desc: '80% technical, 20% behavioral' },
    { value: 'behavioral',    label: 'Behavioral',     icon: '🧠', desc: '80% behavioral, 20% technical' },
    { value: 'system_design', label: 'System Design',  icon: '🏗',  desc: '90% architecture & design questions' },
    { value: 'hr_culture_fit',label: 'Culture Fit',    icon: '🤝', desc: '70% culture & motivation questions' },
];

const SetupPage = ({ onSubmit, isLoading, error }) => {
    const [step, setStep] = useState(0); // 0=upload, 1=configure
    const [cvFile, setCvFile] = useState(null);
    const [isDragging, setIsDragging] = useState(false);
    const [jobDescription, setJobDescription] = useState('');
    const [companyName, setCompanyName] = useState('');
    const [motivationLetter, setMotivationLetter] = useState('');
    const [interviewLength, setInterviewLength] = useState('medium');
    const [interviewMode, setInterviewMode] = useState('mixed');
    const fileInputRef = useRef(null);

    const handleFile = (file) => {
        if (!file) return;
        if (file.type !== 'application/pdf') {
            alert('Please select a PDF file.');
            return;
        }
        setCvFile(file);
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setIsDragging(false);
        const f = e.dataTransfer.files?.[0];
        if (f) handleFile(f);
    };

    const handleSubmit = () => {
        onSubmit(
            { cvFile, jobDescription, companyName, motivationLetter },
            { interviewLength, interviewMode }
        );
    };

    const canProceed = cvFile && jobDescription.trim().length > 10;

    // ── Shared input style ─────────────────────────────────────────────────────
    const inputStyle = {
        width: '100%',
        background: 'var(--bg-primary)',
        border: '1px solid var(--bg-border)',
        borderRadius: '8px',
        color: 'var(--text-primary)',
        fontFamily: 'inherit',
        fontSize: '0.9rem',
        padding: '0.7rem 1rem',
        transition: 'border-color 0.2s',
        boxSizing: 'border-box',
    };

    const labelStyle = {
        display: 'block',
        fontSize: '0.8125rem',
        fontWeight: 600,
        color: 'var(--text-secondary)',
        marginBottom: '6px',
        letterSpacing: '0.02em',
        textTransform: 'uppercase',
    };

    return (
        <div style={{
            minHeight: 'calc(100vh - 56px)',
            display: 'grid',
            gridTemplateColumns: '1fr 520px',
            overflow: 'hidden',
        }}>
            {/* ── LEFT: Hero ────────────────────────────────────────────────── */}
            <div style={{
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                padding: '4rem 5rem',
                background: 'var(--bg-surface)',
                borderRight: '1px solid var(--bg-border)',
            }}>
                <div style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '6px 14px',
                    background: 'rgba(59,130,246,0.1)',
                    border: '1px solid rgba(59,130,246,0.25)',
                    borderRadius: '999px',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    color: 'var(--accent-blue)',
                    width: 'fit-content',
                    marginBottom: '2rem',
                }}>
                    <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--accent-blue)', display: 'inline-block' }}></span>
                    AI-Powered Interview Practice
                </div>

                <h1 style={{
                    fontSize: '3rem',
                    fontWeight: 800,
                    lineHeight: 1.1,
                    letterSpacing: '-1.5px',
                    margin: '0 0 1.25rem',
                    background: 'linear-gradient(135deg, #fafafa 40%, #a1a1aa)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    backgroundClip: 'text',
                }}>
                    Ace your next<br />technical interview
                </h1>

                <p style={{ fontSize: '1.0625rem', color: 'var(--text-secondary)', lineHeight: 1.7, maxWidth: 440, margin: '0 0 2.5rem' }}>
                    Upload your CV and a job description. Our AI conducts a realistic interview, provides live coaching, and delivers a full performance report.
                </p>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    {[
                        { icon: '🎯', title: 'Personalised Questions', desc: 'Generated from your CV and the target role' },
                        { icon: '💬', title: 'Live Coaching Sidebar', desc: 'Real-time feedback on every answer you give' },
                        { icon: '📊', title: 'Detailed Score Report', desc: 'Scored across 6 performance dimensions' },
                    ].map(f => (
                        <div key={f.title} style={{ display: 'flex', gap: '14px', alignItems: 'flex-start' }}>
                            <span style={{
                                width: 38, height: 38, borderRadius: '10px',
                                background: 'var(--bg-elevated)',
                                border: '1px solid var(--bg-border)',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                fontSize: '1rem', flexShrink: 0,
                            }}>{f.icon}</span>
                            <div>
                                <div style={{ fontWeight: 600, fontSize: '0.9375rem', marginBottom: 2 }}>{f.title}</div>
                                <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>{f.desc}</div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* ── RIGHT: Form Panel ─────────────────────────────────────────── */}
            <div style={{
                background: 'var(--bg-primary)',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'auto',
                padding: '2.5rem 2rem',
                gap: '1.5rem',
            }}>
                {/* Step tabs */}
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '6px',
                    background: 'var(--bg-elevated)',
                    padding: '4px',
                    borderRadius: '10px',
                    border: '1px solid var(--bg-border)',
                }}>
                    {['Upload Details', 'Interview Settings'].map((label, i) => (
                        <button key={i} onClick={() => setStep(i)} style={{
                            padding: '9px',
                            border: 'none',
                            borderRadius: '7px',
                            fontFamily: 'inherit',
                            fontSize: '0.85rem',
                            fontWeight: step === i ? 600 : 400,
                            cursor: 'pointer',
                            transition: 'all 0.2s',
                            background: step === i ? 'var(--bg-surface)' : 'transparent',
                            color: step === i ? 'var(--text-primary)' : 'var(--text-muted)',
                            boxShadow: step === i ? '0 1px 4px rgba(0,0,0,0.3)' : 'none',
                        }}>{label}</button>
                    ))}
                </div>

                {/* ── Step 0: Upload Details ─────────────────────────────────── */}
                {step === 0 && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', animation: 'fadeInUp 0.3s ease both' }}>

                        {/* CV Drop Zone */}
                        <div>
                            <label style={labelStyle}>Curriculum Vitae <span style={{ color: 'var(--accent-red)' }}>*</span></label>
                            <div
                                onClick={() => fileInputRef.current?.click()}
                                onDrop={handleDrop}
                                onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                                onDragLeave={() => setIsDragging(false)}
                                style={{
                                    border: `2px dashed ${isDragging ? 'var(--accent-blue)' : cvFile ? 'var(--accent-emerald)' : 'var(--bg-border)'}`,
                                    borderRadius: '12px',
                                    padding: '2rem 1.5rem',
                                    cursor: 'pointer',
                                    textAlign: 'center',
                                    background: isDragging ? 'rgba(59,130,246,0.05)' : cvFile ? 'rgba(16,185,129,0.05)' : 'var(--bg-elevated)',
                                    transition: 'all 0.2s',
                                }}>
                                <input
                                    type="file"
                                    accept="application/pdf"
                                    ref={fileInputRef}
                                    style={{ display: 'none' }}
                                    onChange={(e) => handleFile(e.target.files?.[0])}
                                />
                                {cvFile ? (
                                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
                                        <div style={{
                                            width: 44, height: 44, borderRadius: '50%',
                                            background: 'rgba(16,185,129,0.15)',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                                        }}>
                                            <svg width="22" height="22" fill="none" stroke="#10b981" strokeWidth="2.5" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                                            </svg>
                                        </div>
                                        <span style={{ fontWeight: 600, color: 'var(--accent-emerald)', fontSize: '0.9rem' }}>
                                            {cvFile.name}
                                        </span>
                                        <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                                            {(cvFile.size / 1024).toFixed(1)} KB · Click to change
                                        </span>
                                    </div>
                                ) : (
                                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px' }}>
                                        <div style={{
                                            width: 44, height: 44, borderRadius: '50%',
                                            background: 'var(--bg-surface)',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                                            border: '1px solid var(--bg-border)',
                                        }}>
                                            <svg width="20" height="20" fill="none" stroke="var(--text-muted)" strokeWidth="1.75" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                            </svg>
                                        </div>
                                        <div>
                                            <div style={{ fontSize: '0.9rem', fontWeight: 500, color: 'var(--text-secondary)' }}>
                                                <span style={{ color: 'var(--accent-blue)', fontWeight: 600 }}>Click to upload</span> or drag & drop
                                            </div>
                                            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 4 }}>PDF only · max 10 MB</div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Job Description */}
                        <div>
                            <label style={labelStyle}>Job Description <span style={{ color: 'var(--accent-red)' }}>*</span></label>
                            <textarea
                                rows={6}
                                value={jobDescription}
                                onChange={(e) => setJobDescription(e.target.value)}
                                placeholder="Paste the full job description here. The AI uses it to generate relevant interview questions..."
                                style={{ ...inputStyle, resize: 'vertical', minHeight: '140px', lineHeight: 1.6 }}
                                onFocus={(e) => e.target.style.borderColor = 'var(--accent-blue)'}
                                onBlur={(e) => e.target.style.borderColor = 'var(--bg-border)'}
                            />
                        </div>

                        {/* Company Name */}
                        <div>
                            <label style={labelStyle}>Target Company <span style={{ color: 'var(--text-muted)', fontWeight: 400, textTransform: 'none' }}>(optional)</span></label>
                            <input
                                type="text"
                                value={companyName}
                                onChange={(e) => setCompanyName(e.target.value)}
                                placeholder="e.g. Google, OpenAI, Stripe"
                                style={inputStyle}
                                onFocus={(e) => e.target.style.borderColor = 'var(--accent-blue)'}
                                onBlur={(e) => e.target.style.borderColor = 'var(--bg-border)'}
                            />
                        </div>

                        {/* Motivation Letter */}
                        <div>
                            <label style={labelStyle}>Cover Letter / Motivation <span style={{ color: 'var(--text-muted)', fontWeight: 400, textTransform: 'none' }}>(optional)</span></label>
                            <textarea
                                rows={4}
                                value={motivationLetter}
                                onChange={(e) => setMotivationLetter(e.target.value)}
                                placeholder="Paste your cover letter or a brief motivation statement..."
                                style={{ ...inputStyle, resize: 'vertical', lineHeight: 1.6 }}
                                onFocus={(e) => e.target.style.borderColor = 'var(--accent-blue)'}
                                onBlur={(e) => e.target.style.borderColor = 'var(--bg-border)'}
                            />
                        </div>

                        <button
                            onClick={() => setStep(1)}
                            disabled={!canProceed}
                            style={{
                                padding: '0.75rem',
                                background: canProceed ? 'var(--accent-blue)' : 'var(--bg-elevated)',
                                color: canProceed ? '#fff' : 'var(--text-muted)',
                                border: 'none',
                                borderRadius: '9px',
                                fontFamily: 'inherit',
                                fontSize: '0.9375rem',
                                fontWeight: 600,
                                cursor: canProceed ? 'pointer' : 'not-allowed',
                                transition: 'all 0.2s',
                            }}>
                            Continue to Interview Settings →
                        </button>
                    </div>
                )}

                {/* ── Step 1: Configure ──────────────────────────────────────── */}
                {step === 1 && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', animation: 'fadeInUp 0.3s ease both' }}>

                        {/* Interview Length */}
                        <div>
                            <label style={labelStyle}>Interview Length</label>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                {LENGTH_OPTIONS.map(opt => (
                                    <button key={opt.value} onClick={() => setInterviewLength(opt.value)} style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'space-between',
                                        padding: '0.875rem 1.125rem',
                                        background: interviewLength === opt.value ? 'rgba(59,130,246,0.12)' : 'var(--bg-elevated)',
                                        border: `1px solid ${interviewLength === opt.value ? 'var(--accent-blue)' : 'var(--bg-border)'}`,
                                        borderRadius: '9px',
                                        cursor: 'pointer',
                                        textAlign: 'left',
                                        fontFamily: 'inherit',
                                        transition: 'all 0.15s',
                                        width: '100%',
                                    }}>
                                        <div>
                                            <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)' }}>{opt.label}</div>
                                            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 2 }}>{opt.sub}</div>
                                        </div>
                                        <div style={{
                                            width: 18, height: 18, borderRadius: '50%',
                                            border: `2px solid ${interviewLength === opt.value ? 'var(--accent-blue)' : 'var(--bg-muted)'}`,
                                            background: interviewLength === opt.value ? 'var(--accent-blue)' : 'transparent',
                                            flexShrink: 0,
                                        }}></div>
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Interview Mode */}
                        <div>
                            <label style={labelStyle}>Interview Mode</label>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                {MODE_OPTIONS.map(opt => (
                                    <button key={opt.value} onClick={() => setInterviewMode(opt.value)} style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '12px',
                                        padding: '0.875rem 1.125rem',
                                        background: interviewMode === opt.value ? 'rgba(59,130,246,0.12)' : 'var(--bg-elevated)',
                                        border: `1px solid ${interviewMode === opt.value ? 'var(--accent-blue)' : 'var(--bg-border)'}`,
                                        borderRadius: '9px',
                                        cursor: 'pointer',
                                        textAlign: 'left',
                                        fontFamily: 'inherit',
                                        transition: 'all 0.15s',
                                        width: '100%',
                                    }}>
                                        <span style={{ fontSize: '1.25rem' }}>{opt.icon}</span>
                                        <div style={{ flex: 1 }}>
                                            <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)' }}>{opt.label}</div>
                                            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 2 }}>{opt.desc}</div>
                                        </div>
                                        <div style={{
                                            width: 18, height: 18, borderRadius: '50%',
                                            border: `2px solid ${interviewMode === opt.value ? 'var(--accent-blue)' : 'var(--bg-muted)'}`,
                                            background: interviewMode === opt.value ? 'var(--accent-blue)' : 'transparent',
                                            flexShrink: 0,
                                        }}></div>
                                    </button>
                                ))}
                            </div>
                        </div>

                        {error && (
                            <div style={{
                                padding: '0.875rem 1rem',
                                background: 'rgba(239,68,68,0.1)',
                                border: '1px solid rgba(239,68,68,0.3)',
                                borderRadius: '9px',
                                color: '#fca5a5',
                                fontSize: '0.875rem',
                            }}>
                                {error}
                            </div>
                        )}

                        <button
                            onClick={handleSubmit}
                            disabled={isLoading}
                            style={{
                                padding: '0.9rem',
                                background: isLoading ? 'var(--bg-elevated)' : 'linear-gradient(135deg, #3b82f6, #6366f1)',
                                color: isLoading ? 'var(--text-muted)' : '#fff',
                                border: 'none',
                                borderRadius: '9px',
                                fontFamily: 'inherit',
                                fontSize: '1rem',
                                fontWeight: 700,
                                cursor: isLoading ? 'not-allowed' : 'pointer',
                                letterSpacing: '-0.2px',
                                boxShadow: isLoading ? 'none' : '0 4px 20px rgba(99,102,241,0.3)',
                                transition: 'all 0.2s',
                            }}>
                            {isLoading ? 'Uploading & Analysing...' : '🚀  Begin Interview Setup'}
                        </button>

                        <button onClick={() => setStep(0)} style={{
                            background: 'none', border: 'none', color: 'var(--text-muted)',
                            fontSize: '0.85rem', cursor: 'pointer', fontFamily: 'inherit', padding: 0,
                        }}>
                            ← Back to upload details
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
};

export default SetupPage;
