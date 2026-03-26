import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiService } from '../services/api';
import { JobAnalysisResponse, StoredCV, CVJobMatch } from '../types';
import { Briefcase, ArrowLeft, Loader2, CheckCircle2, ChevronRight, Zap } from 'lucide-react';

export function JobDetailsPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<JobAnalysisResponse | null>(null);
  const [cvs, setCvs] = useState<StoredCV[]>([]);
  const [selectedCvId, setSelectedCvId] = useState<number | ''>('');
  
  const [isJobLoading, setIsJobLoading] = useState(true);
  const [isMatchLoading, setIsMatchLoading] = useState(false);
  const [matchResult, setMatchResult] = useState<CVJobMatch | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      if (!jobId) return;
      try {
        const [jobData, cvsData] = await Promise.all([
          apiService.getJob(parseInt(jobId)),
          apiService.listCVs()
        ]);
        setJob(jobData);
        setCvs(cvsData);
        if (cvsData.length > 0) {
          setSelectedCvId(cvsData[0].id);
        }
      } catch (err) {
        console.error('Failed to load data', err);
        setError('Failed to load job details.');
      } finally {
        setIsJobLoading(false);
      }
    }
    loadData();
  }, [jobId]);

  const handleMatch = async () => {
    if (!jobId || !selectedCvId) return;
    setIsMatchLoading(true);
    setMatchResult(null);
    setError(null);

    try {
      const result = await apiService.matchCVToJob(parseInt(jobId), Number(selectedCvId));
      setMatchResult(result);
    } catch (err: any) {
      setError(err.message || 'Failed to match CV.');
    } finally {
      setIsMatchLoading(false);
    }
  };

  if (isJobLoading) {
    return (
      <div className="flex justify-center py-20 animate-in fade-in duration-300">
        <Loader2 className="animate-spin text-brand-primary h-8 w-8" />
      </div>
    );
  }

  if (!job) {
    return (
      <div className="text-center py-20">
        <h2 className="text-2xl font-bold mb-4">Job Not Found</h2>
        <Link to="/jobs" className="text-brand-primary hover:underline">Return to jobs</Link>
      </div>
    );
  }

  return (
    <div className="animate-in fade-in duration-300 pb-20">
      <Link to="/jobs" className="inline-flex items-center text-sm font-semibold text-slate-500 hover:text-brand-primary mb-6 transition-colors">
        <ArrowLeft size={16} className="mr-2" /> Back to Analysis
      </Link>

      <div className="flex flex-col lg:flex-row gap-8">
        {/* Main Details */}
        <div className="flex-1 space-y-8">
          <div>
            <div className="flex items-center gap-4 mb-4">
              <div className="w-14 h-14 rounded-2xl bg-brand-primary/10 flex items-center justify-center text-brand-primary">
                <Briefcase size={28} />
              </div>
              <div>
                <h1 className="text-3xl font-heading font-extrabold text-brand-text dark:text-white leading-tight">
                  {job.title || job.role_type || 'Untitled Role'}
                </h1>
                <p className="text-lg text-slate-500 font-medium">
                  {job.company || job.seniority || 'Unknown Company'}
                </p>
              </div>
            </div>
            
            <div className="glass-card-solid p-6 rounded-2xl">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500 mb-3">Executive Summary</h2>
              <p className="text-slate-700 dark:text-slate-300 leading-relaxed text-[15px]">{job.summary}</p>
            </div>
          </div>

          <div className="grid sm:grid-cols-2 gap-6">
            <div className="glass-card-solid p-6 rounded-2xl border-l-[4px] border-l-brand-primary">
              <h3 className="font-bold text-lg mb-4 flex items-center gap-2"> Required Skills</h3>
              <ul className="space-y-3">
                {job.required_skills?.map((skill: string, i: number) => (
                  <li key={i} className="flex items-start text-[15px] text-slate-700 dark:text-slate-300 font-medium leading-tight">
                    <CheckCircle2 size={18} className="text-brand-primary mr-3 flex-shrink-0 mt-0.5" />
                    <span>{skill}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="glass-card-solid p-6 rounded-2xl border-l-[4px] border-l-brand-secondary/50">
              <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
                 Nice to Have
              </h3>
              <ul className="space-y-3">
                {job.nice_to_have_skills?.map((skill: string, i: number) => (
                  <li key={i} className="flex items-start text-[15px] text-slate-600 dark:text-slate-400 font-medium leading-tight">
                    <ChevronRight size={18} className="text-slate-400 mr-2 flex-shrink-0" />
                    <span>{skill}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
          
          <div className="glass-card-solid p-6 rounded-2xl">
              <h3 className="font-bold text-lg mb-4">Core Responsibilities</h3>
              <ul className="space-y-3 list-disc pl-5">
                {job.responsibilities?.map((res: string, i: number) => (
                  <li key={i} className="text-slate-700 dark:text-slate-300 leading-relaxed">{res}</li>
                ))}
              </ul>
          </div>
        </div>

        {/* Sidebar Logic Panel */}
        <div className="w-full lg:w-[400px] shrink-0 space-y-6 lg:sticky lg:top-[100px] lg:self-start">
          <div className="glass-card p-6 rounded-[2rem]">
            <h2 className="text-xl font-heading font-bold text-brand-text dark:text-white mb-2">
              Match Analysis
            </h2>
            <p className="text-sm text-slate-500 mb-6">Select a CV from your library to evaluate fitment against this role.</p>

            {cvs.length === 0 ? (
              <div className="bg-slate-100 dark:bg-slate-800 p-4 rounded-xl text-center text-sm text-slate-500">
                You need to <Link to="/library" className="text-brand-primary hover:underline">upload a CV</Link> first.
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold mb-2 text-slate-500 uppercase">Target CV</label>
                  <select 
                    value={selectedCvId} 
                    onChange={e => setSelectedCvId(Number(e.target.value))}
                    className="input-field"
                  >
                    <option value="" disabled>Select CV...</option>
                    {cvs.map(cv => (
                      <option key={cv.id} value={cv.id}>{cv.name}</option>
                    ))}
                  </select>
                </div>
                <button 
                  onClick={handleMatch}
                  disabled={isMatchLoading || !selectedCvId}
                  className="btn-primary flex items-center justify-center gap-2 text-[15px]" 
                >
                  {isMatchLoading ? (
                    <><Loader2 size={18} className="animate-spin" /> Evaluating...</>
                  ) : (
                    <><Zap size={18} /> Run Algorithm</>
                  )}
                </button>
              </div>
            )}
            
            {error && <p className="text-red-500 text-sm mt-4">{error}</p>}
          </div>

          {matchResult && matchResult.result && (
            <div className="glass-card border-brand-primary/20 bg-brand-primary/5 p-6 rounded-[2rem] animate-in slide-in-from-bottom-4 duration-500">
               <h3 className="font-heading font-bold text-xl mb-4 text-brand-text dark:text-white">
                 Match Results
               </h3>
               <div className="mb-4">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Fit Level</span>
                  <div className={`mt-1 text-lg font-bold ${matchResult.result.likely_fit_level === 'Strong' ? 'text-brand-cta' : matchResult.result.likely_fit_level === 'Moderate' ? 'text-amber-500' : 'text-rose-500'}`}>
                    {matchResult.result.likely_fit_level} Match
                  </div>
               </div>
               
               <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed mb-6">
                 {matchResult.result.fit_summary}
               </p>

               <div className="space-y-4">
                 <div>
                   <h4 className="text-sm font-bold text-slate-900 dark:text-white mb-2 flex items-center gap-2">
                     <span className="w-1.5 h-1.5 rounded-full bg-brand-cta"></span> Strengths
                   </h4>
                   <ul className="text-sm space-y-1.5">
                     {matchResult.result.strengths?.map((s: string, i: number) => (
                       <li key={i} className="text-slate-600 dark:text-slate-400" title={s}>• {s}</li>
                     ))}
                   </ul>
                 </div>
                 
                 {matchResult.result.missing_skills?.length > 0 && (
                 <div>
                   <h4 className="text-sm font-bold text-slate-900 dark:text-white mb-2 flex items-center gap-2">
                     <span className="w-1.5 h-1.5 rounded-full bg-rose-500"></span> Gaps
                   </h4>
                   <ul className="text-sm space-y-1.5 items-start">
                     {matchResult.result.missing_skills?.map((s: string, i: number) => (
                       <li key={i} className="text-slate-600 dark:text-slate-400 text-left" title={s}>• {s}</li>
                     ))}
                   </ul>
                 </div>
                 )}
               </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
