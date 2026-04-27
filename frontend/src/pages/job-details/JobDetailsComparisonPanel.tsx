import {
  Check,
  Copy,
  GitCompareArrows,
  Loader2,
  SearchCheck,
  ShieldAlert,
  Trophy,
} from 'lucide-react';
import type { CVComparisonResult, StoredCV } from '../../types';

interface JobDetailsComparisonPanelProps {
  cvs: StoredCV[];
  compareCvIdA: number | '';
  compareCvIdB: number | '';
  setCompareCvIdA: (value: number) => void;
  setCompareCvIdB: (value: number) => void;
  isCompareLoading: boolean;
  handleCompare: () => void;
  comparisonResult: CVComparisonResult | null;
  cvA: StoredCV | null;
  cvB: StoredCV | null;
  comparisonExplanationBlocks: string[];
  copiedSection: 'cover' | 'match' | 'comparison' | null;
  handleCopyText: (text: string, section: 'cover' | 'match' | 'comparison') => void;
  t: (key: string, params?: Record<string, string | number>) => string;
}

interface CompareListProps {
  tone: 'emerald' | 'amber' | 'sky';
  eyebrow: string;
  title: string;
  icon: React.ReactNode;
  items: string[];
}

function CompareList({ tone, eyebrow, title, icon, items }: CompareListProps) {
  const colorMap = {
    emerald: {
      card: 'border-emerald-200/80 bg-[linear-gradient(180deg,rgba(236,253,245,0.96),rgba(255,255,255,0.92))] dark:border-emerald-900/50 dark:bg-[linear-gradient(180deg,rgba(6,78,59,0.2),rgba(15,23,42,0.72))]',
      icon: 'bg-emerald-500/15 text-emerald-700 dark:bg-emerald-400/15 dark:text-emerald-200',
      bullet: 'bg-emerald-500',
    },
    amber: {
      card: 'border-amber-200/80 bg-[linear-gradient(180deg,rgba(255,251,235,0.96),rgba(255,255,255,0.92))] dark:border-amber-900/50 dark:bg-[linear-gradient(180deg,rgba(69,26,3,0.22),rgba(15,23,42,0.72))]',
      icon: 'bg-amber-500/15 text-amber-700 dark:bg-amber-400/15 dark:text-amber-200',
      bullet: 'bg-amber-500',
    },
    sky: {
      card: 'border-sky-200/80 bg-[linear-gradient(180deg,rgba(240,249,255,0.96),rgba(255,255,255,0.92))] dark:border-sky-900/50 dark:bg-[linear-gradient(180deg,rgba(12,74,110,0.2),rgba(15,23,42,0.72))]',
      icon: 'bg-sky-500/15 text-sky-700 dark:bg-sky-400/15 dark:text-sky-200',
      bullet: 'bg-sky-500',
    },
  };
  const c = colorMap[tone];

  if (!items.length) return null;

  return (
    <div className={`improvement-panel-card rounded-[24px] border p-4 ${c.card}`}>
      <div className="mb-3 flex items-center gap-3">
        <div className={`improvement-panel-icon ${c.icon}`}>{icon}</div>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500 dark:text-slate-400">
            {eyebrow}
          </p>
          <h3 className="mt-0.5 text-sm font-semibold text-slate-900 dark:text-slate-100">{title}</h3>
        </div>
      </div>
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li key={i} className="improvement-panel-list-item">
            <span className={`improvement-panel-bullet ${c.bullet}`} aria-hidden="true" />
            <span className="min-w-0 break-words text-sm leading-6 text-slate-700 dark:text-slate-300">{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function JobDetailsComparisonPanel({
  cvs,
  compareCvIdA,
  compareCvIdB,
  setCompareCvIdA,
  setCompareCvIdB,
  isCompareLoading,
  handleCompare,
  comparisonResult,
  cvA,
  cvB,
  comparisonExplanationBlocks,
  copiedSection,
  handleCopyText,
  t,
}: JobDetailsComparisonPanelProps) {
  return (
    <div className="space-y-5">
      {/* Workspace card */}
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
            <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
              {t('jobDetails.compareWorkspaceBody')}
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              <select
                value={compareCvIdA}
                onChange={(e) => setCompareCvIdA(Number(e.target.value))}
                className="input-field !py-2.5 text-sm"
              >
                <option value="" disabled>
                  {t('common.selectCv')}
                </option>
                {cvs.map((cv) => (
                  <option key={`a-${cv.id}`} value={cv.id}>
                    {cv.name}
                  </option>
                ))}
              </select>
              <select
                value={compareCvIdB}
                onChange={(e) => setCompareCvIdB(Number(e.target.value))}
                className="input-field !py-2.5 text-sm"
              >
                <option value="" disabled>
                  {t('common.selectCv')}
                </option>
                {cvs.map((cv) => (
                  <option key={`b-${cv.id}`} value={cv.id} disabled={cv.id === Number(compareCvIdA)}>
                    {cv.name}
                  </option>
                ))}
              </select>
            </div>
            <button
              onClick={handleCompare}
              disabled={isCompareLoading || !compareCvIdA || !compareCvIdB || compareCvIdA === compareCvIdB}
              className="btn-primary flex items-center justify-center gap-2 !py-2.5 text-sm"
            >
              {isCompareLoading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  {t('jobDetails.comparing')}
                </>
              ) : (
                <>
                  <GitCompareArrows size={16} />
                  {t('jobDetails.compareCvs')}
                </>
              )}
            </button>
          </div>
        )}
      </section>

      {/* Results */}
      {comparisonResult && cvA && cvB ? (
        <>
          {/* Winner hero */}
          <section className="improvement-panel-hero">
            <div className="improvement-panel-glow improvement-panel-glow-primary" aria-hidden="true" />
            <div className="improvement-panel-glow improvement-panel-glow-secondary" aria-hidden="true" />
            <div className="relative z-[1] flex flex-wrap items-start justify-between gap-4">
              <div className="space-y-2">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500 dark:text-slate-400">
                  {t('jobDetails.comparisonResult')}
                </p>
                <h2 className="text-xl font-semibold tracking-tight text-slate-950 dark:text-slate-50 md:text-2xl">
                  {comparisonResult.winner.label}
                </h2>
                {comparisonExplanationBlocks.length > 0 && (
                  <p className="max-w-2xl text-sm leading-7 text-slate-600 dark:text-slate-300">
                    {comparisonExplanationBlocks[0]}
                  </p>
                )}
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
                {copiedSection === 'comparison' ? (
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
          </section>

          {/* Three columns */}
          <div className="grid gap-4 md:grid-cols-3">
            <CompareList
              tone="emerald"
              eyebrow={t('jobDetails.comparativeStrengths')}
              title={t('jobDetails.comparisonStrengthsTitle')}
              icon={<Trophy size={18} />}
              items={comparisonResult.comparative_strengths}
            />
            <CompareList
              tone="amber"
              eyebrow={t('jobDetails.comparativeWeaknesses')}
              title={t('jobDetails.comparisonWeaknessesTitle')}
              icon={<ShieldAlert size={18} />}
              items={comparisonResult.comparative_weaknesses}
            />
            <CompareList
              tone="sky"
              eyebrow={t('jobDetails.jobAlignmentBreakdown')}
              title={t('jobDetails.comparisonAlignmentTitle')}
              icon={<SearchCheck size={18} />}
              items={comparisonResult.job_alignment_breakdown}
            />
          </div>
        </>
      ) : null}
    </div>
  );
}
