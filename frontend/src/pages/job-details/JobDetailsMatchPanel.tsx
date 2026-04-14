import { Check, Copy, Loader2, Zap } from 'lucide-react';
import type { CVComparisonResult, CVJobMatch, StoredCV } from '../../types';

interface JobDetailsMatchPanelProps {
  cvs: StoredCV[];
  selectedCvId: number | '';
  compareCvIdA: number | '';
  compareCvIdB: number | '';
  setSelectedCvId: (value: number) => void;
  setCompareCvIdA: (value: number) => void;
  setCompareCvIdB: (value: number) => void;
  isMatchLoading: boolean;
  isCompareLoading: boolean;
  handleMatch: () => void;
  handleCompare: () => void;
  comparisonResult: CVComparisonResult | null;
  matchResult: CVJobMatch | null;
  cvA: StoredCV | null;
  cvB: StoredCV | null;
  comparisonExplanationBlocks: string[];
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
  compareCvIdA,
  compareCvIdB,
  setSelectedCvId,
  setCompareCvIdA,
  setCompareCvIdB,
  isMatchLoading,
  isCompareLoading,
  handleMatch,
  handleCompare,
  comparisonResult,
  matchResult,
  cvA,
  cvB,
  comparisonExplanationBlocks,
  matchWhyBlocks,
  copiedSection,
  handleCopyText,
  matchLevelTextClasses,
  displayMissingSkills,
  matchSuggestions,
  matchReorderSuggestions,
  t,
}: JobDetailsMatchPanelProps) {
  return (
    <div className="grid grid-cols-1 gap-4 lg:gap-5 xl:grid-cols-[minmax(0,360px)_minmax(0,1fr)]">
      <div className="space-y-4">
        <div className="rounded-2xl border border-slate-200/70 bg-white/70 p-4 dark:border-slate-800 dark:bg-slate-950/20">
          <h3 className="mb-3 text-sm font-bold uppercase tracking-wider text-slate-500">{t('jobDetails.matchTitle')}</h3>
          {cvs.length === 0 ? (
            <p className="text-sm text-slate-500">{t('jobDetails.uploadCvFirst')}</p>
          ) : (
            <>
              <select
                value={selectedCvId}
                onChange={(e) => setSelectedCvId(Number(e.target.value))}
                className="input-field !py-2.5 text-sm"
              >
                <option value="" disabled>{t('common.selectCv')}</option>
                {cvs.map((cv) => (
                  <option key={cv.id} value={cv.id}>{cv.name}</option>
                ))}
              </select>
              <button
                onClick={handleMatch}
                disabled={isMatchLoading || !selectedCvId}
                className="btn-primary mt-3 flex items-center justify-center gap-2 !py-2.5 text-sm"
              >
                {isMatchLoading ? <><Loader2 size={16} className="animate-spin" /> {t('jobDetails.evaluating')}</> : <><Zap size={16} /> {t('jobDetails.runAlgorithm')}</>}
              </button>
            </>
          )}
        </div>

        <div className="rounded-2xl border border-slate-200/70 bg-white/70 p-4 dark:border-slate-800 dark:bg-slate-950/20">
          <h3 className="mb-3 text-sm font-bold uppercase tracking-wider text-slate-500">{t('jobDetails.compareTitle')}</h3>
          {cvs.length < 2 ? (
            <p className="text-sm text-slate-500">{t('jobDetails.uploadTwoCvs')}</p>
          ) : (
            <div className="space-y-2">
              <select value={compareCvIdA} onChange={(e) => setCompareCvIdA(Number(e.target.value))} className="input-field !py-2.5 text-sm">
                <option value="" disabled>{t('common.selectCv')}</option>
                {cvs.map((cv) => <option key={`a-${cv.id}`} value={cv.id}>{cv.name}</option>)}
              </select>
              <select value={compareCvIdB} onChange={(e) => setCompareCvIdB(Number(e.target.value))} className="input-field !py-2.5 text-sm">
                <option value="" disabled>{t('common.selectCv')}</option>
                {cvs.map((cv) => (
                  <option key={`b-${cv.id}`} value={cv.id} disabled={cv.id === Number(compareCvIdA)}>
                    {cv.name}
                  </option>
                ))}
              </select>
              <button
                onClick={handleCompare}
                disabled={isCompareLoading || !compareCvIdA || !compareCvIdB || compareCvIdA === compareCvIdB}
                className="btn-secondary !py-2.5 text-sm"
              >
                {isCompareLoading ? t('jobDetails.comparing') : t('jobDetails.compareCvs')}
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="min-w-0 space-y-4">
        {comparisonResult && cvA && cvB && (
          <div className="space-y-4 rounded-2xl border border-emerald-200/70 bg-emerald-50/70 p-5 lg:p-6 dark:border-emerald-900/50 dark:bg-emerald-950/20">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1.5">
                <p className="text-xs font-bold uppercase tracking-wider text-slate-500">{t('jobDetails.recommendedCv')}</p>
                <p className="break-words text-base font-semibold leading-7 text-emerald-700 dark:text-emerald-300 lg:text-lg">{comparisonResult.winner.label}</p>
              </div>
              <button
                type="button"
                onClick={() =>
                  handleCopyText(
                    [
                      comparisonResult.overall_reason,
                      ...comparisonResult.comparative_strengths,
                      ...comparisonResult.comparative_weaknesses,
                      ...comparisonResult.job_alignment_breakdown,
                    ].join('\n'),
                    'comparison',
                  )
                }
                className="btn-secondary flex w-full items-center justify-center gap-2 px-4 !py-2 text-sm sm:w-auto"
              >
                {copiedSection === 'comparison' ? <><Check size={14} /> {t('common.copied')}</> : <><Copy size={14} /> {t('common.copyToClipboard')}</>}
              </button>
            </div>

            {comparisonExplanationBlocks.length > 0 && (
              <div className="rounded-xl border border-emerald-200/80 bg-white/80 px-4 py-3 dark:border-emerald-900/50 dark:bg-slate-950/30">
                {comparisonExplanationBlocks.length > 1 ? (
                  <ul className="list-disc space-y-2 pl-5 text-sm leading-7 text-slate-700 dark:text-slate-300">
                    {comparisonExplanationBlocks.map((item, i) => <li key={i} className="break-words">{item}</li>)}
                  </ul>
                ) : (
                  <p className="break-words text-sm leading-7 text-slate-700 dark:text-slate-300">{comparisonExplanationBlocks[0]}</p>
                )}
              </div>
            )}

            <div className="grid grid-cols-1 gap-3 lg:grid-cols-2 lg:gap-4">
              <div className="min-w-0 rounded-xl border border-emerald-200/80 bg-white/80 px-4 py-3 dark:border-emerald-900/50 dark:bg-slate-950/30">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">{t('jobDetails.comparativeStrengths')}</p>
                {comparisonResult.comparative_strengths.length > 0 ? (
                  <ul className="list-disc space-y-1.5 pl-5 text-sm leading-7 text-slate-700 dark:text-slate-300">
                    {comparisonResult.comparative_strengths.map((item, i) => <li key={`cmp-strength-${i}`} className="break-words">{item}</li>)}
                  </ul>
                ) : (
                  <p className="text-sm text-slate-500 dark:text-slate-400">--</p>
                )}
              </div>
              <div className="min-w-0 rounded-xl border border-emerald-200/80 bg-white/80 px-4 py-3 dark:border-emerald-900/50 dark:bg-slate-950/30">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">{t('jobDetails.comparativeWeaknesses')}</p>
                {comparisonResult.comparative_weaknesses.length > 0 ? (
                  <ul className="list-disc space-y-1.5 pl-5 text-sm leading-7 text-slate-700 dark:text-slate-300">
                    {comparisonResult.comparative_weaknesses.map((item, i) => <li key={`cmp-weak-${i}`} className="break-words">{item}</li>)}
                  </ul>
                ) : (
                  <p className="text-sm text-slate-500 dark:text-slate-400">--</p>
                )}
              </div>
            </div>

            <div className="min-w-0 rounded-xl border border-emerald-200/80 bg-white/80 px-4 py-3 dark:border-emerald-900/50 dark:bg-slate-950/30">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">{t('jobDetails.jobAlignmentBreakdown')}</p>
              {comparisonResult.job_alignment_breakdown.length > 0 ? (
                <ul className="list-disc space-y-1.5 pl-5 text-sm leading-7 text-slate-700 dark:text-slate-300">
                  {comparisonResult.job_alignment_breakdown.map((item, i) => <li key={`cmp-align-${i}`} className="break-words">{item}</li>)}
                </ul>
              ) : (
                <p className="text-sm text-slate-500 dark:text-slate-400">--</p>
              )}
            </div>
          </div>
        )}

        {matchResult && (
          <div className="space-y-5 rounded-2xl border border-brand-primary/20 bg-brand-primary/5 p-5 lg:p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">{t('jobDetails.matchResults')}</h3>
              <div className="flex flex-wrap items-center gap-2">
                <span className={`text-sm font-bold uppercase ${matchLevelTextClasses[matchResult.match_level]}`}>{matchResult.match_level}</span>
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
                  {copiedSection === 'match' ? <><Check size={14} /> {t('common.copied')}</> : <><Copy size={14} /> {t('common.copyToClipboard')}</>}
                </button>
              </div>
            </div>

            <div className="rounded-xl border border-slate-200/70 bg-white/70 px-4 py-3 dark:border-slate-700 dark:bg-slate-950/30">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">{t('jobDetails.whyThisCv')}</p>
              {matchWhyBlocks.length > 1 ? (
                <ul className="list-disc space-y-2 pl-5 text-sm leading-7 text-slate-700 dark:text-slate-300">
                  {matchWhyBlocks.map((item, i) => <li key={i} className="break-words">{item}</li>)}
                </ul>
              ) : (
                <p className="break-words text-sm leading-7 text-slate-700 dark:text-slate-300">{matchWhyBlocks[0] ?? matchResult.why_this_cv}</p>
              )}
            </div>

            <div className="grid grid-cols-1 gap-3 lg:grid-cols-2 lg:gap-4">
              <div className="min-w-0 rounded-xl border border-slate-200/70 bg-white/70 px-4 py-3 dark:border-slate-700 dark:bg-slate-950/30">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">{t('jobDetails.strengths')}</p>
                {matchResult.strengths?.length ? (
                  <ul className="list-disc space-y-1.5 pl-5 text-sm leading-7 text-slate-700 dark:text-slate-300">
                    {matchResult.strengths.map((item, i) => <li key={i} className="break-words">{item}</li>)}
                  </ul>
                ) : (
                  <p className="text-sm text-slate-500 dark:text-slate-400">--</p>
                )}
              </div>
              <div className="min-w-0 rounded-xl border border-slate-200/70 bg-white/70 px-4 py-3 dark:border-slate-700 dark:bg-slate-950/30">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">{t('jobDetails.missingSkills')}</p>
                {displayMissingSkills.length > 0 ? (
                  <ul className="list-disc space-y-1.5 pl-5 text-sm leading-7 text-slate-700 dark:text-slate-300">
                    {displayMissingSkills.map((item, i) => <li key={`${item}-${i}`} className="break-words">{item}</li>)}
                  </ul>
                ) : (
                  <p className="text-sm text-slate-500 dark:text-slate-400">--</p>
                )}
              </div>
            </div>

            {(matchSuggestions.length > 0 || matchReorderSuggestions.length > 0) && (
              <div className="rounded-xl border border-slate-200/70 bg-white/70 px-4 py-3 dark:border-slate-700 dark:bg-slate-950/30">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">{t('jobDetails.improveCv')}</p>
                <ul className="list-disc space-y-1.5 pl-5 text-sm leading-7 text-slate-700 dark:text-slate-300">
                  {[...matchSuggestions, ...matchReorderSuggestions].map((item, i) => <li key={i} className="break-words">{item}</li>)}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
