import { CvAnalysisResponse } from '../types';

interface CvResultCardProps {
  result: CvAnalysisResponse;
}

const FIT_COLORS: Record<string, string> = {
  Strong: 'bg-emerald-100/80 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-200/50 dark:border-emerald-500/20',
  Moderate: 'bg-amber-100/80 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-200/50 dark:border-amber-500/20',
  Weak: 'bg-rose-100/80 dark:bg-rose-500/10 text-rose-700 dark:text-rose-400 border border-rose-200/50 dark:border-rose-500/20',
};

const sections = [
  { key: 'strengths', title: 'Your Strengths' },
  { key: 'missing_skills', title: 'Missing Skills' },
  { key: 'resume_improvements', title: 'Resume Improvements' },
  { key: 'interview_focus', title: 'Interview Focus Areas' },
  { key: 'next_steps', title: 'Next Steps' },
] as const;

export function CvResultCard({ result }: CvResultCardProps) {
  const fitColorClass = FIT_COLORS[result.likely_fit_level] ?? 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700';

  return (
    <div className="glass-card rounded-3xl p-6 md:p-8 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 h-full">

      {/* Fit Level Badge */}
      <div className="flex flex-wrap items-center gap-3">
        <span className={`px-4 py-1.5 font-bold tracking-wide uppercase text-xs rounded-full shadow-sm ${fitColorClass}`}>
          {result.likely_fit_level} Fit
        </span>
      </div>

      {/* Summary */}
      <div className="bg-slate-50 dark:bg-[#0f172a] rounded-2xl p-5 border border-slate-100 dark:border-slate-800">
        <h3 className="text-sm font-bold tracking-widest text-slate-500 dark:text-slate-400 uppercase mb-3 text-center">Fit Summary</h3>
        <p className="text-slate-700 dark:text-slate-300 leading-relaxed font-medium">{result.fit_summary}</p>
      </div>

      {/* Dynamic sections */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-10">
        {sections.map(({ key, title }) => {
          const items = result[key];
          const isSkills = title.toLowerCase().includes('skills');

          return (
            <div key={key} className="relative">
              <h3 className="text-base font-bold tracking-wide text-slate-900 dark:text-white mb-4 flex items-center gap-2 border-b border-slate-100 dark:border-slate-800 pb-2">
                <span className="w-1.5 h-4 rounded-full bg-emerald-500 inline-block"></span>
                {title}
              </h3>
              
              {items.length > 0 ? (
                isSkills ? (
                  <div className="flex flex-wrap gap-2">
                    {items.map((item, i) => (
                      <span key={i} className="inline-flex items-center px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 text-sm font-medium transition-colors hover:bg-emerald-50 hover:border-emerald-300 dark:hover:bg-emerald-900/40 dark:hover:border-emerald-700">
                        {item}
                      </span>
                    ))}
                  </div>
                ) : (
                  <ul className="space-y-3 pl-2">
                    {items.map((item, i) => (
                      <li key={i} className="flex items-start text-slate-600 dark:text-slate-400 group">
                        <span className="mr-3 mt-2 h-1.5 w-1.5 rounded-full bg-slate-300 dark:bg-slate-600 group-hover:bg-emerald-400 transition-colors flex-shrink-0" />
                        <span className="leading-relaxed text-sm group-hover:text-slate-900 dark:group-hover:text-slate-200 transition-colors">{item}</span>
                      </li>
                    ))}
                  </ul>
                )
              ) : (
                <p className="text-slate-400 dark:text-slate-500 italic text-sm pl-2">None identified.</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
