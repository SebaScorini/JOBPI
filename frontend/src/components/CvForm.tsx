import React, { useRef, useState } from 'react';

interface CvFormProps {
  onSubmit: (title: string, description: string, cvFile: File) => void;
  isLoading: boolean;
}

export function CvForm({ onSubmit, isLoading }: CvFormProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !description.trim() || !cvFile) return;
    onSubmit(title, description, cvFile);
  };

  const handleFile = (file: File) => {
    if (file.type === 'application/pdf') {
      setCvFile(file);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const canSubmit = title.trim() && description.trim() && cvFile && !isLoading;

  return (
    <form onSubmit={handleSubmit} className="glass-card-solid p-6 md:p-8 space-y-5 rounded-3xl">
      <div>
        <label htmlFor="cv-title" className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
          Job Title <span className="text-emerald-500">*</span>
        </label>
        <input
          type="text"
          id="cv-title"
          required
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g. Backend Engineer"
          className="input-field focus:ring-emerald-500/10 dark:focus:ring-emerald-500/20 focus:border-emerald-500 dark:focus:border-emerald-500"
        />
      </div>

      <div>
        <label htmlFor="cv-description" className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
          Job Description <span className="text-emerald-500">*</span>
        </label>
        <textarea
          id="cv-description"
          required
          rows={5}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Paste the job description here..."
          className="input-field resize-y focus:ring-emerald-500/10 dark:focus:ring-emerald-500/20 focus:border-emerald-500 dark:focus:border-emerald-500"
        />
      </div>

      <div>
        <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-1.5">Your CV (PDF) <span className="text-emerald-500">*</span></label>
        <div
          role="button"
          tabIndex={0}
          onClick={() => fileInputRef.current?.click()}
          onKeyDown={(e) => e.key === 'Enter' && fileInputRef.current?.click()}
          onDrop={handleDrop}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          className={`w-full border-2 border-dashed rounded-2xl p-6 text-center transition-all duration-300 ${
            dragOver ? 'border-emerald-400 bg-emerald-50/50 dark:bg-emerald-900/10 dark:border-emerald-500' : 'border-slate-300 dark:border-slate-700 hover:border-emerald-300 dark:hover:border-emerald-600 bg-slate-50 dark:bg-[#0B0F19]'
          }`}
        >
          {cvFile ? (
            <div className="flex items-center justify-center gap-2 text-emerald-600 dark:text-emerald-400 font-semibold cursor-pointer">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="text-sm font-medium">{cvFile.name}</span>
            </div>
          ) : (
            <div className="text-slate-500 dark:text-slate-400 cursor-pointer flex flex-col items-center">
              <div className="w-12 h-12 rounded-full bg-slate-200/50 dark:bg-slate-800 flex items-center justify-center mb-3">
                <svg className="w-6 h-6 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
              </div>
              <p className="text-sm font-medium">Drop your PDF here or click to browse</p>
            </div>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
          />
        </div>
      </div>

      <div className="pt-2">
        <button
          type="submit"
          disabled={!canSubmit}
          className="btn-primary !bg-emerald-600 hover:!bg-emerald-500 flex justify-center items-center gap-2 shadow-emerald-500/20"
        >
          {isLoading ? (
          <>
            <svg className="animate-spin -ml-1 mr-2 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Analyzing Fit...
          </>
        ) : (
          'Analyze My CV Fit'
          )}
        </button>
      </div>
    </form>
  );
}
