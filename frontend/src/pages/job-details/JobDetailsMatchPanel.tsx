import {
  Check,
  Copy,
  GitCompareArrows,
  Loader2,
  SearchCheck,
  ShieldAlert,
  Sparkles,
  Trophy,
  Zap,
} from 'lucide-react';
import type { ReactNode } from 'react';
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

interface MatchSectionProps {
  title: string;
  eyebrow: string;
  tone: 'emerald' | 'sky' | 'amber' | 'slate';
  icon: ReactNode;
  items: string[];
}

function MatchSection({ title, eyebrow, tone, icon, items }: MatchSectionProps) {
  return (
    <section className={`improvement-panel-card improvement-panel-card-${tone} flex flex-col h-full`}>
      <div className="mb-4 flex items-start gap-3">
        <div className={`improvement-panel-icon improvement-panel-icon-${tone}`}>{icon}</div>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500 dark:text-slate-400">
            {eyebrow}
          </p>
          <h3 className="mt-1 text-base font-semibold text-slate-900 dark:text-slate-100">{title}</h3>
        </div>
      </div>

      {items.length > 0 ? (
        <ul className="flex-1 space-y-3">
          {items.map((item, index) => (
            <li key={`${title}-${index}`} className="improvement-panel-list-item">
              <span className={`improvement-panel-bullet improvement-panel-bullet-${tone}`} aria-hidden="true" />
              <span className="min-w-0 break-words text-sm leading-6 text-slate-700 dark:text-slate-300">{item}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="flex-1 text-sm text-slate-500 dark:text-slate-400">--</p>
      )}
    </section>
  );
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
  const improvementSignals = [...matchSuggestions, ...matchReorderSuggestions];

  return (
    <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,370px)_minmax(0,1fr)]">
      <aside className="space-y-5">
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
            <div className="space-y-3">
              <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">{t('jobDetails.matchWorkspaceBody')}</p>
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
                className="btn-primary flex items-center justify-center gap-2 !py-2.5 text-sm"
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

        <section className="improvement-panel-sidebar-card">
          <div className="mb-4 flex items-start gap-3">
            <div className="improvement-panel-icon improvement-panel-icon-emerald">
              <GitCompareArrows size={18} />
            </div>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500 dark:text-slate-400">
                {t('jobDetails.compareTitle')}
              </p>
              <h3 className="mt-1 text-base font-semibold text-slate-900 dark:text-slate-100">
                {t('jobDetails.compareWorkspaceTitle')}
              </h3>
            </div>
          </div>

          {cvs.length < 2 ? (
            <p className="text-sm text-slate-500">{t('jobDetails.uploadTwoCvs')}</p>
          ) : (
            <div className="space-y-3">
              <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">{t('jobDetails.compareWorkspaceBody')}</p>
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
        </section>
      </aside>

      <div className="min-w-0 space-y-5">
        {matchResult ? (
          <section className="improvement-panel-hero">
            <div className="improvement-panel-glow improvement-panel-glow-primary" aria-hidden="true" />
            <div className="improvement-panel-glow improvement-panel-glow-secondary" aria-hidden="true" />

            <div className="relative z-[1] grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_320px]">
              <div className="space-y-5">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="improvement-panel-badge">
                    <Sparkles size={14} />
                    {t('jobDetails.matchResults')}
                  </span>
                  <span className={`improvement-panel-badge improvement-panel-badge-muted ${matchLevelTextClasses[matchResult.match_level]}`}>
                    {t('jobDetails.matchLevelLabel', { level: matchResult.match_level })}
                  </span>
                </div>

                <div className="max-w-3xl">
                  <h2 className="text-2xl font-semibold tracking-tight text-slate-950 dark:text-slate-50 md:text-[2rem]">
                    {t('jobDetails.matchHeroTitle')}
                  </h2>
                  <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600 dark:text-slate-300 md:text-[15px]">
                    {matchWhyBlocks[0] ?? matchResult.why_this_cv}
                  </p>
                </div>

                <div className="flex flex-wrap gap-2.5">
                  {(matchResult.strengths ?? []).slice(0, 3).map((item, index) => (
                    <span
                      key={`match-strength-${index}`}
                      className="rounded-full border border-emerald-200/80 bg-emerald-50/90 px-3 py-1.5 text-xs font-medium text-emerald-900 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:text-emerald-200"
                    >
                      {item}
                    </span>
                  ))}
                </div>
              </div>

              <aside className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
                <div className="improvement-panel-stat-card">
                  <div className="improvement-panel-stat-icon bg-emerald-500/15 text-emerald-700 dark:bg-emerald-400/15 dark:text-emerald-200">
                    <Trophy size={18} />
                  </div>
                  <p className="mt-4 text-3xl font-semibold tracking-tight text-slate-950 dark:text-slate-50">
                    {matchResult.strengths.length}
                  </p>
                  <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{t('jobDetails.alignmentSignals')}</p>
                </div>

                <div className="improvement-panel-stat-card">
                  <div className="improvement-panel-stat-icon bg-amber-500/15 text-amber-700 dark:bg-amber-400/15 dark:text-amber-200">
                    <ShieldAlert size={18} />
                  </div>
                  <p className="mt-4 text-3xl font-semibold tracking-tight text-slate-950 dark:text-slate-50">
                    {displayMissingSkills.length}
                  </p>
                  <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{t('jobDetails.gapsToClose')}</p>
                </div>

                <div className="improvement-panel-stat-card">
                  <div className="improvement-panel-stat-icon bg-sky-500/15 text-sky-700 dark:bg-sky-400/15 dark:text-sky-200">
                    <SearchCheck size={18} />
                  </div>
                  <p className="mt-4 text-3xl font-semibold tracking-tight text-slate-950 dark:text-slate-50">
                    {improvementSignals.length}
                  </p>
                  <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{t('jobDetails.editsSuggested')}</p>
                </div>
              </aside>
            </div>
          </section>
        ) : null}

        {matchResult ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <MatchSection
              eyebrow={t('jobDetails.whyThisCv')}
              title={t('jobDetails.fitNarrative')}
              tone="slate"
              icon={<Sparkles size={18} />}
              items={matchWhyBlocks.length > 0 ? matchWhyBlocks : [matchResult.why_this_cv]}
            />
            <MatchSection
              eyebrow={t('jobDetails.strengths')}
              title={t('jobDetails.strengthsTitle')}
              tone="emerald"
              icon={<Trophy size={18} />}
              items={matchResult.strengths}
            />
            <MatchSection
              eyebrow={t('jobDetails.missingSkills')}
              title={t('jobDetails.gapsTitle')}
              tone="amber"
              icon={<ShieldAlert size={18} />}
              items={displayMissingSkills}
            />
          </div>
        ) : null}

        {matchResult ? (
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
                {copiedSection === 'match' ? <><Check size={14} /> {t('common.copied')}</> : <><Copy size={14} /> {t('common.copyToClipboard')}</>}
              </button>
            </div>

            {improvementSignals.length > 0 ? (
              <div className="grid gap-3 md:grid-cols-2">
                {improvementSignals.map((item, index) => (
                  <article
                    key={`signal-${index}`}
                    className="h-full rounded-2xl border border-slate-200/80 bg-white p-4 dark:border-slate-800/80 dark:bg-slate-950/30"
                  >
                    <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500 dark:text-slate-400">
                      {t('jobDetails.editCardLabel', { count: index + 1 })}
                    </div>
                    <p className="text-sm leading-6 text-slate-700 dark:text-slate-300">{item}</p>
                  </article>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-500 dark:text-slate-400">--</p>
            )}
          </section>
        ) : null}

        {comparisonResult && cvA && cvB ? (
          <section className="improvement-panel-card improvement-panel-card-emerald">
            <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <div className="improvement-panel-icon improvement-panel-icon-emerald">
                  <GitCompareArrows size={18} />
                </div>
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500 dark:text-slate-400">
                    {t('jobDetails.comparisonResult')}
                  </p>
                  <h3 className="mt-1 text-base font-semibold text-slate-900 dark:text-slate-100">
                    {comparisonResult.winner.label}
                  </h3>
                </div>
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

            {comparisonExplanationBlocks.length > 0 ? (
              <div className="rounded-2xl border border-slate-100 bg-white p-4 dark:border-slate-800/80 dark:bg-slate-950/30">
                {comparisonExplanationBlocks.length > 1 ? (
                  <ul className="space-y-3">
                    {comparisonExplanationBlocks.map((item, index) => (
                      <li key={`compare-block-${index}`} className="improvement-panel-inline-item">
                        <span className="mt-2 inline-flex h-2.5 w-2.5 shrink-0 rounded-full bg-emerald-500" />
                        <span className="break-words text-sm leading-6 text-slate-700 dark:text-slate-300">{item}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm leading-7 text-slate-700 dark:text-slate-300">{comparisonExplanationBlocks[0]}</p>
                )}
              </div>
            ) : null}

            <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              <MatchSection
                eyebrow={t('jobDetails.comparativeStrengths')}
                title={t('jobDetails.comparisonStrengthsTitle')}
                tone="emerald"
                icon={<Trophy size={18} />}
                items={comparisonResult.comparative_strengths}
              />
              <MatchSection
                eyebrow={t('jobDetails.comparativeWeaknesses')}
                title={t('jobDetails.comparisonWeaknessesTitle')}
                tone="amber"
                icon={<ShieldAlert size={18} />}
                items={comparisonResult.comparative_weaknesses}
              />
              <MatchSection
                eyebrow={t('jobDetails.jobAlignmentBreakdown')}
                title={t('jobDetails.comparisonAlignmentTitle')}
                tone="sky"
                icon={<SearchCheck size={18} />}
                items={comparisonResult.job_alignment_breakdown}
              />
            </div>
          </section>
        ) : null}
      </div>
    </div>
  );
}
