import { CVJobMatch, StoredCV } from '../types';
import { CvResultCard } from './CvResultCard';

interface CVMatchResultProps {
  match: CVJobMatch | null;
  activeCv: StoredCV | null;
  isLoading: boolean;
  isRecommended: boolean;
}

export function CVMatchResult({ match, activeCv, isLoading, isRecommended }: CVMatchResultProps) {
  if (isLoading) {
    return (
      <div className="glass-card p-6 md:p-8 rounded-3xl animate-pulse flex flex-col items-center justify-center text-center space-y-3">
        <div className="w-10 h-10 rounded-full border-4 border-slate-200 dark:border-slate-700 border-t-sky-500 animate-spin" />
        <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">Matching the selected CV against this job...</p>
      </div>
    );
  }

  if (!activeCv) {
    return (
      <div className="glass-card-solid p-6 md:p-8 rounded-3xl border-dashed flex flex-col items-center justify-center text-center">
        <svg className="w-10 h-10 text-slate-400 dark:text-slate-500 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 2.05l.566 2.844M20.95 6.05l-2.844-.566" /></svg>
        <p className="text-sm font-medium text-slate-600 dark:text-slate-400">Choose a CV from the library to run a persistent match.</p>
      </div>
    );
  }

  if (!match) {
    return (
      <div className="glass-card-solid p-6 md:p-8 rounded-3xl border-dashed text-center">
        <p className="text-sm text-slate-600 dark:text-slate-400 font-medium">
          Analyze a job first, then JobPi will match <span className="font-bold text-sky-600 dark:text-sky-400">{activeCv.name}</span>.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200/60 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-900/80 px-5 py-4 backdrop-blur-sm">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500 mb-1">Selected CV</p>
          <p className="text-lg font-bold text-slate-900 dark:text-white">{activeCv.name}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-sky-100/80 dark:bg-sky-500/10 px-3 py-1.5 text-xs font-bold tracking-wide text-sky-700 dark:text-sky-400 uppercase border border-sky-200/50 dark:border-sky-500/20">
            Score {Math.round(match.heuristic_score * 100)}%
          </span>
          {isRecommended && (
            <span className="rounded-full bg-emerald-100/80 dark:bg-emerald-500/10 px-3 py-1.5 text-xs font-bold tracking-wide text-emerald-700 dark:text-emerald-400 uppercase border border-emerald-200/50 dark:border-emerald-500/20 shadow-[0_0_15px_rgba(16,185,129,0.15)] dark:shadow-[0_0_15px_rgba(16,185,129,0.1)]">
              Best match
            </span>
          )}
        </div>
      </div>
      <CvResultCard result={match.result} />
    </div>
  );
}
