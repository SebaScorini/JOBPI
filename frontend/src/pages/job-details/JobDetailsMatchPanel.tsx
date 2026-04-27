import {
  Check,
  Copy,
  Loader2,
  SearchCheck,
  ShieldAlert,
  Sparkles,
  Trophy,
  Zap,
} from 'lucide-react';
import type { CVJobMatch, StoredCV } from '../../types';

interface JobDetailsMatchPanelProps {
  cvs: StoredCV[];
  selectedCvId: number | '';
  setSelectedCvId: (value: number) => void;
  isMatchLoading: boolean;
  handleMatch: () => void;
  matchResult: CVJobMatch | null;
  matchWhyBlocks: string[];
  copiedSection: 'cover' | 'match' | 'comparison' | null;
  handleCopyText: (text: string, section: 'cover' | 'match' | 'comparison') => void;
  matchLevelTextClasses: Record<'strong' | 'medium' | 'weak', string>;
  displayMissingSkills: string[];
  matchSuggestions: string[];
  matchReorderSuggestions: string[];
  t: (key: string, params?: Record<string, string | number>) => string;
}

export function JobDetailsMatchPanel({
  cvs,
  selectedCvId,
  setSelectedCvId,
  isMatchLoading,
  handleMatch,
  matchResult,
  matchWhyBlocks,
  copiedSection,
  handleCopyText,
  matchLevelTextClasses,
  displayMissingSkills,
  matchSuggestions,
  matchReorderSuggestions,
  t,
}: JobDetailsMatchPanelProps) {
  const improvementSignals = [...matchSuggestions, ...matchReorderSuggestions];

  return (
    <div className="space-y-5">
      {/* Mobile/Tablet Workspace (Hidden on Desktop since it's in the global sidebar) */}
      <div className="xl:hidden">
        <section className="improvement-panel-sidebar-card">
          <div className="mb-4 flex items-start gap-3">
            <div className="improvement-panel-icon improvement-panel-icon-sky">
              <SearchCheck size={18} />
            </div>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500 dark:text-slate-400">
                {t('jobDetails.matchTitle')}
              </p>
              <h3 className="mt-1 text-base font-semibold text-slate-900 dark:text-slate-100">
                {t('jobDetails.matchWorkspaceTitle')}
              </h3>
            </div>
          </div>

          {cvs.length === 0 ? (
            <p className="text-sm text-slate-500">{t('jobDetails.uploadCvFirst')}</p>
          ) : (
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
              <div className="flex-1">
                <p className="mb-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                  {t('jobDetails.matchWorkspaceBody')}
                </p>
                <select
                  value={selectedCvId}
                  onChange={(e) => setSelectedCvId(Number(e.target.value))}
                  className="input-field !py-2.5 text-sm"
                >
                  <option value="" disabled>
                    {t('common.selectCv')}
                  </option>
                  {cvs.map((cv) => (
                    <option key={cv.id} value={cv.id}>
                      {cv.name}
                    </option>
                  ))}
                </select>
              </div>
              <button
                onClick={handleMatch}
                disabled={isMatchLoading || !selectedCvId}
                className="btn-primary flex shrink-0 items-center justify-center gap-2 !py-2.5 text-sm sm:w-auto"
              >
                {isMatchLoading ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    {t('jobDetails.evaluating')}
                  </>
                ) : (
                  <>
                    <Zap size={16} />
                    {t('jobDetails.runAlgorithm')}
                  </>
                )}
              </button>
            </div>
          )}
        </section>
      </div>

      {matchResult ? (
        <>
          {/* Hero */}
          <section className="improvement-panel-sidebar-card relative overflow-hidden">
            <div className="improvement-panel-glow improvement-panel-glow-primary" aria-hidden="true" />

            <div className="relative z-[1]">
              <div className="mb-3 flex flex-wrap items-center gap-3">
                <span className="improvement-panel-badge">
                  <Sparkles size={14} />
                  {t('jobDetails.matchResults')}
                </span>
                <span className={`improvement-panel-badge improvement-panel-badge-muted ${matchLevelTextClasses[matchResult.match_level]}`}>
                  {t('jobDetails.matchLevelLabel', { level: matchResult.match_level })}
                </span>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300">
                    <Trophy size={12} /> <span className="font-bold">{matchResult.strengths.length}</span> {t('jobDetails.alignmentSignals')}
                  </span>
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-500/10 px-2.5 py-1 text-xs font-medium text-amber-700 dark:bg-amber-500/20 dark:text-amber-300">
                    <ShieldAlert size={12} /> <span className="font-bold">{displayMissingSkills.length}</span> {t('jobDetails.gapsToClose')}
                  </span>
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-sky-500/10 px-2.5 py-1 text-xs font-medium text-sky-700 dark:bg-sky-500/20 dark:text-sky-300">
                    <SearchCheck size={12} /> <span className="font-bold">{improvementSignals.length}</span> {t('jobDetails.editsSuggested')}
                  </span>
                </div>
              </div>

              <h2 className="text-lg font-semibold tracking-tight text-slate-950 dark:text-slate-50 md:text-xl">
                {t('jobDetails.matchHeroTitle')}
              </h2>
              <p className="mt-1.5 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
                {matchWhyBlocks[0] ?? matchResult.why_this_cv}
              </p>
            </div>
          </section>

          {/* Strengths + Gaps — side by side */}
          <div className="grid gap-4 md:grid-cols-2">
            {/* Strengths */}
            <div className="improvement-panel-card improvement-panel-card-emerald">
              <div className="mb-3 flex items-center gap-3">
                <div className="improvement-panel-icon improvement-panel-icon-emerald">
                  <Trophy size={18} />
                </div>
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500 dark:text-slate-400">
                    {t('jobDetails.strengths')}
                  </p>
                  <h3 className="mt-0.5 text-sm font-semibold text-slate-900 dark:text-slate-100">
                    {t('jobDetails.strengthsTitle')}
                  </h3>
                </div>
              </div>
              {matchResult.strengths.length > 0 ? (
                <ul className="space-y-2">
                  {matchResult.strengths.map((item, i) => (
                    <li key={i} className="improvement-panel-list-item">
                      <span className="improvement-panel-bullet improvement-panel-bullet-emerald" aria-hidden="true" />
                      <span className="min-w-0 break-words text-sm leading-6 text-slate-700 dark:text-slate-300">
                        {item}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-slate-500 dark:text-slate-400">--</p>
              )}
            </div>

            {/* Gaps */}
            <div className="improvement-panel-card improvement-panel-card-amber">
              <div className="mb-3 flex items-center gap-3">
                <div className="improvement-panel-icon improvement-panel-icon-amber">
                  <ShieldAlert size={18} />
                </div>
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500 dark:text-slate-400">
                    {t('jobDetails.missingSkills')}
                  </p>
                  <h3 className="mt-0.5 text-sm font-semibold text-slate-900 dark:text-slate-100">
                    {t('jobDetails.gapsTitle')}
                  </h3>
                </div>
              </div>
              {displayMissingSkills.length > 0 ? (
                <ul className="space-y-2">
                  {displayMissingSkills.map((item, i) => (
                    <li key={i} className="improvement-panel-list-item">
                      <span className="improvement-panel-bullet improvement-panel-bullet-amber" aria-hidden="true" />
                      <span className="min-w-0 break-words text-sm leading-6 text-slate-700 dark:text-slate-300">
                        {item}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-slate-500 dark:text-slate-400">--</p>
              )}
            </div>
          </div>

          {/* Improvement signals */}
          {improvementSignals.length > 0 && (
            <section className="improvement-panel-sidebar-card">
              <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <div className="improvement-panel-icon improvement-panel-icon-sky">
                    <SearchCheck size={18} />
                  </div>
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500 dark:text-slate-400">
                      {t('jobDetails.improveCv')}
                    </p>
                    <h3 className="mt-1 text-base font-semibold text-slate-900 dark:text-slate-100">
                      {t('jobDetails.nextRevisionFocus')}
                    </h3>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() =>
                    handleCopyText(
                      [
                        matchResult.why_this_cv,
                        ...matchResult.strengths,
                        ...displayMissingSkills,
                        ...matchSuggestions,
                        ...matchReorderSuggestions,
                      ].join('\n'),
                      'match',
                    )
                  }
                  className="btn-secondary flex w-full items-center justify-center gap-2 px-4 !py-2 text-sm sm:w-auto"
                >
                  {copiedSection === 'match' ? (
                    <>
                      <Check size={14} /> {t('common.copied')}
                    </>
                  ) : (
                    <>
                      <Copy size={14} /> {t('common.copyToClipboard')}
                    </>
                  )}
                </button>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                {improvementSignals.map((item, index) => (
                  <article
                    key={`signal-${index}`}
                    className="rounded-2xl border border-slate-200/80 bg-white p-4 dark:border-slate-800/80 dark:bg-slate-950/30"
                  >
                    <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500 dark:text-slate-400">
                      {t('jobDetails.editCardLabel', { count: index + 1 })}
                    </div>
                    <p className="text-sm leading-6 text-slate-700 dark:text-slate-300">{item}</p>
                  </article>
                ))}
              </div>
            </section>
          )}
        </>
      ) : (
        <div className="flex min-h-[300px] flex-col items-center justify-center rounded-2xl border border-dashed border-slate-200/80 bg-slate-50/50 p-8 text-center dark:border-slate-800/80 dark:bg-slate-900/20">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-slate-100 text-slate-400 dark:bg-slate-800/50 dark:text-slate-500">
            <Zap size={24} />
          </div>
          <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">
            {t('jobDetails.matchTitle')}
          </h3>
          <p className="mt-2 max-w-sm text-sm leading-6 text-slate-500 dark:text-slate-400">
            {t('jobDetails.matchWorkspaceBody')}
          </p>
        </div>
      )}
    </div>
  );
}
