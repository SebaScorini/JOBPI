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
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      {/* Header Info */}
      <div className="flex flex-wrap items-center gap-3">
        <span className="px-3 py-1 bg-purple-100 text-purple-700 font-medium text-sm rounded-full">
          {result.seniority}
        </span>
        <span className="px-3 py-1 bg-emerald-100 text-emerald-700 font-medium text-sm rounded-full">
          {result.role_type}
        </span>
      </div>

      {/* Summary */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Summary</h3>
        <p className="text-gray-600 leading-relaxed">{result.summary}</p>
      </div>

      {sections.map((section) => (
        <div key={section.title}>
          <h3 className="text-lg font-semibold text-gray-900 mb-3">{section.title}</h3>
          {section.items.length > 0 ? (
            <ul className="space-y-2">
              {section.items.map((item, index) => (
                <li key={index} className="flex items-start text-gray-600">
                  <span className="mr-2 mt-1.5 h-1.5 w-1.5 rounded-full bg-blue-500 flex-shrink-0" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-500 italic text-sm">No specific items extracted.</p>
          )}
        </div>
      ))}

    </div>
  );
}
