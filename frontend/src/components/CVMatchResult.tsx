import { CVJobMatch, StoredCV } from '../types';
import { CvResultCard } from './CvResultCard';

interface CVMatchResultProps {
  match: CVJobMatch | null;
  activeCv: StoredCV | null;
  isLoading: boolean;
  isRecommended: boolean;
}

export function CVMatchResult({ match, activeCv, isLoading, isRecommended }: CVMatchResultProps) {
  const suggestions = match?.suggested_improvements ?? match?.improvement_suggestions ?? [];
  const missingKeywords = match?.missing_keywords ?? [];
  const reorderSuggestions = match?.reorder_suggestions ?? [];

  const matchLevelClasses = {
    strong: 'rounded-full border border-emerald-200/50 bg-emerald-100/80 px-3 py-1.5 text-xs font-bold tracking-wide text-emerald-700 dark:border-emerald-500/20 dark:bg-emerald-500/10 dark:text-emerald-400 uppercase',
    medium: 'rounded-full border border-amber-200/50 bg-amber-100/80 px-3 py-1.5 text-xs font-bold tracking-wide text-amber-700 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-400 uppercase',
    weak: 'rounded-full border border-rose-200/50 bg-rose-100/80 px-3 py-1.5 text-xs font-bold tracking-wide text-rose-700 dark:border-rose-500/20 dark:bg-rose-500/10 dark:text-rose-400 uppercase',
  } as const;

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
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500 mb-1">Best CV</p>
          <p className="text-lg font-bold text-slate-900 dark:text-white">{activeCv.name}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-sky-100/80 dark:bg-sky-500/10 px-3 py-1.5 text-xs font-bold tracking-wide text-sky-700 dark:text-sky-400 uppercase border border-sky-200/50 dark:border-sky-500/20">
            Score {Math.round(match.heuristic_score * 100)}%
          </span>
          <span className={matchLevelClasses[match.match_level]}>
            {match.match_level} match
          </span>
          {isRecommended && (
            <span className="rounded-full bg-emerald-100/80 dark:bg-emerald-500/10 px-3 py-1.5 text-xs font-bold tracking-wide text-emerald-700 dark:text-emerald-400 uppercase border border-emerald-200/50 dark:border-emerald-500/20 shadow-[0_0_15px_rgba(16,185,129,0.15)] dark:shadow-[0_0_15px_rgba(16,185,129,0.1)]">
              Recommended
            </span>
          )}
        </div>
      </div>

      <div className="glass-card rounded-3xl p-6 md:p-8 space-y-6">
        <section className="rounded-2xl border border-slate-200/70 dark:border-slate-800 bg-white/70 dark:bg-slate-950/30 p-5">
          <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-slate-500 mb-2">Why This CV</p>
          <p className="text-slate-700 dark:text-slate-300 leading-relaxed font-medium">
            {match.why_this_cv || match.result.fit_summary}
          </p>
        </section>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <section className="rounded-2xl border border-emerald-200/70 dark:border-emerald-900/60 bg-emerald-50/70 dark:bg-emerald-950/20 p-5">
            <h3 className="text-sm font-bold uppercase tracking-wide text-emerald-800 dark:text-emerald-300 mb-3">Strengths</h3>
            {match.strengths.length > 0 ? (
              <ul className="space-y-2">
                {match.strengths.map((item) => (
                  <li key={item} className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                    &bull; {item}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500 dark:text-slate-400">No standout strengths were identified.</p>
            )}
          </section>

          <section className="rounded-2xl border border-rose-200/70 dark:border-rose-900/60 bg-rose-50/70 dark:bg-rose-950/20 p-5">
            <h3 className="text-sm font-bold uppercase tracking-wide text-rose-800 dark:text-rose-300 mb-3">Missing Skills</h3>
            {match.missing_skills.length > 0 ? (
              <ul className="space-y-2">
                {match.missing_skills.map((item) => (
                  <li key={item} className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                    &bull; {item}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500 dark:text-slate-400">No material skill gaps were identified.</p>
            )}
          </section>
        </div>

        {(suggestions.length > 0 || missingKeywords.length > 0 || reorderSuggestions.length > 0) && (
          <section className="rounded-2xl border border-amber-200/70 dark:border-amber-900/60 bg-amber-50/70 dark:bg-amber-950/20 p-5">
            <h3 className="text-sm font-bold uppercase tracking-wide text-amber-800 dark:text-amber-300 mb-3">How to improve this CV</h3>

            {suggestions.length > 0 && (
              <div className="mb-4">
                <p className="mb-2 text-xs font-bold uppercase tracking-[0.18em] text-amber-700/80 dark:text-amber-300/80">
                  Suggested improvements
                </p>
                <ul className="space-y-2">
                  {suggestions.map((item) => (
                    <li key={item} className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                      &bull; {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {missingKeywords.length > 0 && (
              <div className="mb-4">
                <p className="mb-2 text-xs font-bold uppercase tracking-[0.18em] text-amber-700/80 dark:text-amber-300/80">
                  Missing keywords
                </p>
                <div className="flex flex-wrap gap-2">
                  {missingKeywords.map((item) => (
                    <span
                      key={item}
                      className="rounded-full border border-amber-200/80 bg-white/80 px-3 py-1 text-xs font-semibold text-amber-900 dark:border-amber-800 dark:bg-slate-950/40 dark:text-amber-200"
                    >
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {reorderSuggestions.length > 0 && (
              <div>
                <p className="mb-2 text-xs font-bold uppercase tracking-[0.18em] text-amber-700/80 dark:text-amber-300/80">
                  Reorder suggestions
                </p>
                <ul className="space-y-2">
                  {reorderSuggestions.map((item) => (
                    <li key={item} className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                      &bull; {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        )}
      </div>
      <CvResultCard result={match.result} matchLevel={match.match_level} />
    </div>
  );
}
