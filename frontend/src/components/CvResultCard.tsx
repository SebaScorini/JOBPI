import { CvAnalysisResponse } from '../types';

interface CvResultCardProps {
  result: CvAnalysisResponse;
}

const FIT_COLORS: Record<string, string> = {
  Strong: 'bg-emerald-100 text-emerald-700',
  Moderate: 'bg-amber-100 text-amber-700',
  Weak: 'bg-red-100 text-red-700',
};

const sections = [
  { key: 'strengths', title: 'Your Strengths' },
  { key: 'missing_skills', title: 'Missing Skills' },
  { key: 'resume_improvements', title: 'Resume Improvements' },
  { key: 'interview_focus', title: 'Interview Focus Areas' },
  { key: 'next_steps', title: 'Next Steps' },
] as const;

export function CvResultCard({ result }: CvResultCardProps) {
  const fitColorClass = FIT_COLORS[result.likely_fit_level] ?? 'bg-gray-100 text-gray-700';

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-6">

      {/* Fit Level Badge */}
      <div className="flex flex-wrap items-center gap-3">
        <span className={`px-4 py-1.5 font-semibold text-sm rounded-full ${fitColorClass}`}>
          {result.likely_fit_level} Fit
        </span>
      </div>

      {/* Summary */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Fit Summary</h3>
        <p className="text-gray-600 leading-relaxed">{result.fit_summary}</p>
      </div>

      {/* Dynamic sections */}
      {sections.map(({ key, title }) => {
        const items = result[key];
        return (
          <div key={key}>
            <h3 className="text-lg font-semibold text-gray-900 mb-3">{title}</h3>
            {items.length > 0 ? (
              <ul className="space-y-2">
                {items.map((item, i) => (
                  <li key={i} className="flex items-start text-gray-600">
                    <span className="mr-2 mt-1.5 h-1.5 w-1.5 rounded-full bg-emerald-500 flex-shrink-0" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-400 italic text-sm">None identified.</p>
            )}
          </div>
        );
      })}
    </div>
  );
}
