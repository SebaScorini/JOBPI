import { JobAnalysisResponse } from '../types';

interface ResultCardProps {
  result: JobAnalysisResponse;
}

export function ResultCard({ result }: ResultCardProps) {
  const sections = [
    { title: 'Required Skills', items: result.required_skills },
    { title: 'Nice to Have Skills', items: result.nice_to_have_skills },
    { title: 'Responsibilities', items: result.responsibilities },
    { title: 'How to Prepare', items: result.how_to_prepare },
    { title: 'Learning Path', items: result.learning_path },
    { title: 'Missing Skills', items: result.missing_skills },
    { title: 'Resume Tips', items: result.resume_tips },
    { title: 'Interview Tips', items: result.interview_tips },
    { title: 'Portfolio Project Ideas', items: result.portfolio_project_ideas },
  ];

  return (
    <div className="glass-card rounded-3xl p-6 md:p-8 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 h-full">
      
      {/* Header Info */}
      <div className="flex flex-wrap items-center gap-3">
        <span className="px-4 py-1.5 bg-indigo-100/80 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-400 font-bold text-xs tracking-wide uppercase rounded-full border border-indigo-200/50 dark:border-indigo-500/20">
          {result.seniority}
        </span>
        <span className="px-4 py-1.5 bg-emerald-100/80 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 font-bold text-xs tracking-wide uppercase rounded-full border border-emerald-200/50 dark:border-emerald-500/20">
          {result.role_type}
        </span>
      </div>

      {/* Summary */}
      <div className="bg-slate-50 dark:bg-[#0f172a] rounded-2xl p-5 border border-slate-100 dark:border-slate-800">
        <h3 className="text-sm font-bold tracking-widest text-slate-500 dark:text-slate-400 uppercase mb-3 text-center">Executive Summary</h3>
        <p className="text-slate-700 dark:text-slate-300 leading-relaxed font-medium">{result.summary}</p>
      </div>

      {/* Grid for Content Sections */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-10">
        {sections.map((section) => {
          // Special handling for "Skills" to use badges
          const isSkills = section.title.toLowerCase().includes('skills');

          return (
            <div key={section.title} className="relative">
              <h3 className="text-base font-bold tracking-wide text-slate-900 dark:text-white mb-4 flex items-center gap-2 border-b border-slate-100 dark:border-slate-800 pb-2">
                <span className="w-1.5 h-4 rounded-full bg-sky-500 inline-block"></span>
                {section.title}
              </h3>
              
              {section.items.length > 0 ? (
                isSkills ? (
                  <div className="flex flex-wrap gap-2">
                    {section.items.map((item, index) => (
                      <span key={index} className="inline-flex items-center px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 text-sm font-medium transition-colors hover:bg-sky-50 hover:border-sky-300 dark:hover:bg-sky-900/40 dark:hover:border-sky-700">
                        {item}
                      </span>
                    ))}
                  </div>
                ) : (
                  <ul className="space-y-3 pl-2">
                    {section.items.map((item, index) => (
                      <li key={index} className="flex items-start text-slate-600 dark:text-slate-400 group">
                        <span className="mr-3 mt-2 h-1.5 w-1.5 rounded-full bg-slate-300 dark:bg-slate-600 group-hover:bg-sky-400 transition-colors flex-shrink-0" />
                        <span className="leading-relaxed text-sm group-hover:text-slate-900 dark:group-hover:text-slate-200 transition-colors">{item}</span>
                      </li>
                    ))}
                  </ul>
                )
              ) : (
                <p className="text-slate-400 dark:text-slate-500 italic text-sm pl-2">Section left blank in source.</p>
              )}
            </div>
          );
        })}
      </div>

    </div>
  );
}
