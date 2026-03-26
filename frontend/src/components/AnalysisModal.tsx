import { useEffect } from 'react';
import { CVJobMatch, JobAnalysisResponse, Recommendation, StoredCV } from '../types';
import { CVMatchResult } from './CVMatchResult';
import { ResultCard } from './ResultCard';

interface AnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  jobResult: JobAnalysisResponse | null;
  matchResult: CVJobMatch | null;
  activeCv: StoredCV | null;
  matchLoading: boolean;
  matchError: string | null;
  recommendation: Recommendation | null;
  onRecommend: () => void;
  isRecommended: boolean;
}

export function AnalysisModal({
  isOpen,
  onClose,
  jobResult,
  matchResult,
  activeCv,
  matchLoading,
  matchError,
  recommendation,
  onRecommend,
  isRecommended,
}: AnalysisModalProps) {

  // Lock body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
      document.body.style.overflow = 'hidden';
      document.body.style.paddingRight = `${scrollbarWidth}px`;
      return () => {
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';
      };
    }
  }, [isOpen]);

  // Close on Escape key
  useEffect(() => {
    if (!isOpen) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [isOpen, onClose]);

  if (!isOpen || !jobResult) return null;

  return (
    <div className="fixed inset-0 z-50">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-slate-900/70 animate-in fade-in duration-200"
        onClick={onClose}
      />

      {/* Modal Shell — fixed position, explicit bounds */}
      <div
        className="absolute inset-4 sm:inset-6 md:inset-8 lg:inset-10 flex flex-col bg-slate-50 dark:bg-[#0d1117] rounded-3xl shadow-2xl ring-1 ring-slate-200 dark:ring-slate-800 animate-in fade-in zoom-in-95 duration-300"
        style={{ overflow: 'hidden' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header — pinned */}
        <div className="flex items-center justify-between px-6 py-4 md:px-8 md:py-5 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex-shrink-0">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-2xl bg-sky-100 dark:bg-sky-500/10 flex items-center justify-center text-sky-600 dark:text-sky-400 border border-sky-200 dark:border-sky-500/20">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
            </div>
            <div>
              <h2 className="text-xl md:text-2xl font-bold text-slate-800 dark:text-white leading-tight">Comprehensive Analysis</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">Target job requirements vs. your CV — side by side.</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700 hover:text-slate-900 dark:hover:text-white transition-colors cursor-pointer"
            aria-label="Close modal"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>

        {/* Content — the ONLY scrollable zone */}
        <div className="flex-1 min-h-0 overflow-y-auto overscroll-contain">
          <div className="p-6 md:p-8">
            {/* Recommendation banner */}
            {recommendation && (
              <div className="mb-6 rounded-2xl bg-emerald-50/80 dark:bg-emerald-900/10 border border-emerald-200/50 dark:border-emerald-500/20 p-4 text-sm text-emerald-800 dark:text-emerald-300 flex items-center gap-3">
                <div className="bg-emerald-100 dark:bg-emerald-500/20 p-2 rounded-full hidden sm:block flex-shrink-0">
                  <svg className="w-5 h-5 text-emerald-600 dark:text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                </div>
                <div>
                  <span className="font-bold uppercase tracking-wide text-xs opacity-80 block mb-0.5">Auto-Selection Complete</span>
                  Best pick: <span className="font-bold text-emerald-900 dark:text-emerald-200">{recommendation.best_cv.name}</span> — confidence <span className="font-bold text-emerald-900 dark:text-emerald-200">{Math.round(recommendation.score * 100)}%</span>.
                </div>
              </div>
            )}

            {/* Two-column layout */}
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">

              {/* Left Column: JOB */}
              <div className="space-y-5 min-w-0 overflow-hidden">
                <div className="flex items-center justify-between flex-wrap gap-3">
                  <h3 className="text-lg font-bold text-slate-800 dark:text-slate-200 flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-sky-500 flex-shrink-0"></span>
                    Job Requirements
                  </h3>
                  <button
                    type="button"
                    onClick={onRecommend}
                    className="btn-secondary flex items-center gap-2 text-sm py-2 px-4 cursor-pointer"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" /></svg>
                    Auto-Select Best CV
                  </button>
                </div>

                <ResultCard result={jobResult} />
              </div>

              {/* Right Column: CV MATCH */}
              <div className="space-y-5 min-w-0 overflow-hidden">
                <h3 className="text-lg font-bold text-slate-800 dark:text-slate-200 flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-indigo-500 flex-shrink-0"></span>
                  CV Library Match
                </h3>

                {matchError && (
                  <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-rose-700 text-sm">
                    {matchError}
                  </div>
                )}

                <CVMatchResult
                  match={matchResult}
                  activeCv={activeCv}
                  isLoading={matchLoading}
                  isRecommended={isRecommended}
                />
              </div>

            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
