import type { CVJobMatch } from '../../types';

interface JobDetailsImprovementsPanelProps {
  matchResult: CVJobMatch | null;
  matchSuggestions: string[];
  additionalMissingKeywords: string[];
  matchReorderSuggestions: string[];
  setActiveTab: (tab: 'match') => void;
  t: (key: string, params?: Record<string, string | number>) => string;
}

export function JobDetailsImprovementsPanel({
  matchResult,
  matchSuggestions,
  additionalMissingKeywords,
  matchReorderSuggestions,
  setActiveTab,
  t,
}: JobDetailsImprovementsPanelProps) {
  if (!matchResult) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-center dark:border-slate-700">
        <p className="mb-3 text-sm text-slate-500">{t('jobDetails.noCvSelected')}</p>
        <button onClick={() => setActiveTab('match')} className="btn-secondary w-auto px-5 !py-2">{t('jobDetails.matchTitle')}</button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-slate-200/70 bg-white/70 p-5 dark:border-slate-800 dark:bg-slate-950/20">
        <h3 className="mb-3 text-sm font-bold uppercase tracking-wider text-slate-500">{t('jobDetails.strengths')}</h3>
        <ul className="list-disc space-y-2 pl-5 text-sm leading-7 text-slate-700 dark:text-slate-300">
          {matchResult.strengths?.map((item, i) => <li key={i} className="break-words">{item}</li>)}
        </ul>
      </div>

      <div className="space-y-4 rounded-2xl border border-slate-200/70 bg-white/70 p-5 dark:border-slate-800 dark:bg-slate-950/20">
        <h3 className="mb-3 text-sm font-bold uppercase tracking-wider text-slate-500">{t('jobDetails.improveCv')}</h3>

        {matchSuggestions.length > 0 && (
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">{t('jobDetails.improveCv')}</p>
            <ul className="list-disc space-y-2 pl-5 text-sm leading-7 text-slate-700 dark:text-slate-300">
              {matchSuggestions.map((item, i) => <li key={i} className="break-words">{item}</li>)}
            </ul>
          </div>
        )}

        {matchResult.missing_skills?.length > 0 && (
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">{t('jobDetails.missingSkills')}</p>
            <ul className="list-disc space-y-2 pl-5 text-sm leading-7 text-slate-700 dark:text-slate-300">
              {matchResult.missing_skills.map((item, i) => <li key={i} className="break-words">{item}</li>)}
            </ul>
          </div>
        )}

        {additionalMissingKeywords.length > 0 && (
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">Keywords to add</p>
            <div className="flex flex-wrap gap-2">
              {additionalMissingKeywords.map((keyword) => (
                <span key={keyword} className="break-words rounded-full border border-amber-200/80 bg-white/80 px-3 py-1 text-xs font-semibold text-amber-900 dark:border-amber-800 dark:bg-slate-950/40 dark:text-amber-200">
                  {keyword}
                </span>
              ))}
            </div>
          </div>
        )}

        {matchReorderSuggestions.length > 0 && (
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">{t('jobDetails.improveCv')}</p>
            <ul className="list-disc space-y-2 pl-5 text-sm leading-7 text-slate-700 dark:text-slate-300">
              {matchReorderSuggestions.map((item, i) => <li key={i} className="break-words">{item}</li>)}
            </ul>
          </div>
        )}

        {matchSuggestions.length === 0 && matchResult.missing_skills?.length === 0 && additionalMissingKeywords.length === 0 && matchReorderSuggestions.length === 0 && (
          <p className="text-sm text-slate-500 dark:text-slate-400">--</p>
        )}
      </div>
    </div>
  );
}
