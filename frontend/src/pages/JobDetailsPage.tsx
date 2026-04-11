import { useEffect, useMemo, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import { JobAnalysisResponse, StoredCV, CVJobMatch, CVComparisonResult, JobApplicationStatus } from '../types';
import { Briefcase, ArrowLeft, Loader2, CheckCircle2, ChevronRight, Zap, Copy, Check, Trash2, Bookmark } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { useToast } from '../context/ToastContext';
import { SkeletonLoader } from '../components/SkeletonLoader';

type DetailsTab = 'overview' | 'match' | 'improvements' | 'cover' | 'tracker';

const statusBadgeMap: Record<JobApplicationStatus, string> = {
  saved: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
  applied: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  interview: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  rejected: 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300',
  offer: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
};

function splitReadableText(text?: string | null): string[] {
  if (!text) return [];

  const blocks = text
    .split(/\n+/)
    .map((item) => item.trim())
    .filter(Boolean);

  if (blocks.length !== 1) {
    return blocks;
  }

  const sentenceBlocks = blocks[0]
    .split(/(?<=[.!?])\s+(?=\S)/)
    .map((item) => item.trim())
    .filter(Boolean);

  return sentenceBlocks.length > 1 ? sentenceBlocks : blocks;
}

function normalizeComparableText(value: string): string {
  return value.trim().replace(/[.]+$/g, '').toLowerCase();
}

function dedupeItems(items: string[]): string[] {
  const seen = new Set<string>();
  const unique: string[] = [];

  for (const item of items) {
    const key = normalizeComparableText(item);
    if (!key || seen.has(key)) {
      continue;
    }
    seen.add(key);
    unique.push(item);
  }

  return unique;
}

export function JobDetailsPage() {
  const { aiLanguage, language, t } = useLanguage();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<JobAnalysisResponse | null>(null);
  const [cvs, setCvs] = useState<StoredCV[]>([]);
  const [selectedCvId, setSelectedCvId] = useState<number | ''>('');
  const [compareCvIdA, setCompareCvIdA] = useState<number | ''>('');
  const [compareCvIdB, setCompareCvIdB] = useState<number | ''>('');

  const [isJobLoading, setIsJobLoading] = useState(true);
  const [isMatchLoading, setIsMatchLoading] = useState(false);
  const [isCompareLoading, setIsCompareLoading] = useState(false);
  const [isCoverLetterLoading, setIsCoverLetterLoading] = useState(false);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const [isSavingNotes, setIsSavingNotes] = useState(false);
  const [isDeletingJob, setIsDeletingJob] = useState(false);
  const [isTogglingSaved, setIsTogglingSaved] = useState(false);
  const [notesDraft, setNotesDraft] = useState('');
  const [matchResult, setMatchResult] = useState<CVJobMatch | null>(null);
  const [comparisonResult, setComparisonResult] = useState<CVComparisonResult | null>(null);
  const [coverLetter, setCoverLetter] = useState('');
  const [copiedSection, setCopiedSection] = useState<'cover' | 'match' | 'comparison' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<DetailsTab>('overview');

  const matchLevelTextClasses = {
    strong: 'text-brand-cta',
    medium: 'text-amber-500',
    weak: 'text-rose-500',
  } as const;

  const matchSuggestions = dedupeItems(matchResult?.suggested_improvements ?? matchResult?.improvement_suggestions ?? []);
  const matchMissingKeywords = dedupeItems(matchResult?.missing_keywords ?? []);
  const matchReorderSuggestions = matchResult?.reorder_suggestions ?? [];
  const displayMissingSkills = dedupeItems(
    matchResult?.missing_skills?.length ? matchResult.missing_skills : matchMissingKeywords,
  );
  const additionalMissingKeywords = matchMissingKeywords.filter(
    (keyword) =>
      !matchResult?.missing_skills?.some(
        (skill) => normalizeComparableText(skill) === normalizeComparableText(keyword),
      ),
  );
  const comparisonExplanationBlocks = splitReadableText(comparisonResult?.overall_reason);
  const matchWhyBlocks = splitReadableText(matchResult?.why_this_cv);

  const statusOptions: Array<{ value: JobApplicationStatus; label: string }> = [
    { value: 'saved', label: t('statuses.saved') },
    { value: 'applied', label: t('statuses.applied') },
    { value: 'interview', label: t('statuses.interview') },
    { value: 'rejected', label: t('statuses.rejected') },
    { value: 'offer', label: t('statuses.offer') },
  ];

  useEffect(() => {
    let cancelled = false;

    async function loadData() {
      if (!jobId) return;

      setIsJobLoading(true);
      setError(null);

      try {
        const [jobData, cvsData] = await Promise.all([
          apiService.getJob(parseInt(jobId)),
          apiService.listCVs(),
        ]);

        if (cancelled) {
          return;
        }

        setJob(jobData);
        setNotesDraft(jobData.notes ?? '');
        setCvs(cvsData);
        setSelectedCvId((current) =>
          current && cvsData.some((cv) => cv.id === current) ? current : (cvsData[0]?.id ?? ''),
        );
        setCompareCvIdA((current) =>
          current && cvsData.some((cv) => cv.id === current) ? current : (cvsData[0]?.id ?? ''),
        );
        setCompareCvIdB((current) => {
          if (current && cvsData.some((cv) => cv.id === current)) {
            return current;
          }

          if (cvsData.length > 1) {
            return cvsData[1].id;
          }

          return '';
        });
      } catch (err) {
        if (cancelled) {
          return;
        }
        const message = err instanceof Error ? err.message : t('jobDetails.failedLoad');
        setError(message);
        showToast(message, 'error');
      } finally {
        if (!cancelled) {
          setIsJobLoading(false);
        }
      }
    }

    loadData();

    return () => {
      cancelled = true;
    };
  }, [jobId, showToast, t]);

  useEffect(() => {
    setCoverLetter('');
    setCopiedSection(null);
    setMatchResult(null);
    setError(null);
  }, [selectedCvId, jobId]);

  useEffect(() => {
    setComparisonResult(null);
    setError(null);
  }, [compareCvIdA, compareCvIdB, jobId]);

  const handleMatch = async () => {
    if (!jobId || !selectedCvId) return;
    setIsMatchLoading(true);
    setMatchResult(null);
    setComparisonResult(null);
    setError(null);

    try {
      const result = await apiService.matchCVToJob(parseInt(jobId), Number(selectedCvId), aiLanguage);
      setMatchResult(result);
      setActiveTab('match');
    } catch (err: any) {
      const message = err.message || t('jobDetails.failedMatch');
      setError(message);
      showToast(message, 'error');
    } finally {
      setIsMatchLoading(false);
    }
  };

  const handleCompare = async () => {
    if (!jobId || !compareCvIdA || !compareCvIdB) return;
    if (compareCvIdA === compareCvIdB) {
      const message = t('jobDetails.compareDifferentCvs');
      setError(message);
      showToast(message, 'warning');
      return;
    }

    setIsCompareLoading(true);
    setComparisonResult(null);
    setError(null);

    try {
      const result = await apiService.compareCVsForJob(parseInt(jobId), Number(compareCvIdA), Number(compareCvIdB), aiLanguage);
      setComparisonResult(result);
    } catch (err: any) {
      const message = err.message || t('jobDetails.failedCompare');
      setError(message);
      showToast(message, 'error');
    } finally {
      setIsCompareLoading(false);
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
      showToast(t('jobDetails.statusUpdatedSuccess'), 'success');
    } catch (err: any) {
      const message = err.message || t('jobDetails.failedStatus');
      setError(message);
      showToast(message, 'error');
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
      showToast(t('jobDetails.notesSavedSuccess'), 'success');
    } catch (err: any) {
      const message = err.message || t('jobDetails.failedNotes');
      setError(message);
      showToast(message, 'error');
    } finally {
      setIsSavingNotes(false);
    }
  };

  const handleGenerateCoverLetter = async () => {
    if (!jobId || !selectedCvId) return;

    setIsCoverLetterLoading(true);
    setCopiedSection(null);
    setError(null);

    try {
      const result = await apiService.generateCoverLetter(parseInt(jobId), Number(selectedCvId), aiLanguage);
      setCoverLetter(result.generated_cover_letter);
      setActiveTab('cover');
      showToast(t('jobDetails.coverLetterGeneratedSuccess'), 'success');
    } catch (err: any) {
      const message = err.message || t('jobDetails.failedCoverLetter');
      setError(message);
      showToast(message, 'error');
    } finally {
      setIsCoverLetterLoading(false);
    }
  };

  const handleToggleSaved = async () => {
    if (!jobId || !job) return;

    setIsTogglingSaved(true);
    try {
      const updated = await apiService.toggleSavedJob(Number(jobId));
      setJob(updated);
      showToast(updated.is_saved ? t('jobs.savedAdded') : t('jobs.savedRemoved'), 'success');
    } catch (err: any) {
      const message = err.message || t('jobs.failedSaveToggle');
      setError(message);
      showToast(message, 'error');
    } finally {
      setIsTogglingSaved(false);
    }
  };

  const handleDeleteJob = async () => {
    if (!jobId) return;

    const confirmed = window.confirm(t('jobs.confirmDelete'));
    if (!confirmed) {
      return;
    }

    setIsDeletingJob(true);
    setError(null);
    try {
      await apiService.deleteJob(Number(jobId));
      showToast(t('jobs.deletedSuccess'), 'success');
      navigate('/jobs');
    } catch (err: any) {
      const message = err.message || t('jobs.failedDelete');
      setError(message);
      showToast(message, 'error');
    } finally {
      setIsDeletingJob(false);
    }
  };

  const handleCopyText = async (text: string, section: 'cover' | 'match' | 'comparison') => {
    if (!text) return;

    try {
      await navigator.clipboard.writeText(text);
      setCopiedSection(section);
      showToast(t('common.copied'), 'success');
      window.setTimeout(() => setCopiedSection(null), 2000);
    } catch (err: any) {
      const message = err.message || t('jobDetails.failedCopy');
      setError(message);
      showToast(message, 'error');
    }
  };

  const cvA = cvs.find((cv) => cv.id === Number(compareCvIdA)) ?? null;
  const cvB = cvs.find((cv) => cv.id === Number(compareCvIdB)) ?? null;
  const selectedCv = cvs.find((cv) => cv.id === Number(selectedCvId)) ?? null;
  const bestCvLabel = comparisonResult?.winner?.label ?? selectedCv?.name ?? t('jobDetails.noCvSelected');

  const tabs: Array<{ id: DetailsTab; label: string }> = useMemo(
    () => [
      { id: 'overview', label: t('jobDetails.executiveSummary') },
      { id: 'match', label: t('jobDetails.matchTitle') },
      { id: 'improvements', label: t('jobDetails.improveCv') },
      { id: 'cover', label: t('jobDetails.coverLetterTitle') },
      { id: 'tracker', label: t('jobDetails.trackerTitle') },
    ],
    [t],
  );

  if (isJobLoading) {
    return (
      <div className="animate-in fade-in space-y-4 duration-300">
        <div className="skeleton-block h-6 w-32 rounded-xl" />
        <div className="glass-card rounded-3xl p-5">
          <div className="space-y-4">
            <div className="skeleton-block h-10 w-1/2 rounded-xl" />
            <SkeletonLoader lines={8} />
          </div>
        </div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="text-center py-20">
        <h2 className="text-2xl font-bold mb-4">{t('jobDetails.notFound')}</h2>
        <Link to="/jobs" className="text-brand-primary hover:underline">{t('jobDetails.returnToJobs')}</Link>
      </div>
    );
  }

  return (
    <div className="animate-in fade-in duration-300 space-y-4 pb-8">
      <Link to="/jobs" className="inline-flex items-center text-sm font-semibold text-slate-500 hover:text-brand-primary transition-colors">
        <ArrowLeft size={16} className="mr-2" /> {t('jobDetails.backToAnalysis')}
      </Link>

      <div className="grid grid-cols-1 2xl:grid-cols-[minmax(0,1fr)_320px] gap-4">
        <section className="min-w-0 space-y-4">
          <div className="glass-card p-4 lg:p-5 rounded-3xl">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0">
                <div className="flex items-center gap-3">
                  <div className="w-11 h-11 rounded-xl bg-brand-primary/10 flex items-center justify-center text-brand-primary shrink-0">
                    <Briefcase size={22} />
                  </div>
                  <div className="min-w-0">
                    <h1 className="text-2xl lg:text-3xl font-heading font-extrabold text-brand-text dark:text-white break-words">
                      {job.title || job.role_type || t('common.untitledRole')}
                    </h1>
                    <p className="text-slate-500 font-medium break-words">{job.company || job.seniority || t('common.unknownCompany')}</p>
                  </div>
                </div>

                <div className="mt-3 flex flex-wrap items-center gap-2">
                  {job.is_saved && (
                    <span className="rounded-lg bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">
                      {t('jobs.savedBadge')}
                    </span>
                  )}
                  <span className={`px-2.5 py-1 text-xs font-semibold rounded-lg ${statusBadgeMap[job.status]}`}>
                    {t(`statuses.${job.status}`)}
                  </span>
                  {job.applied_date && (
                    <span className="text-xs text-slate-500">
                      {t('jobs.appliedOn', { date: new Date(job.applied_date).toLocaleDateString(language) })}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={handleToggleSaved}
                  disabled={isTogglingSaved}
                  className={`inline-flex items-center justify-center gap-2 rounded-xl border px-4 py-2 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${
                    job.is_saved
                      ? 'border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100 dark:border-amber-900/50 dark:bg-amber-950/20 dark:text-amber-300'
                      : 'border-slate-200 text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800'
                  }`}
                >
                  {isTogglingSaved ? <Loader2 size={16} className="animate-spin" /> : <Bookmark size={16} className={job.is_saved ? 'fill-current' : ''} />}
                  {job.is_saved ? t('jobs.unsaveAction') : t('jobs.saveAction')}
                </button>
                <button
                  type="button"
                  onClick={handleDeleteJob}
                  disabled={isDeletingJob}
                  className="inline-flex items-center justify-center gap-2 rounded-xl border border-rose-200 px-4 py-2 text-sm font-semibold text-rose-600 transition-colors hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-rose-900/50 dark:text-rose-300 dark:hover:bg-rose-950/30"
                >
                  {isDeletingJob ? <Loader2 size={16} className="animate-spin" /> : <Trash2 size={16} />}
                  {t('jobs.deleteAction')}
                </button>
              </div>
            </div>
          </div>

          <div className="glass-card p-3 rounded-2xl">
            <div className="flex gap-2 overflow-x-auto">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`rounded-xl px-3 py-2 text-sm font-semibold whitespace-nowrap transition-colors ${
                    activeTab === tab.id
                      ? 'bg-brand-primary text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {error && <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/20 dark:text-rose-300">{error}</div>}

          <div className="glass-card p-4 lg:p-5 rounded-3xl min-h-[460px]">
            {activeTab === 'overview' && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div className="space-y-4">
                  <div className="rounded-2xl border border-slate-200/70 dark:border-slate-800 bg-white/70 dark:bg-slate-950/20 p-4">
                    <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-2">{t('jobDetails.executiveSummary')}</h2>
                    <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">{job.summary}</p>
                  </div>

                  <div className="rounded-2xl border border-slate-200/70 dark:border-slate-800 bg-white/70 dark:bg-slate-950/20 p-4">
                    <h3 className="font-bold text-sm uppercase tracking-wider text-slate-500 mb-3">{t('jobDetails.requiredSkills')}</h3>
                    <ul className="space-y-2 max-h-52 overflow-y-auto pr-1">
                      {job.required_skills?.map((skill, i) => (
                        <li key={i} className="flex items-start text-sm text-slate-700 dark:text-slate-300">
                          <CheckCircle2 size={15} className="text-brand-primary mr-2 mt-0.5 shrink-0" />
                          <span>{skill}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="rounded-2xl border border-slate-200/70 dark:border-slate-800 bg-white/70 dark:bg-slate-950/20 p-4">
                    <h3 className="font-bold text-sm uppercase tracking-wider text-slate-500 mb-3">{t('jobDetails.niceToHave')}</h3>
                    <ul className="space-y-2 max-h-52 overflow-y-auto pr-1">
                      {job.nice_to_have_skills?.map((skill, i) => (
                        <li key={i} className="flex items-start text-sm text-slate-600 dark:text-slate-400">
                          <ChevronRight size={15} className="text-slate-400 mr-2 mt-0.5 shrink-0" />
                          <span>{skill}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="rounded-2xl border border-slate-200/70 dark:border-slate-800 bg-white/70 dark:bg-slate-950/20 p-4">
                    <h3 className="font-bold text-sm uppercase tracking-wider text-slate-500 mb-3">{t('jobDetails.responsibilities')}</h3>
                    <ul className="space-y-2 max-h-52 overflow-y-auto pl-4 pr-1 list-disc">
                      {job.responsibilities?.map((res, i) => (
                        <li key={i} className="text-sm text-slate-700 dark:text-slate-300">{res}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'match' && (
              <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,360px)_minmax(0,1fr)] gap-4 lg:gap-5">
                <div className="space-y-4">
                  <div className="rounded-2xl border border-slate-200/70 dark:border-slate-800 p-4 bg-white/70 dark:bg-slate-950/20">
                    <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-3">{t('jobDetails.matchTitle')}</h3>
                    {cvs.length === 0 ? (
                      <p className="text-sm text-slate-500">{t('jobDetails.uploadCvFirst')}</p>
                    ) : (
                      <>
                        <select
                          value={selectedCvId}
                          onChange={(e) => setSelectedCvId(Number(e.target.value))}
                          className="input-field !py-2.5 text-sm"
                        >
                          <option value="" disabled>{t('common.selectCv')}</option>
                          {cvs.map((cv) => (
                            <option key={cv.id} value={cv.id}>{cv.name}</option>
                          ))}
                        </select>
                        <button
                          onClick={handleMatch}
                          disabled={isMatchLoading || !selectedCvId}
                          className="btn-primary mt-3 !py-2.5 text-sm flex items-center justify-center gap-2"
                        >
                          {isMatchLoading ? <><Loader2 size={16} className="animate-spin" /> {t('jobDetails.evaluating')}</> : <><Zap size={16} /> {t('jobDetails.runAlgorithm')}</>}
                        </button>
                      </>
                    )}
                  </div>

                  <div className="rounded-2xl border border-slate-200/70 dark:border-slate-800 p-4 bg-white/70 dark:bg-slate-950/20">
                    <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-3">{t('jobDetails.compareTitle')}</h3>
                    {cvs.length < 2 ? (
                      <p className="text-sm text-slate-500">{t('jobDetails.uploadTwoCvs')}</p>
                    ) : (
                      <div className="space-y-2">
                        <select value={compareCvIdA} onChange={(e) => setCompareCvIdA(Number(e.target.value))} className="input-field !py-2.5 text-sm">
                          <option value="" disabled>{t('common.selectCv')}</option>
                          {cvs.map((cv) => <option key={`a-${cv.id}`} value={cv.id}>{cv.name}</option>)}
                        </select>
                        <select value={compareCvIdB} onChange={(e) => setCompareCvIdB(Number(e.target.value))} className="input-field !py-2.5 text-sm">
                          <option value="" disabled>{t('common.selectCv')}</option>
                          {cvs.map((cv) => (
                            <option key={`b-${cv.id}`} value={cv.id} disabled={cv.id === Number(compareCvIdA)}>
                              {cv.name}
                            </option>
                          ))}
                        </select>
                        <button
                          onClick={handleCompare}
                          disabled={isCompareLoading || !compareCvIdA || !compareCvIdB || compareCvIdA === compareCvIdB}
                          className="btn-secondary !py-2.5 text-sm"
                        >
                          {isCompareLoading ? t('jobDetails.comparing') : t('jobDetails.compareCvs')}
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                <div className="space-y-4 min-w-0">
                  {comparisonResult && cvA && cvB && (
                    <div className="rounded-2xl border border-emerald-200/70 dark:border-emerald-900/50 p-5 lg:p-6 bg-emerald-50/70 dark:bg-emerald-950/20 space-y-4">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="space-y-1.5">
                          <p className="text-xs font-bold uppercase tracking-wider text-slate-500">{t('jobDetails.recommendedCv')}</p>
                          <p className="text-base lg:text-lg font-semibold text-emerald-700 dark:text-emerald-300 break-words leading-7">{comparisonResult.winner.label}</p>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleCopyText(
                            [
                              comparisonResult.overall_reason,
                              ...comparisonResult.comparative_strengths,
                              ...comparisonResult.comparative_weaknesses,
                              ...comparisonResult.job_alignment_breakdown,
                            ].join('\n'),
                            'comparison',
                          )}
                          className="btn-secondary w-full sm:w-auto px-4 !py-2 text-sm flex items-center justify-center gap-2"
                        >
                          {copiedSection === 'comparison' ? <><Check size={14} /> {t('common.copied')}</> : <><Copy size={14} /> {t('common.copyToClipboard')}</>}
                        </button>
                      </div>

                      {comparisonExplanationBlocks.length > 0 && (
                        <div className="rounded-xl border border-emerald-200/80 dark:border-emerald-900/50 bg-white/80 dark:bg-slate-950/30 px-4 py-3">
                          {comparisonExplanationBlocks.length > 1 ? (
                            <ul className="list-disc pl-5 space-y-2 text-sm text-slate-700 dark:text-slate-300 leading-7">
                              {comparisonExplanationBlocks.map((item, i) => (
                                <li key={i} className="break-words">{item}</li>
                              ))}
                            </ul>
                          ) : (
                            <p className="text-sm text-slate-700 dark:text-slate-300 leading-7 break-words">{comparisonExplanationBlocks[0]}</p>
                          )}
                        </div>
                      )}

                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 lg:gap-4">
                        <div className="rounded-xl border border-emerald-200/80 dark:border-emerald-900/50 bg-white/80 dark:bg-slate-950/30 px-4 py-3 min-w-0">
                          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">{t('jobDetails.comparativeStrengths')}</p>
                          {comparisonResult.comparative_strengths.length > 0 ? (
                            <ul className="list-disc pl-5 space-y-1.5 text-sm text-slate-700 dark:text-slate-300 leading-7">
                              {comparisonResult.comparative_strengths.map((item, i) => (
                                <li key={`cmp-strength-${i}`} className="break-words">{item}</li>
                              ))}
                            </ul>
                          ) : (
                            <p className="text-sm text-slate-500 dark:text-slate-400">--</p>
                          )}
                        </div>

                        <div className="rounded-xl border border-emerald-200/80 dark:border-emerald-900/50 bg-white/80 dark:bg-slate-950/30 px-4 py-3 min-w-0">
                          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">{t('jobDetails.comparativeWeaknesses')}</p>
                          {comparisonResult.comparative_weaknesses.length > 0 ? (
                            <ul className="list-disc pl-5 space-y-1.5 text-sm text-slate-700 dark:text-slate-300 leading-7">
                              {comparisonResult.comparative_weaknesses.map((item, i) => (
                                <li key={`cmp-weak-${i}`} className="break-words">{item}</li>
                              ))}
                            </ul>
                          ) : (
                            <p className="text-sm text-slate-500 dark:text-slate-400">--</p>
                          )}
                        </div>
                      </div>

                      <div className="rounded-xl border border-emerald-200/80 dark:border-emerald-900/50 bg-white/80 dark:bg-slate-950/30 px-4 py-3 min-w-0">
                        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">{t('jobDetails.jobAlignmentBreakdown')}</p>
                        {comparisonResult.job_alignment_breakdown.length > 0 ? (
                          <ul className="list-disc pl-5 space-y-1.5 text-sm text-slate-700 dark:text-slate-300 leading-7">
                            {comparisonResult.job_alignment_breakdown.map((item, i) => (
                              <li key={`cmp-align-${i}`} className="break-words">{item}</li>
                            ))}
                          </ul>
                        ) : (
                          <p className="text-sm text-slate-500 dark:text-slate-400">--</p>
                        )}
                      </div>
                    </div>
                  )}

                  {matchResult && (
                    <div className="rounded-2xl border border-brand-primary/20 p-5 lg:p-6 bg-brand-primary/5 space-y-5">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">{t('jobDetails.matchResults')}</h3>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className={`text-sm font-bold uppercase ${matchLevelTextClasses[matchResult.match_level]}`}>{matchResult.match_level}</span>
                          <button
                            type="button"
                            onClick={() => handleCopyText(
                              [
                                matchResult.why_this_cv,
                                ...matchResult.strengths,
                                ...displayMissingSkills,
                                ...matchSuggestions,
                                ...matchReorderSuggestions,
                              ].join('\n'),
                              'match',
                            )}
                            className="btn-secondary w-full sm:w-auto px-4 !py-2 text-sm flex items-center justify-center gap-2"
                          >
                            {copiedSection === 'match' ? <><Check size={14} /> {t('common.copied')}</> : <><Copy size={14} /> {t('common.copyToClipboard')}</>}
                          </button>
                        </div>
                      </div>

                      <div className="rounded-xl border border-slate-200/70 dark:border-slate-700 bg-white/70 dark:bg-slate-950/30 px-4 py-3">
                        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">{t('jobDetails.whyThisCv')}</p>
                        {matchWhyBlocks.length > 1 ? (
                          <ul className="list-disc pl-5 space-y-2 text-sm text-slate-700 dark:text-slate-300 leading-7">
                            {matchWhyBlocks.map((item, i) => (
                              <li key={i} className="break-words">{item}</li>
                            ))}
                          </ul>
                        ) : (
                          <p className="text-sm text-slate-700 dark:text-slate-300 leading-7 break-words">{matchWhyBlocks[0] ?? matchResult.why_this_cv}</p>
                        )}
                      </div>

                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 lg:gap-4">
                        <div className="rounded-xl border border-slate-200/70 dark:border-slate-700 bg-white/70 dark:bg-slate-950/30 px-4 py-3 min-w-0">
                          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">{t('jobDetails.strengths')}</p>
                          {matchResult.strengths?.length ? (
                            <ul className="list-disc pl-5 space-y-1.5 text-sm text-slate-700 dark:text-slate-300 leading-7">
                              {matchResult.strengths.map((item, i) => (
                                <li key={i} className="break-words">{item}</li>
                              ))}
                            </ul>
                          ) : (
                            <p className="text-sm text-slate-500 dark:text-slate-400">--</p>
                          )}
                        </div>

                        <div className="rounded-xl border border-slate-200/70 dark:border-slate-700 bg-white/70 dark:bg-slate-950/30 px-4 py-3 min-w-0">
                          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">{t('jobDetails.missingSkills')}</p>
                          {displayMissingSkills.length > 0 ? (
                            <ul className="list-disc pl-5 space-y-1.5 text-sm text-slate-700 dark:text-slate-300 leading-7">
                              {displayMissingSkills.map((item, i) => (
                                <li key={`${item}-${i}`} className="break-words">{item}</li>
                              ))}
                            </ul>
                          ) : (
                            <p className="text-sm text-slate-500 dark:text-slate-400">--</p>
                          )}
                        </div>
                      </div>

                      {(matchSuggestions.length > 0 || matchReorderSuggestions.length > 0) && (
                        <div className="rounded-xl border border-slate-200/70 dark:border-slate-700 bg-white/70 dark:bg-slate-950/30 px-4 py-3">
                          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">{t('jobDetails.improveCv')}</p>
                          <ul className="list-disc pl-5 space-y-1.5 text-sm text-slate-700 dark:text-slate-300 leading-7">
                            {[...matchSuggestions, ...matchReorderSuggestions].map((item, i) => (
                              <li key={i} className="break-words">{item}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeTab === 'improvements' && (
              <div className="space-y-4">
                {!matchResult ? (
                  <div className="rounded-2xl border border-dashed border-slate-300 dark:border-slate-700 p-8 text-center">
                    <p className="text-sm text-slate-500 mb-3">{t('jobDetails.noCvSelected')}</p>
                    <button onClick={() => setActiveTab('match')} className="btn-secondary w-auto px-5 !py-2">{t('jobDetails.matchTitle')}</button>
                  </div>
                ) : (
                  <>
                    <div className="rounded-2xl border border-slate-200/70 dark:border-slate-800 p-5 bg-white/70 dark:bg-slate-950/20">
                      <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-3">{t('jobDetails.strengths')}</h3>
                      <ul className="list-disc pl-5 space-y-2 text-sm text-slate-700 dark:text-slate-300 leading-7">
                        {matchResult.strengths?.map((item, i) => <li key={i} className="break-words">{item}</li>)}
                      </ul>
                    </div>

                    <div className="rounded-2xl border border-slate-200/70 dark:border-slate-800 p-5 bg-white/70 dark:bg-slate-950/20 space-y-4">
                      <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-3">{t('jobDetails.improveCv')}</h3>

                      {matchSuggestions.length > 0 && (
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">{t('jobDetails.improveCv')}</p>
                          <ul className="list-disc pl-5 space-y-2 text-sm text-slate-700 dark:text-slate-300 leading-7">
                            {matchSuggestions.map((item, i) => <li key={i} className="break-words">{item}</li>)}
                          </ul>
                        </div>
                      )}

                      {matchResult.missing_skills?.length > 0 && (
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">{t('jobDetails.missingSkills')}</p>
                          <ul className="list-disc pl-5 space-y-2 text-sm text-slate-700 dark:text-slate-300 leading-7">
                            {matchResult.missing_skills.map((item, i) => <li key={i} className="break-words">{item}</li>)}
                          </ul>
                        </div>
                      )}

                      {additionalMissingKeywords.length > 0 && (
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">{t('jobDetails.keywordsToAdd')}</p>
                          <div className="flex flex-wrap gap-2">
                            {additionalMissingKeywords.map((keyword) => (
                              <span key={keyword} className="rounded-full border border-amber-200/80 bg-white/80 px-3 py-1 text-xs font-semibold text-amber-900 dark:border-amber-800 dark:bg-slate-950/40 dark:text-amber-200 break-words">
                                {keyword}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {matchReorderSuggestions.length > 0 && (
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">{t('jobDetails.improveCv')}</p>
                          <ul className="list-disc pl-5 space-y-2 text-sm text-slate-700 dark:text-slate-300 leading-7">
                            {matchReorderSuggestions.map((item, i) => <li key={i} className="break-words">{item}</li>)}
                          </ul>
                        </div>
                      )}

                      {matchSuggestions.length === 0 && matchResult.missing_skills?.length === 0 && additionalMissingKeywords.length === 0 && matchReorderSuggestions.length === 0 && (
                        <p className="text-sm text-slate-500 dark:text-slate-400">--</p>
                      )}
                    </div>
                  </>
                )}
              </div>
            )}

            {activeTab === 'cover' && (
              <div className="space-y-4">
                <div className="rounded-2xl border border-slate-200/70 dark:border-slate-800 p-4 bg-white/70 dark:bg-slate-950/20 space-y-4">
                  <div>
                    <label className="block text-xs font-semibold mb-2 text-slate-500 uppercase">{t('jobDetails.targetCv')}</label>
                    <select
                      value={selectedCvId}
                      onChange={(e) => setSelectedCvId(Number(e.target.value))}
                      className="input-field !py-2.5 text-sm"
                      disabled={cvs.length === 0}
                    >
                      <option value="" disabled>{t('common.selectCv')}</option>
                      {cvs.map((cv) => (
                        <option key={cv.id} value={cv.id}>{cv.name}</option>
                      ))}
                    </select>
                  </div>

                  <button
                    onClick={handleGenerateCoverLetter}
                    disabled={isCoverLetterLoading || !selectedCvId}
                    className="btn-primary w-full sm:w-auto px-6 !py-2.5 text-sm"
                  >
                    {isCoverLetterLoading ? t('jobDetails.generating') : t('jobDetails.generateCoverLetter')}
                  </button>
                </div>

                {coverLetter && (
                  <div className="rounded-2xl border border-slate-200/70 dark:border-slate-800 bg-white/80 dark:bg-slate-950/40 p-4">
                    <pre className="whitespace-pre-wrap break-words text-sm leading-relaxed text-slate-700 dark:text-slate-300 font-sans max-h-[min(65vh,48rem)] overflow-y-auto pr-1">
                      {coverLetter}
                    </pre>
                    <button onClick={() => handleCopyText(coverLetter, 'cover')} className="btn-secondary mt-3 w-full sm:w-auto px-6 !py-2.5 text-sm flex items-center justify-center gap-2">
                      {copiedSection === 'cover' ? <><Check size={14} /> {t('common.copied')}</> : <><Copy size={14} /> {t('common.copyToClipboard')}</>}
                    </button>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'tracker' && (
              <div className="space-y-4 max-w-2xl">
                <div>
                  <label className="block text-xs font-semibold mb-2 text-slate-500 uppercase">{t('jobDetails.status')}</label>
                  <select
                    value={job.status}
                    onChange={(e) => handleStatusChange(e.target.value as JobApplicationStatus)}
                    disabled={isUpdatingStatus}
                    className="input-field"
                  >
                    {statusOptions.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold mb-2 text-slate-500 uppercase">{t('jobDetails.notes')}</label>
                  <textarea
                    value={notesDraft}
                    onChange={(e) => setNotesDraft(e.target.value)}
                    rows={7}
                    placeholder={t('jobDetails.notesPlaceholder')}
                    className="input-field resize-y"
                  />
                </div>

                <button onClick={handleSaveNotes} disabled={isSavingNotes} className="btn-secondary w-full sm:w-auto px-6">
                  {isSavingNotes ? t('jobDetails.savingNotes') : t('jobDetails.saveNotes')}
                </button>
              </div>
            )}
          </div>
        </section>

        <aside className="hidden 2xl:flex 2xl:flex-col gap-4 sticky top-[84px] h-fit">
          <div className="glass-card p-4 rounded-2xl">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">{t('jobDetails.insights')}</h3>
            <div className="space-y-3 text-sm">
              <div className="rounded-xl bg-slate-100 dark:bg-slate-800 px-3 py-2">
                <p className="text-xs uppercase tracking-wider text-slate-500 mb-1">{t('jobDetails.recommendedCv')}</p>
                <p className="font-semibold text-slate-800 dark:text-slate-200">{bestCvLabel}</p>
              </div>
              <div className="rounded-xl bg-slate-100 dark:bg-slate-800 px-3 py-2">
                <p className="text-xs uppercase tracking-wider text-slate-500 mb-1">{t('jobDetails.matchLevel')}</p>
                <p className={`font-semibold ${matchResult ? matchLevelTextClasses[matchResult.match_level] : 'text-slate-500'}`}>
                  {matchResult ? matchResult.match_level : '--'}
                </p>
              </div>
            </div>
          </div>

        </aside>
      </div>
    </div>
  );
}
