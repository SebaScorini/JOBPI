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
import type { ReactNode } from 'react';
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

interface ImprovementSectionProps {
  title: string;
  eyebrow: string;
  tone: 'amber' | 'sky' | 'emerald' | 'violet' | 'slate';
  icon: ReactNode;
  items: string[];
  footer?: ReactNode;
}

function ImprovementSection({ title, eyebrow, tone, icon, items, footer }: ImprovementSectionProps) {
  if (!items.length) {
    return null;
  }

  return (
    <section className={`improvement-panel-card improvement-panel-card-${tone}`}>
      <div className="mb-4 flex items-start gap-3">
        <div className={`improvement-panel-icon improvement-panel-icon-${tone}`}>{icon}</div>
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500 dark:text-slate-400">
            {eyebrow}
          </p>
          <h3 className="mt-1 text-base font-semibold text-slate-900 dark:text-slate-100">{title}</h3>
        </div>
      </div>

      <ul className="space-y-3">
        {items.map((item, index) => (
          <li
            key={`${title}-${index}`}
            className="improvement-panel-list-item"
          >
            <span className={`improvement-panel-bullet improvement-panel-bullet-${tone}`} aria-hidden="true" />
            <span className="min-w-0 break-words text-sm leading-6 text-slate-700 dark:text-slate-300">{item}</span>
          </li>
        ))}
      </ul>

      {footer ? <div className="mt-4 border-t border-white/60 pt-4 dark:border-slate-800/80">{footer}</div> : null}
    </section>
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

  const atsChecklist = [
    ...additionalMissingKeywords.map((keyword) => t('jobDetails.atsKeywordPrompt', { keyword })),
    ...matchSuggestions.filter((item) => {
      const lowered = item.toLowerCase();
      return (
        lowered.includes('keyword') ||
        lowered.includes('wording') ||
        lowered.includes('summary') ||
        lowered.includes('skills') ||
        lowered.includes('resumen') ||
        lowered.includes('exacta')
      );
    }),
  ];

  const recruiterChecklist = [
    ...matchResult.missing_skills.map((item) => t('jobDetails.recruiterGapPrompt', { gap: item })),
    ...matchSuggestions.filter((item) => {
      const lowered = item.toLowerCase();
      return (
        lowered.includes('metric') ||
        lowered.includes('impact') ||
        lowered.includes('project') ||
        lowered.includes('bullet') ||
        lowered.includes('logro') ||
        lowered.includes('proyecto')
      );
    }),
  ];

  const actionPlan = [...matchReorderSuggestions, ...matchNextSteps];
  const atsDirectImprovements = matchResult.result.ats_improvements ?? [];
  const recruiterDirectImprovements = matchResult.result.recruiter_improvements ?? [];
  const rewrittenBullets = matchResult.result.rewritten_bullets ?? [];

  const hasRawSections =
    matchSuggestions.length > 0 ||
    matchResult.missing_skills.length > 0 ||
    additionalMissingKeywords.length > 0 ||
    matchReorderSuggestions.length > 0 ||
    matchNextSteps.length > 0;

  const hasGuidedSections =
    atsChecklist.length > 0 ||
    recruiterChecklist.length > 0 ||
    actionPlan.length > 0 ||
    atsDirectImprovements.length > 0 ||
    recruiterDirectImprovements.length > 0 ||
    rewrittenBullets.length > 0;

  const priorityCount = atsChecklist.length + recruiterChecklist.length + actionPlan.length;
  const evidenceCount = matchResult.missing_skills.length + additionalMissingKeywords.length;
  const rewrittenCount = rewrittenBullets.length;

  const handleCopyBullets = async () => {
    if (!rewrittenBullets.length) return;
    await navigator.clipboard.writeText(rewrittenBullets.map((item) => `- ${item}`).join('\n'));
    setCopiedBullets(true);
    window.setTimeout(() => setCopiedBullets(false), 2000);
  };

  const strengthsPreview = matchResult.strengths?.slice(0, 3) ?? [];

  return (
    <div className="space-y-5">
      <section className="improvement-panel-hero">
        <div className="improvement-panel-glow improvement-panel-glow-primary" aria-hidden="true" />
        <div className="improvement-panel-glow improvement-panel-glow-secondary" aria-hidden="true" />

        <div className="relative z-[1] grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_340px]">
          <div className="space-y-5">
            <div className="flex flex-wrap items-center gap-3">
              <span className="improvement-panel-badge">
                <Sparkles size={14} />
                {t('jobDetails.improveCv')}
              </span>
              {rewrittenCount > 0 ? (
                <span className="improvement-panel-badge improvement-panel-badge-muted">
                  {t('jobDetails.rewrittenCount', { count: rewrittenCount })}
                </span>
              ) : null}
            </div>

            <div className="max-w-3xl">
              <h2 className="text-2xl font-semibold tracking-tight text-slate-950 dark:text-slate-50 md:text-[2rem]">
                {t('jobDetails.improvementHeroTitle')}
              </h2>
              <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600 dark:text-slate-300 md:text-[15px]">
                {t('jobDetails.improvementHeroBody')}
              </p>
            </div>

            {strengthsPreview.length > 0 ? (
              <div className="rounded-2xl border border-slate-100 bg-white p-4 backdrop-blur-sm dark:border-slate-800/80 dark:bg-slate-950/35">
                <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500 dark:text-slate-400">
                  {t('jobDetails.keepTheseSignals')}
                </p>
                <div className="flex flex-wrap gap-2.5">
                  {strengthsPreview.map((item, index) => (
                    <span
                      key={`strength-${index}`}
                      className="rounded-full border border-emerald-200/80 bg-emerald-50/90 px-3 py-1.5 text-xs font-medium text-emerald-900 dark:border-emerald-900/60 dark:bg-emerald-950/30 dark:text-emerald-200"
                    >
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            ) : null}
          </div>

          <aside className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
            <div className="improvement-panel-stat-card">
              <div className="improvement-panel-stat-icon bg-amber-500/15 text-amber-700 dark:bg-amber-400/15 dark:text-amber-200">
                <SearchCheck size={18} />
              </div>
              <p className="mt-4 text-3xl font-semibold tracking-tight text-slate-950 dark:text-slate-50">{priorityCount}</p>
              <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{t('jobDetails.prioritySignals')}</p>
            </div>

            <div className="improvement-panel-stat-card">
              <div className="improvement-panel-stat-icon bg-sky-500/15 text-sky-700 dark:bg-sky-400/15 dark:text-sky-200">
                <Target size={18} />
              </div>
              <p className="mt-4 text-3xl font-semibold tracking-tight text-slate-950 dark:text-slate-50">{evidenceCount}</p>
              <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{t('jobDetails.proofPoints')}</p>
            </div>

            <div className="improvement-panel-stat-card">
              <div className="improvement-panel-stat-icon bg-violet-500/15 text-violet-700 dark:bg-violet-400/15 dark:text-violet-200">
                <FilePenLine size={18} />
              </div>
              <p className="mt-4 text-3xl font-semibold tracking-tight text-slate-950 dark:text-slate-50">{rewrittenCount}</p>
              <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{t('jobDetails.readyToPaste')}</p>
            </div>
          </aside>
        </div>
      </section>

      <div className="columns-1 xl:columns-2 gap-5 [&>section]:break-inside-avoid [&>section]:mb-5">
        {atsChecklist.length > 0 && (
          <ImprovementSection
            eyebrow={t('jobDetails.atsChecklist')}
            title={t('jobDetails.atsTitle')}
            tone="amber"
            icon={<SearchCheck size={18} />}
            items={atsChecklist}
            footer={
              atsDirectImprovements.length > 0 ? (
                <div className="space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                    {t('jobDetails.aiBoost')}
                  </p>
                  <ul className="space-y-2">
                    {atsDirectImprovements.map((item, index) => (
                      <li key={`ats-direct-${index}`} className="improvement-panel-inline-item">
                        <ArrowRight size={14} className="mt-1 shrink-0 text-amber-700 dark:text-amber-300" />
                        <span className="break-words text-sm leading-6 text-slate-700 dark:text-slate-300">{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null
            }
          />
        )}

        {recruiterChecklist.length > 0 && (
          <ImprovementSection
            eyebrow={t('jobDetails.recruiterChecklist')}
            title={t('jobDetails.recruiterTitle')}
            tone="sky"
            icon={<Target size={18} />}
            items={recruiterChecklist}
            footer={
              recruiterDirectImprovements.length > 0 ? (
                <div className="space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                    {t('jobDetails.aiBoost')}
                  </p>
                  <ul className="space-y-2">
                    {recruiterDirectImprovements.map((item, index) => (
                      <li key={`recruiter-direct-${index}`} className="improvement-panel-inline-item">
                        <ArrowRight size={14} className="mt-1 shrink-0 text-sky-700 dark:text-sky-300" />
                        <span className="break-words text-sm leading-6 text-slate-700 dark:text-slate-300">{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null
            }
          />
        )}

        {rewrittenBullets.length > 0 ? (
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

            <div className="grid gap-3 grid-cols-1">
              {rewrittenBullets.map((item, index) => (
                <article
                  key={`bullet-${index}`}
                  className="rounded-2xl border border-violet-200/70 bg-white p-4 shadow-[0_18px_40px_rgba(91,33,182,0.08)] dark:border-violet-900/40 dark:bg-slate-950/45 dark:shadow-none"
                >
                  <div className="mb-3 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-violet-700 dark:text-violet-300">
                    <Sparkles size={13} />
                    {t('jobDetails.pasteReadyBullet', { count: index + 1 })}
                  </div>
                  <p className="text-sm leading-7 text-slate-700 dark:text-slate-300">{item}</p>
                </article>
              ))}
            </div>
          </section>
        ) : null}

        {actionPlan.length > 0 && (
          <ImprovementSection
            eyebrow={t('jobDetails.executionPlan')}
            title={t('jobDetails.executionTitle')}
            tone="emerald"
            icon={<LayoutList size={18} />}
            items={actionPlan}
          />
        )}

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

          {matchSuggestions.length > 0 ? (
            <ul className="space-y-3">
              {matchSuggestions.map((item, index) => (
                <li key={`suggestion-${index}`} className="improvement-panel-inline-item">
                  <span className="mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-900 text-[11px] font-semibold text-white dark:bg-slate-100 dark:text-slate-950">
                    {index + 1}
                  </span>
                  <span className="break-words text-sm leading-6 text-slate-700 dark:text-slate-300">{item}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500 dark:text-slate-400">--</p>
          )}
        </section>

        {additionalMissingKeywords.length > 0 ? (
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

            <div className="flex flex-wrap gap-2.5">
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
        ) : null}

        {matchResult.missing_skills?.length > 0 ? (
          <section className="improvement-panel-sidebar-card">
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

            <ul className="space-y-3">
              {matchResult.missing_skills.map((item, index) => (
                <li key={`gap-${index}`} className="improvement-panel-inline-item">
                  <ArrowRight size={14} className="mt-1 shrink-0 text-sky-700 dark:text-sky-300" />
                  <span className="break-words text-sm leading-6 text-slate-700 dark:text-slate-300">{item}</span>
                </li>
              ))}
            </ul>
          </section>
        ) : null}
      </div>

      {!hasRawSections && !hasGuidedSections ? (
        <p className="text-sm text-slate-500 dark:text-slate-400">--</p>
      ) : null}
    </div>
  );
}
