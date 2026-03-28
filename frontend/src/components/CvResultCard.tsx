import { CvAnalysisResponse, MatchLevel } from '../types';

interface CvResultCardProps {
  result: CvAnalysisResponse;
  matchLevel: MatchLevel;
}

const MATCH_LEVEL_COLORS: Record<MatchLevel, string> = {
  strong: 'border-emerald-200/70 bg-emerald-100/90 text-emerald-700 dark:border-emerald-500/20 dark:bg-emerald-500/10 dark:text-emerald-300',
  medium: 'border-amber-200/70 bg-amber-100/90 text-amber-700 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-300',
  weak: 'border-rose-200/70 bg-rose-100/90 text-rose-700 dark:border-rose-500/20 dark:bg-rose-500/10 dark:text-rose-300',
};

type ResultListKey = keyof Pick<
  CvAnalysisResponse,
  'strengths' | 'missing_skills' | 'resume_improvements' | 'interview_focus' | 'next_steps'
>;

interface SectionDefinition {
  key: ResultListKey;
  title: string;
  eyebrow: string;
  accentClass: string;
  emptyLabel: string;
  asChips?: boolean;
}

const primarySections: SectionDefinition[] = [
  {
    key: 'strengths',
    title: 'Strengths',
    eyebrow: 'What aligns well',
    accentClass: 'bg-emerald-500',
    emptyLabel: 'No standout strengths were identified.',
  },
  {
    key: 'missing_skills',
    title: 'Missing skills',
    eyebrow: 'What may hold this CV back',
    accentClass: 'bg-rose-500',
    emptyLabel: 'No important gaps were identified.',
    asChips: true,
  },
  {
    key: 'next_steps',
    title: 'Next steps',
    eyebrow: 'Recommended actions',
    accentClass: 'bg-sky-500',
    emptyLabel: 'No next steps were provided.',
  },
];

const secondarySections: SectionDefinition[] = [
  {
    key: 'resume_improvements',
    title: 'Resume improvements',
    eyebrow: 'Presentation refinements',
    accentClass: 'bg-violet-500',
    emptyLabel: 'No resume improvements were suggested.',
  },
  {
    key: 'interview_focus',
    title: 'Interview focus',
    eyebrow: 'Topics to prepare',
    accentClass: 'bg-amber-500',
    emptyLabel: 'No interview focus areas were suggested.',
  },
];

function SectionCard({ result, section }: { result: CvAnalysisResponse; section: SectionDefinition }) {
  const items = result[section.key];

  return (
    <section className="rounded-[1.75rem] border border-slate-200/70 bg-white/90 p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950/40">
      <div className="mb-4 flex items-center gap-3">
        <span className={`h-9 w-1.5 rounded-full ${section.accentClass}`} />
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
            {section.eyebrow}
          </p>
          <h3 className="text-lg font-bold text-slate-950 dark:text-white">{section.title}</h3>
        </div>
      </div>

      {items.length > 0 ? (
        section.asChips ? (
          <div className="flex flex-wrap gap-2">
            {items.map((item, index) => (
              <span
                key={index}
                className="inline-flex items-center rounded-xl border border-slate-200 bg-slate-100 px-3 py-1.5 text-sm font-medium text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
              >
                {item}
              </span>
            ))}
          </div>
        ) : (
          <ul className="space-y-3">
            {items.map((item, index) => (
              <li key={index} className="flex items-start gap-3 text-sm leading-6 text-slate-700 dark:text-slate-300">
                <span className={`mt-2 h-2 w-2 flex-shrink-0 rounded-full ${section.accentClass}`} />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        )
      ) : (
        <p className="text-sm italic text-slate-500 dark:text-slate-500">{section.emptyLabel}</p>
      )}
    </section>
  );
}

export function CvResultCard({ result, matchLevel }: CvResultCardProps) {
  const fitColorClass = MATCH_LEVEL_COLORS[matchLevel];

  return (
    <div className="glass-card rounded-[2rem] p-6 md:p-7 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 h-full">
      <section className="rounded-[1.75rem] border border-slate-200/70 bg-gradient-to-br from-slate-50 to-white p-5 shadow-sm dark:border-slate-800 dark:from-slate-900 dark:to-slate-950">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div className="space-y-2">
            <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-slate-500 dark:text-slate-400">
              Why this CV
            </p>
            <p className="text-sm leading-7 text-slate-700 dark:text-slate-300">{result.fit_summary}</p>
          </div>

          <div className="shrink-0">
            <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.2em] text-slate-500 dark:text-slate-400">
              Match level badge
            </p>
            <span className={`inline-flex rounded-full border px-4 py-2 text-xs font-bold uppercase tracking-[0.18em] ${fitColorClass}`}>
              {matchLevel} match
            </span>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        {primarySections.map((section) => (
          <SectionCard key={section.key} result={result} section={section} />
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {secondarySections.map((section) => (
          <SectionCard key={section.key} result={result} section={section} />
        ))}
      </div>
    </div>
  );
}
