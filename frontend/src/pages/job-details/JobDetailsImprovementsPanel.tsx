import {
  ArrowRight,
  Check,
  Copy,
  FilePenLine,
  LayoutList,
  SearchCheck,
  Sparkles,
  Target,
} from 'lucide-react';
import { useState } from 'react';
import type { CVJobMatch } from '../../types';

interface JobDetailsImprovementsPanelProps {
  matchResult: CVJobMatch | null;
  matchSuggestions: string[];
  matchNextSteps: string[];
  additionalMissingKeywords: string[];
  matchReorderSuggestions: string[];
  setActiveTab: (tab: 'match') => void;
  t: (key: string, params?: Record<string, string | number>) => string;
}

type ImproveSubTab = 'edit' | 'keywords' | 'plan';

function SubTabBar({
  active,
  onChange,
  tabs,
}: {
  active: ImproveSubTab;
  onChange: (t: ImproveSubTab) => void;
  tabs: Array<{ id: ImproveSubTab; label: string }>;
}) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-1">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onChange(tab.id)}
          className={`whitespace-nowrap rounded-full px-4 py-1.5 text-xs font-semibold transition-colors ${
            active === tab.id
              ? 'bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900'
              : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

export function JobDetailsImprovementsPanel({
  matchResult,
  matchSuggestions,
  matchNextSteps,
  additionalMissingKeywords,
  matchReorderSuggestions,
  setActiveTab,
  t,
}: JobDetailsImprovementsPanelProps) {
  const [copiedBullets, setCopiedBullets] = useState(false);
  const [activeSubTab, setActiveSubTab] = useState<ImproveSubTab>('edit');

  if (!matchResult) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-center dark:border-slate-700">
        <p className="mb-3 text-sm text-slate-500">{t('jobDetails.noCvSelected')}</p>
        <button onClick={() => setActiveTab('match')} className="btn-secondary w-auto px-5 !py-2">
          {t('jobDetails.matchTitle')}
        </button>
      </div>
    );
  }

  const atsDirectImprovements = matchResult.result.ats_improvements ?? [];
  const recruiterDirectImprovements = matchResult.result.recruiter_improvements ?? [];
  const rewrittenBullets = matchResult.result.rewritten_bullets ?? [];
  const actionPlan = [...matchReorderSuggestions, ...matchNextSteps];

  const rewrittenCount = rewrittenBullets.length;
  const priorityCount = matchSuggestions.length + atsDirectImprovements.length;
  const evidenceCount = matchResult.missing_skills.length + additionalMissingKeywords.length;


  const handleCopyBullets = async () => {
    if (!rewrittenBullets.length) return;
    await navigator.clipboard.writeText(rewrittenBullets.map((item) => `- ${item}`).join('\n'));
    setCopiedBullets(true);
    window.setTimeout(() => setCopiedBullets(false), 2000);
  };

  const subTabs: Array<{ id: ImproveSubTab; label: string }> = [
    { id: 'edit', label: t('jobDetails.improveSubTabEdit') },
    { id: 'keywords', label: t('jobDetails.improveSubTabKeywords') },
    { id: 'plan', label: t('jobDetails.improveSubTabPlan') },
  ];

  return (
    <div className="space-y-5">
      {/* Hero */}
      <section className="improvement-panel-sidebar-card relative overflow-hidden">
        <div className="improvement-panel-glow improvement-panel-glow-primary" aria-hidden="true" />

        <div className="relative z-[1]">
          <div className="mb-3 flex flex-wrap items-center gap-3">
            <span className="improvement-panel-badge">
              <Sparkles size={14} />
              {t('jobDetails.improveCv')}
            </span>
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-500/10 px-2.5 py-1 text-xs font-medium text-amber-700 dark:bg-amber-500/20 dark:text-amber-300">
                <SearchCheck size={12} /> <span className="font-bold">{priorityCount}</span> {t('jobDetails.prioritySignals')}
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-sky-500/10 px-2.5 py-1 text-xs font-medium text-sky-700 dark:bg-sky-500/20 dark:text-sky-300">
                <Target size={12} /> <span className="font-bold">{evidenceCount}</span> {t('jobDetails.proofPoints')}
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-violet-500/10 px-2.5 py-1 text-xs font-medium text-violet-700 dark:bg-violet-500/20 dark:text-violet-300">
                <FilePenLine size={12} /> <span className="font-bold">{rewrittenCount}</span> {t('jobDetails.readyToPaste')}
              </span>
            </div>
          </div>

          <h2 className="text-lg font-semibold tracking-tight text-slate-950 dark:text-slate-50 md:text-xl">
            {t('jobDetails.improvementHeroTitle')}
          </h2>
          <p className="mt-1.5 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
            {t('jobDetails.improvementHeroBody')}
          </p>
        </div>
      </section>

      {/* Sub-tab navigation */}
      <div className="improvement-panel-sidebar-card !p-3">
        <SubTabBar active={activeSubTab} onChange={setActiveSubTab} tabs={subTabs} />
      </div>

      {/* ── Tab: Edit CV ── */}
      {activeSubTab === 'edit' && (
        <div className="space-y-4">
          {/* Priority edits */}
          {matchSuggestions.length > 0 && (
            <section className="improvement-panel-sidebar-card">
              <div className="mb-4 flex items-start gap-3">
                <div className="improvement-panel-icon improvement-panel-icon-slate">
                  <Sparkles size={18} />
                </div>
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500 dark:text-slate-400">
                    {t('jobDetails.priorityEdits')}
                  </p>
                  <h3 className="mt-1 text-base font-semibold text-slate-900 dark:text-slate-100">
                    {t('jobDetails.prioritySnapshot')}
                  </h3>
                </div>
              </div>
              <ul className="space-y-2">
                {matchSuggestions.map((item, index) => (
                  <li key={`suggestion-${index}`} className="improvement-panel-inline-item">
                    <span className="mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-900 text-[11px] font-semibold text-white dark:bg-slate-100 dark:text-slate-950">
                      {index + 1}
                    </span>
                    <span className="break-words text-sm leading-6 text-slate-700 dark:text-slate-300">{item}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* ATS improvements (direct AI output) */}
          {atsDirectImprovements.length > 0 && (
            <section className="improvement-panel-card improvement-panel-card-amber">
              <div className="mb-3 flex items-center gap-3">
                <div className="improvement-panel-icon improvement-panel-icon-amber">
                  <SearchCheck size={18} />
                </div>
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500 dark:text-slate-400">
                    {t('jobDetails.aiBoost')}
                  </p>
                  <h3 className="mt-0.5 text-sm font-semibold text-slate-900 dark:text-slate-100">
                    {t('jobDetails.atsTitle')}
                  </h3>
                </div>
              </div>
              <ul className="space-y-2">
                {atsDirectImprovements.map((item, index) => (
                  <li key={`ats-direct-${index}`} className="improvement-panel-inline-item">
                    <ArrowRight size={14} className="mt-1 shrink-0 text-amber-700 dark:text-amber-300" />
                    <span className="break-words text-sm leading-6 text-slate-700 dark:text-slate-300">{item}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Rewritten bullets */}
          {rewrittenBullets.length > 0 && (
            <section className="improvement-panel-card improvement-panel-card-violet">
              <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <div className="improvement-panel-icon improvement-panel-icon-violet">
                    <FilePenLine size={18} />
                  </div>
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500 dark:text-slate-400">
                      {t('jobDetails.rewrittenBullets')}
                    </p>
                    <h3 className="mt-1 text-base font-semibold text-slate-900 dark:text-slate-100">
                      {t('jobDetails.rewrittenBulletsTitle')}
                    </h3>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={handleCopyBullets}
                  className="btn-secondary flex w-auto items-center justify-center gap-2 px-3 !py-1.5 text-xs"
                >
                  {copiedBullets ? (
                    <>
                      <Check size={14} />
                      {t('common.copied')}
                    </>
                  ) : (
                    <>
                      <Copy size={14} />
                      {t('jobDetails.copyBullets')}
                    </>
                  )}
                </button>
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {rewrittenBullets.map((item, index) => (
                  <article
                    key={`bullet-${index}`}
                    className="rounded-2xl border border-violet-200/70 bg-white p-4 dark:border-violet-900/40 dark:bg-slate-950/45"
                  >
                    <div className="mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-violet-700 dark:text-violet-300">
                      <Sparkles size={12} />
                      {t('jobDetails.pasteReadyBullet', { count: index + 1 })}
                    </div>
                    <p className="text-sm leading-6 text-slate-700 dark:text-slate-300">{item}</p>
                  </article>
                ))}
              </div>
            </section>
          )}

          {matchSuggestions.length === 0 && atsDirectImprovements.length === 0 && rewrittenBullets.length === 0 && (
            <p className="text-sm text-slate-500 dark:text-slate-400">--</p>
          )}
        </div>
      )}

      {/* ── Tab: Keywords ── */}
      {activeSubTab === 'keywords' && (
        <div className="space-y-4">
          {/* Keyword bank */}
          {additionalMissingKeywords.length > 0 && (
            <section className="improvement-panel-sidebar-card">
              <div className="mb-4 flex items-start gap-3">
                <div className="improvement-panel-icon improvement-panel-icon-amber">
                  <SearchCheck size={18} />
                </div>
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500 dark:text-slate-400">
                    {t('jobDetails.keywordsToSurface')}
                  </p>
                  <h3 className="mt-1 text-base font-semibold text-slate-900 dark:text-slate-100">
                    {t('jobDetails.keywordBank')}
                  </h3>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {additionalMissingKeywords.map((keyword) => (
                  <span
                    key={keyword}
                    className="rounded-full border border-amber-200/80 bg-amber-50/90 px-3 py-1.5 text-xs font-semibold text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/25 dark:text-amber-200"
                  >
                    {keyword}
                  </span>
                ))}
              </div>
            </section>
          )}

          {/* Missing skills / recruiter gaps */}
          {matchResult.missing_skills?.length > 0 && (
            <section className="improvement-panel-card improvement-panel-card-sky">
              <div className="mb-4 flex items-start gap-3">
                <div className="improvement-panel-icon improvement-panel-icon-sky">
                  <Target size={18} />
                </div>
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500 dark:text-slate-400">
                    {t('jobDetails.evidenceGaps')}
                  </p>
                  <h3 className="mt-1 text-base font-semibold text-slate-900 dark:text-slate-100">
                    {t('jobDetails.proofToAdd')}
                  </h3>
                </div>
              </div>
              <ul className="space-y-2">
                {matchResult.missing_skills.map((item, index) => (
                  <li key={`gap-${index}`} className="improvement-panel-inline-item">
                    <ArrowRight size={14} className="mt-1 shrink-0 text-sky-700 dark:text-sky-300" />
                    <span className="break-words text-sm leading-6 text-slate-700 dark:text-slate-300">{item}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Recruiter direct improvements */}
          {recruiterDirectImprovements.length > 0 && (
            <section className="improvement-panel-card improvement-panel-card-sky">
              <div className="mb-3 flex items-center gap-3">
                <div className="improvement-panel-icon improvement-panel-icon-sky">
                  <Target size={18} />
                </div>
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500 dark:text-slate-400">
                    {t('jobDetails.aiBoost')}
                  </p>
                  <h3 className="mt-0.5 text-sm font-semibold text-slate-900 dark:text-slate-100">
                    {t('jobDetails.recruiterTitle')}
                  </h3>
                </div>
              </div>
              <ul className="space-y-2">
                {recruiterDirectImprovements.map((item, index) => (
                  <li key={`recruiter-direct-${index}`} className="improvement-panel-inline-item">
                    <ArrowRight size={14} className="mt-1 shrink-0 text-sky-700 dark:text-sky-300" />
                    <span className="break-words text-sm leading-6 text-slate-700 dark:text-slate-300">{item}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {additionalMissingKeywords.length === 0 &&
            matchResult.missing_skills?.length === 0 &&
            recruiterDirectImprovements.length === 0 && (
              <p className="text-sm text-slate-500 dark:text-slate-400">--</p>
            )}
        </div>
      )}

      {/* ── Tab: Action Plan ── */}
      {activeSubTab === 'plan' && (
        <div className="space-y-4">
          {actionPlan.length > 0 && (
            <section className="improvement-panel-card improvement-panel-card-emerald">
              <div className="mb-4 flex items-start gap-3">
                <div className="improvement-panel-icon improvement-panel-icon-emerald">
                  <LayoutList size={18} />
                </div>
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500 dark:text-slate-400">
                    {t('jobDetails.executionPlan')}
                  </p>
                  <h3 className="mt-1 text-base font-semibold text-slate-900 dark:text-slate-100">
                    {t('jobDetails.executionTitle')}
                  </h3>
                </div>
              </div>
              <ul className="space-y-2">
                {actionPlan.map((item, index) => (
                  <li key={`plan-${index}`} className="improvement-panel-list-item">
                    <span className="improvement-panel-bullet improvement-panel-bullet-emerald" aria-hidden="true" />
                    <span className="min-w-0 break-words text-sm leading-6 text-slate-700 dark:text-slate-300">
                      {item}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {matchNextSteps.length === 0 && matchReorderSuggestions.length === 0 && (
            <p className="text-sm text-slate-500 dark:text-slate-400">--</p>
          )}
        </div>
      )}
    </div>
  );
}
