import React, { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

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

const containerVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { staggerChildren: 0.1 } }
};

const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 300, damping: 24 } }
};

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
            { interviewLength, interviewMode, appMode: 'production' }
        );
    };

    const canProceed = cvFile && jobDescription.trim().length > 10;

    const inputClass = "w-full bg-slate-900/50 border border-slate-700/50 rounded-[12px] text-slate-100 placeholder:text-slate-500 font-sans text-sm px-4 py-3.5 transition-all duration-300 focus:outline-none focus:border-accent-blue focus:ring-1 focus:ring-accent-blue/50 focus:bg-slate-900 shadow-inner";
    
    const labelClass = "block text-[11px] font-bold text-slate-400 mb-2 tracking-[0.1em] uppercase";

    const handleQuickStartDemo = () => {
        const cvText = `
REHAN AKRAM
Systems-Focused Software Engineer
rehan.akram@outlook.com | +92 314 4723778

CAREER SUMMARY:
Computer Science student and developer blending technical insight with systems-oriented design to craft functional, user-focused products. Experienced in full-stack development with Java and Spring Boot, game development, and distributed systems.

SKILLS:
Core Development: Java, Spring Boot, MySQL, C/C++, RISC-V Assembly.
Web & Systems: Full-stack development, System-oriented design, Distributed systems.
Design & Tools: UX/Product Design, Git, VS Code, Linux, IntelliJ IDEA.
Specialized: Game development, CI/CD logic, Parallel computing (OpenMP).
        `;
        const blob = new Blob([cvText], { type: 'application/pdf' });
        const dummyFile = new File([blob], 'rehan_akram_cv.pdf', { type: 'application/pdf' });
        
        onSubmit(
            { cvFile: dummyFile, jobDescription: 'AI/ML Engineer. Looking for someone with experience in Machine Learning, Python, scalable architecture, and full-stack development.', companyName: 'Demo Company', motivationLetter: '' },
            { interviewLength: 'short', interviewMode: 'technical', appMode: 'demo' }
        );
    };

    return (
        <div className="h-full grid grid-cols-1 lg:grid-cols-2 relative z-10">
            {/* ── LEFT: Hero ────────────────────────────────────────────────── */}
            <div className="flex flex-col justify-center px-12 lg:px-24 py-16 relative">
                {/* Organic shapes behind hero */}
                <div className="absolute top-1/4 left-1/4 w-64 h-64 bg-accent-blue/20 rounded-full blur-[80px] -z-10 mix-blend-screen animate-blob"></div>
                
                <motion.div initial="hidden" animate="visible" variants={containerVariants} className="max-w-[480px]">
                    <motion.div variants={itemVariants} className="inline-flex items-center gap-2 px-4 py-2 glass rounded-full text-xs font-bold text-accent-blue mb-8 backdrop-blur-md border border-accent-blue/20">
                        <span className="w-2 h-2 rounded-full bg-accent-blue animate-pulse-slow"></span>
                        AI-Powered Interview Practice
                    </motion.div>

                    <motion.h1 variants={itemVariants} className="text-5xl lg:text-7xl font-extrabold leading-[1.05] tracking-tight mb-6 gradient-text">
                        Ace your next<br />technical role
                    </motion.h1>

                    <motion.p variants={itemVariants} className="text-lg text-slate-400 leading-relaxed mb-12 font-light">
                        Upload your CV and a job description. Our AI conducts a realistic interview, provides live coaching, and delivers a full performance report.
                    </motion.p>

                    <motion.div variants={containerVariants} className="flex flex-col gap-6 mb-12">
                        {[
                            { icon: '🎯', title: 'Personalised Questions', desc: 'Generated from your CV and the target role' },
                            { icon: '💬', title: 'Live Coaching Sidebar', desc: 'Real-time feedback on every answer you give' },
                            { icon: '📊', title: 'Detailed Score Report', desc: 'Scored across 6 performance dimensions' },
                        ].map((f, i) => (
                            <motion.div key={f.title} variants={itemVariants} className="group flex gap-4 items-start">
                                <div className="w-12 h-12 rounded-2xl glass flex items-center justify-center text-xl shrink-0 transition-transform duration-500 group-hover:scale-110 group-hover:bg-slate-800/80">
                                    {f.icon}
                                </div>
                                <div>
                                    <div className="font-bold text-slate-200 mb-1 tracking-tight transition-colors duration-300 group-hover:text-white">{f.title}</div>
                                    <div className="text-sm text-slate-500 leading-relaxed">{f.desc}</div>
                                </div>
                            </motion.div>
                        ))}
                    </motion.div>

                    <motion.button
                        variants={itemVariants}
                        onClick={handleQuickStartDemo}
                        disabled={isLoading}
                        className="group relative px-8 py-4 rounded-full overflow-hidden font-bold tracking-wide w-fit transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <div className="absolute inset-0 bg-slate-900 border border-slate-700 rounded-full transition-colors duration-300 group-hover:bg-slate-800"></div>
                        <div className="absolute inset-0 opacity-0 group-hover:opacity-100 bg-gradient-to-r from-accent-blue/20 to-accent-purple/20 transition-opacity duration-500 rounded-full"></div>
                        <span className="relative z-10 flex items-center gap-3 text-slate-300 group-hover:text-white transition-colors duration-300">
                            <span className="text-xl group-hover:rotate-12 transition-transform duration-300">⚡</span> 
                            Quick Start Demo
                        </span>
                    </motion.button>
                </motion.div>
            </div>

            {/* ── RIGHT: Form Panel ─────────────────────────────────────────── */}
            <div className="flex flex-col justify-center px-8 lg:px-20 py-10 relative z-10">
                <div className="glass-panel p-8 lg:p-10 rounded-[2rem] relative overflow-hidden shadow-2xl">
                    
                    {/* Step tabs */}
                    <div className="flex gap-2 p-1.5 bg-slate-900/60 backdrop-blur-md rounded-2xl border border-slate-800/50 mb-8 relative z-20">
                        {['Upload Details', 'Interview Settings'].map((label, i) => (
                            <button 
                                key={i} 
                                onClick={() => setStep(i)} 
                                className={`flex-1 py-3 rounded-xl text-sm font-bold tracking-wide transition-all duration-300 relative ${
                                    step === i ? 'text-white shadow-lg' : 'text-slate-500 hover:text-slate-300'
                                }`}
                            >
                                {step === i && (
                                    <motion.div 
                                        layoutId="activeTab" 
                                        className="absolute inset-0 bg-slate-800 rounded-xl -z-10 border border-slate-700/50"
                                        transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                                    />
                                )}
                                {label}
                            </button>
                        ))}
                    </div>

                    <div className="relative z-20">
                        <AnimatePresence mode="wait">
                            {/* ── Step 0: Upload Details ─────────────────────────────────── */}
                            {step === 0 && (
                                <motion.div 
                                    key="step0"
                                    initial={{ opacity: 0, x: -20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    exit={{ opacity: 0, x: 20 }}
                                    transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                                    className="flex flex-col gap-6"
                                >
                                    {/* CV Drop Zone */}
                                    <div className="group relative">
                                        <label className={labelClass}>Curriculum Vitae <span className="text-accent-red">*</span></label>
                                        <div
                                            onClick={() => fileInputRef.current?.click()}
                                            onDrop={handleDrop}
                                            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                                            onDragLeave={() => setIsDragging(false)}
                                            className={`relative overflow-hidden border-2 border-dashed rounded-[1rem] p-8 text-center cursor-pointer transition-all duration-500 ${
                                                isDragging ? 'border-accent-blue bg-accent-blue/5' : 
                                                cvFile ? 'border-accent-emerald bg-accent-emerald/5' : 
                                                'border-slate-700/50 bg-slate-900/50 hover:border-slate-500 hover:bg-slate-800/50'
                                            }`}
                                        >
                                            <input
                                                type="file"
                                                accept="application/pdf"
                                                ref={fileInputRef}
                                                className="hidden"
                                                onChange={(e) => handleFile(e.target.files?.[0])}
                                            />
                                            {cvFile ? (
                                                <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="flex flex-col items-center gap-3">
                                                    <div className="w-12 h-12 rounded-full bg-accent-emerald/20 flex items-center justify-center">
                                                        <svg width="24" height="24" fill="none" stroke="var(--accent-emerald)" strokeWidth="2.5" viewBox="0 0 24 24">
                                                            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                                                        </svg>
                                                    </div>
                                                    <span className="font-bold text-accent-emerald text-sm">{cvFile.name}</span>
                                                    <span className="text-xs text-slate-500">{(cvFile.size / 1024).toFixed(1)} KB · Click to change</span>
                                                </motion.div>
                                            ) : (
                                                <div className="flex flex-col items-center gap-3">
                                                    <div className="w-12 h-12 rounded-full glass flex items-center justify-center group-hover:scale-110 transition-transform duration-500">
                                                        <svg width="24" height="24" fill="none" stroke="currentColor" className="text-slate-400" strokeWidth="2" viewBox="0 0 24 24">
                                                            <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                                                        </svg>
                                                    </div>
                                                    <div>
                                                        <div className="text-sm font-semibold text-slate-300">
                                                            <span className="text-accent-blue">Click to upload</span> or drag & drop
                                                        </div>
                                                        <div className="text-xs text-slate-500 mt-1">PDF only · max 10 MB</div>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    </div>

                                    {/* Job Description */}
                                    <div className="group">
                                        <label className={labelClass}>Job Description <span className="text-accent-red">*</span></label>
                                        <textarea
                                            rows={5}
                                            value={jobDescription}
                                            onChange={(e) => setJobDescription(e.target.value)}
                                            placeholder="Paste the full job description here. The AI uses it to generate relevant interview questions..."
                                            className={`${inputClass} resize-y min-h-[120px]`}
                                        />
                                    </div>

                                    <div className="grid grid-cols-2 gap-4">
                                        {/* Company Name */}
                                        <div className="group">
                                            <label className={labelClass}>Company <span className="text-slate-600 font-normal normal-case">(optional)</span></label>
                                            <input
                                                type="text"
                                                value={companyName}
                                                onChange={(e) => setCompanyName(e.target.value)}
                                                placeholder="e.g. Google"
                                                className={inputClass}
                                            />
                                        </div>

                                        {/* Motivation Letter */}
                                        <div className="group">
                                            <label className={labelClass}>Motivation <span className="text-slate-600 font-normal normal-case">(optional)</span></label>
                                            <input
                                                type="text"
                                                value={motivationLetter}
                                                onChange={(e) => setMotivationLetter(e.target.value)}
                                                placeholder="Brief cover letter snippet..."
                                                className={inputClass}
                                            />
                                        </div>
                                    </div>

                                    <button
                                        onClick={() => setStep(1)}
                                        disabled={!canProceed}
                                        className={`mt-4 w-full py-4 rounded-xl font-bold tracking-wide transition-all duration-300 ${
                                            canProceed ? 'bg-slate-800 text-white hover:bg-slate-700 shadow-lg' : 'bg-slate-900/50 text-slate-600 cursor-not-allowed'
                                        }`}
                                    >
                                        Continue Settings →
                                    </button>
                                </motion.div>
                            )}

                            {/* ── Step 1: Configure ──────────────────────────────────────── */}
                            {step === 1 && (
                                <motion.div 
                                    key="step1"
                                    initial={{ opacity: 0, x: 20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    exit={{ opacity: 0, x: -20 }}
                                    transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                                    className="flex flex-col gap-8"
                                >
                                    {/* Interview Length */}
                                    <div>
                                        <label className={labelClass}>Interview Length</label>
                                        <div className="grid grid-cols-1 gap-3">
                                            {LENGTH_OPTIONS.map(opt => (
                                                <button 
                                                    key={opt.value} 
                                                    onClick={() => setInterviewLength(opt.value)} 
                                                    className={`group relative overflow-hidden flex items-center justify-between px-5 py-4 rounded-[14px] cursor-pointer text-left transition-all duration-300 ${
                                                        interviewLength === opt.value ? 'bg-accent-blue/10 border border-accent-blue/50' : 'bg-slate-900/50 border border-slate-800/50 hover:bg-slate-800/80'
                                                    }`}
                                                >
                                                    {interviewLength === opt.value && (
                                                        <div className="absolute inset-0 bg-gradient-to-r from-accent-blue/5 to-transparent pointer-events-none" />
                                                    )}
                                                    <div className="relative z-10">
                                                        <div className={`font-bold text-sm transition-colors duration-300 ${interviewLength === opt.value ? 'text-accent-blue' : 'text-slate-300 group-hover:text-white'}`}>{opt.label}</div>
                                                        <div className="text-xs text-slate-500 mt-1">{opt.sub}</div>
                                                    </div>
                                                    <div className={`relative z-10 w-5 h-5 rounded-full border-2 shrink-0 transition-all duration-300 ${
                                                        interviewLength === opt.value ? 'border-accent-blue bg-accent-blue scale-110 shadow-[0_0_10px_rgba(59,130,246,0.5)]' : 'border-slate-600 bg-transparent'
                                                    }`} />
                                                </button>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Interview Mode */}
                                    <div>
                                        <label className={labelClass}>Interview Mode</label>
                                        <div className="grid grid-cols-1 gap-3">
                                            {MODE_OPTIONS.map(opt => (
                                                <button 
                                                    key={opt.value} 
                                                    onClick={() => setInterviewMode(opt.value)} 
                                                    className={`group relative overflow-hidden flex items-center gap-4 px-5 py-4 rounded-[14px] cursor-pointer text-left transition-all duration-300 ${
                                                        interviewMode === opt.value ? 'bg-accent-purple/10 border border-accent-purple/50' : 'bg-slate-900/50 border border-slate-800/50 hover:bg-slate-800/80'
                                                    }`}
                                                >
                                                    {interviewMode === opt.value && (
                                                        <div className="absolute inset-0 bg-gradient-to-r from-accent-purple/5 to-transparent pointer-events-none" />
                                                    )}
                                                    <span className="relative z-10 text-2xl drop-shadow-md">{opt.icon}</span>
                                                    <div className="relative z-10 flex-1">
                                                        <div className={`font-bold text-sm transition-colors duration-300 ${interviewMode === opt.value ? 'text-accent-purple' : 'text-slate-300 group-hover:text-white'}`}>{opt.label}</div>
                                                        <div className="text-xs text-slate-500 mt-1">{opt.desc}</div>
                                                    </div>
                                                    <div className={`relative z-10 w-5 h-5 rounded-full border-2 shrink-0 transition-all duration-300 ${
                                                        interviewMode === opt.value ? 'border-accent-purple bg-accent-purple scale-110 shadow-[0_0_10px_rgba(139,92,246,0.5)]' : 'border-slate-600 bg-transparent'
                                                    }`} />
                                                </button>
                                            ))}
                                        </div>
                                    </div>

                                    {error && (
                                        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="px-5 py-4 bg-accent-red/10 border border-accent-red/30 rounded-[14px] text-accent-red text-sm font-medium">
                                            {error}
                                        </motion.div>
                                    )}

                                    <div className="flex flex-col gap-4 mt-2">
                                        <button
                                            onClick={handleSubmit}
                                            disabled={isLoading}
                                            className={`relative w-full py-4 rounded-xl font-bold tracking-wide transition-all duration-500 overflow-hidden group ${
                                                isLoading ? 'bg-slate-800 text-slate-500 cursor-not-allowed' : 'bg-slate-100 text-slate-900 shadow-[0_0_40px_rgba(255,255,255,0.15)] hover:shadow-[0_0_60px_rgba(255,255,255,0.25)] hover:scale-[1.02]'
                                            }`}
                                        >
                                            {!isLoading && <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent -translate-x-full group-hover:animate-[shimmer_1.5s_infinite]" />}
                                            <span className="relative z-10">{isLoading ? 'Processing...' : 'Launch Interview'}</span>
                                        </button>

                                        <button onClick={() => setStep(0)} className="text-slate-500 hover:text-slate-300 text-xs font-bold uppercase tracking-widest transition-colors duration-300">
                                            ← Back
                                        </button>
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SetupPage;
