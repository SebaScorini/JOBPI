import React, { useState } from 'react';
import { JobAnalysisRequest } from '../types';

interface JobFormProps {
  onSubmit: (data: JobAnalysisRequest) => void;
  isLoading: boolean;
}

export function JobForm({ onSubmit, isLoading }: JobFormProps) {
  const [title, setTitle] = useState('');
  const [company, setCompany] = useState('');
  const [description, setDescription] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !company.trim() || !description.trim()) return;
    
    onSubmit({ title, company, description });
  };

  return (
    <form onSubmit={handleSubmit} className="glass-card-solid p-6 md:p-8 space-y-5 rounded-3xl">
      <div>
        <label htmlFor="title" className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
          Job Title <span className="text-rose-500">*</span>
        </label>
        <input
          type="text"
          id="title"
          required
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g. Senior Frontend Engineer"
          className="input-field"
        />
      </div>

      <div>
        <label htmlFor="company" className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
          Company <span className="text-rose-500">*</span>
        </label>
        <input
          type="text"
          id="company"
          required
          value={company}
          onChange={(e) => setCompany(e.target.value)}
          placeholder="e.g. TechCorp Inc."
          className="input-field"
        />
      </div>

      <div>
        <label htmlFor="description" className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
          Job Description <span className="text-rose-500">*</span>
        </label>
        <textarea
          id="description"
          required
          rows={8}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Paste the full job description here..."
          className="input-field resize-y"
        />
      </div>

      <div className="pt-2">
        <button
          type="submit"
          disabled={isLoading || !title.trim() || !company.trim() || !description.trim()}
          className="btn-primary flex justify-center items-center gap-2"
        >
        {isLoading ? (
          <>
            <svg className="animate-spin -ml-1 mr-2 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Analyzing...
          </>
        ) : (
          'Analyze Job Description'
        )}
        </button>
      </div>
    </form>
  );
}
