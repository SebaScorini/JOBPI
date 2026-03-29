import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiService } from '../services/api';
import { JobAnalysisResponse, StoredCV, CVJobMatch, JobApplicationStatus } from '../types';
import { Briefcase, ArrowLeft, Loader2, CheckCircle2, ChevronRight, Zap } from 'lucide-react';

const statusOptions: Array<{ value: JobApplicationStatus; label: string }> = [
  { value: 'saved', label: 'Saved' },
  { value: 'applied', label: 'Applied' },
  { value: 'interview', label: 'Interview' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'offer', label: 'Offer' },
];

const statusBadgeMap: Record<JobApplicationStatus, string> = {
  saved: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
  applied: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  interview: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  rejected: 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300',
  offer: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
};

const statusLabelMap: Record<JobApplicationStatus, string> = {
  saved: 'Saved',
  applied: 'Applied',
  interview: 'Interview',
  rejected: 'Rejected',
  offer: 'Offer',
};

export function JobDetailsPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<JobAnalysisResponse | null>(null);
  const [cvs, setCvs] = useState<StoredCV[]>([]);
  const [selectedCvId, setSelectedCvId] = useState<number | ''>('');

  const [isJobLoading, setIsJobLoading] = useState(true);
  const [isMatchLoading, setIsMatchLoading] = useState(false);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const [isSavingNotes, setIsSavingNotes] = useState(false);
  const [notesDraft, setNotesDraft] = useState('');
  const [matchResult, setMatchResult] = useState<CVJobMatch | null>(null);
  const [error, setError] = useState<string | null>(null);
  const matchLevelTextClasses = {
    strong: 'text-brand-cta',
    medium: 'text-amber-500',
    weak: 'text-rose-500',
  } as const;
  const matchSuggestions = matchResult?.suggested_improvements ?? matchResult?.improvement_suggestions ?? [];
  const matchMissingKeywords = matchResult?.missing_keywords ?? [];
  const matchReorderSuggestions = matchResult?.reorder_suggestions ?? [];

  useEffect(() => {
    async function loadData() {
      if (!jobId) return;
      try {
        const [jobData, cvsData] = await Promise.all([
          apiService.getJob(parseInt(jobId)),
          apiService.listCVs(),
        ]);
        setJob(jobData);
        setNotesDraft(jobData.notes ?? '');
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

  const handleStatusChange = async (status: JobApplicationStatus) => {
    if (!jobId || !job) return;

    setIsUpdatingStatus(true);
    try {
      const payloadDate = status === 'applied' && !job.applied_date ? new Date().toISOString() : undefined;
      const updated = await apiService.updateJobStatus(Number(jobId), status, payloadDate);
      setJob(updated);
      setNotesDraft(updated.notes ?? '');
    } catch (err: any) {
      setError(err.message || 'Failed to update status.');
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  const handleSaveNotes = async () => {
    if (!jobId || !job) return;

    setIsSavingNotes(true);
    try {
      const updated = await apiService.updateJobNotes(Number(jobId), notesDraft.trim() || null);
      setJob(updated);
      setNotesDraft(updated.notes ?? '');
    } catch (err: any) {
      setError(err.message || 'Failed to save notes.');
    } finally {
      setIsSavingNotes(false);
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
                <div className="mt-2 flex items-center gap-2">
                  <span className={`px-2.5 py-1 text-xs font-semibold rounded-lg ${statusBadgeMap[job.status]}`}>
                    {statusLabelMap[job.status]}
                  </span>
                  {job.applied_date && (
                    <span className="text-xs text-slate-500">
                      Applied {new Date(job.applied_date).toLocaleDateString()}
                    </span>
                  )}
                </div>
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

        <div className="w-full lg:w-[400px] shrink-0 space-y-6 lg:sticky lg:top-[100px] lg:self-start">
          <div className="glass-card p-6 rounded-[2rem]">
            <h2 className="text-xl font-heading font-bold text-brand-text dark:text-white mb-4">
              Application Tracker
            </h2>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold mb-2 text-slate-500 uppercase">Status</label>
                <select
                  value={job.status}
                  onChange={(e) => handleStatusChange(e.target.value as JobApplicationStatus)}
                  disabled={isUpdatingStatus}
                  className="input-field"
                >
                  {statusOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold mb-2 text-slate-500 uppercase">Notes</label>
                <textarea
                  value={notesDraft}
                  onChange={(e) => setNotesDraft(e.target.value)}
                  rows={4}
                  placeholder="Add interview notes, recruiter updates, or reminders..."
                  className="input-field resize-y"
                />
              </div>

              <button
                onClick={handleSaveNotes}
                disabled={isSavingNotes}
                className="btn-secondary w-full flex items-center justify-center gap-2"
              >
                {isSavingNotes ? (
                  <><Loader2 size={16} className="animate-spin" /> Saving notes...</>
                ) : (
                  'Save Notes'
                )}
              </button>
            </div>
          </div>

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
                <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Match Level</span>
                <div className={`mt-1 text-lg font-bold uppercase ${matchLevelTextClasses[matchResult.match_level]}`}>
                  {matchResult.match_level}
                </div>
              </div>

              <div className="space-y-4">
                <div className="rounded-2xl border border-slate-200/70 dark:border-slate-800 bg-white/70 dark:bg-slate-950/30 p-4">
                  <h4 className="text-sm font-bold text-slate-900 dark:text-white mb-2">Why This CV</h4>
                  <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                    {matchResult.why_this_cv}
                  </p>
                </div>

                <div>
                  <h4 className="text-sm font-bold text-slate-900 dark:text-white mb-2 flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-brand-cta"></span> Strengths
                  </h4>
                  <ul className="text-sm space-y-1.5">
                    {matchResult.strengths?.map((s: string, i: number) => (
                      <li key={i} className="text-slate-600 dark:text-slate-400" title={s}>&bull; {s}</li>
                    ))}
                  </ul>
                </div>

                {matchResult.missing_skills?.length > 0 && (
                  <div>
                    <h4 className="text-sm font-bold text-slate-900 dark:text-white mb-2 flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-rose-500"></span> Missing Skills
                    </h4>
                    <ul className="text-sm space-y-1.5 items-start">
                      {matchResult.missing_skills?.map((s: string, i: number) => (
                        <li key={i} className="text-slate-600 dark:text-slate-400 text-left" title={s}>&bull; {s}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {(matchSuggestions.length > 0 || matchMissingKeywords.length > 0 || matchReorderSuggestions.length > 0) && (
                  <div>
                    <h4 className="text-sm font-bold text-slate-900 dark:text-white mb-2 flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span> How to improve this CV
                    </h4>

                    {matchSuggestions.length > 0 && (
                      <ul className="text-sm space-y-1.5 items-start mb-3">
                        {matchSuggestions.map((s: string, i: number) => (
                          <li key={i} className="text-slate-600 dark:text-slate-400 text-left" title={s}>&bull; {s}</li>
                        ))}
                      </ul>
                    )}

                    {matchMissingKeywords.length > 0 && (
                      <div className="mb-3 flex flex-wrap gap-2">
                        {matchMissingKeywords.map((keyword) => (
                          <span
                            key={keyword}
                            className="rounded-full border border-amber-200/80 bg-white/80 px-3 py-1 text-xs font-semibold text-amber-900 dark:border-amber-800 dark:bg-slate-950/40 dark:text-amber-200"
                          >
                            {keyword}
                          </span>
                        ))}
                      </div>
                    )}

                    {matchReorderSuggestions.length > 0 && (
                      <ul className="text-sm space-y-1.5 items-start">
                        {matchReorderSuggestions.map((s: string, i: number) => (
                          <li key={i} className="text-slate-600 dark:text-slate-400 text-left" title={s}>&bull; {s}</li>
                        ))}
                      </ul>
                    )}
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
