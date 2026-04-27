import { Suspense, lazy, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Bookmark, Briefcase, CheckCircle2, ChevronRight, Loader2, SearchCheck, Trash2, Zap } from 'lucide-react';
import { apiService } from '../services/api';
import type {
  CVComparisonResult,
  CVJobMatch,
  JobAnalysisResponse,
  JobApplicationStatus,
  StoredCV,
} from '../types';
import { useLanguage } from '../context/LanguageContext';
import { useToast } from '../context/ToastContext';
import { SkeletonLoader } from '../components/SkeletonLoader';
import { RouteFallback } from '../components/RouteFallback';

const JobDetailsMatchPanel = lazy(() =>
  import('./job-details/JobDetailsMatchPanel').then((module) => ({ default: module.JobDetailsMatchPanel })),
);
const JobDetailsImprovementsPanel = lazy(() =>
  import('./job-details/JobDetailsImprovementsPanel').then((module) => ({ default: module.JobDetailsImprovementsPanel })),
);
const JobDetailsComparisonPanel = lazy(() =>
  import('./job-details/JobDetailsComparisonPanel').then((module) => ({ default: module.JobDetailsComparisonPanel })),
);
const JobDetailsCoverPanel = lazy(() =>
  import('./job-details/JobDetailsCoverPanel').then((module) => ({ default: module.JobDetailsCoverPanel })),
);
const JobDetailsTrackerPanel = lazy(() =>
  import('./job-details/JobDetailsTrackerPanel').then((module) => ({ default: module.JobDetailsTrackerPanel })),
);

type DetailsTab = 'overview' | 'match' | 'improvements' | 'comparison' | 'cover' | 'tracker';

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

function JobDetailsTabFallback() {
  return <RouteFallback variant="panel" />;
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
  const matchNextSteps = dedupeItems(matchResult?.result?.next_steps ?? []);
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
      showToast('Job status updated.', 'success');
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
      showToast('Notes saved.', 'success');
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
      showToast('Cover letter generated.', 'success');
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
      showToast('Job deleted.', 'success');
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
      { id: 'comparison', label: t('jobDetails.compareTitle') },
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
      <div className="py-20 text-center">
        <h2 className="mb-4 text-2xl font-bold">{t('jobDetails.notFound')}</h2>
        <Link to="/jobs" className="text-brand-primary hover:underline">{t('jobDetails.returnToJobs')}</Link>
      </div>
    );
  }

  return (
    <div className="animate-in fade-in space-y-4 pb-8 duration-300">
      <Link to="/jobs" className="inline-flex items-center text-sm font-semibold text-slate-500 transition-colors hover:text-brand-primary">
        <ArrowLeft size={16} className="mr-2" /> {t('jobDetails.backToAnalysis')}
      </Link>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
        <section className="min-w-0 space-y-4">
          <div className="glass-card rounded-3xl p-4 lg:p-5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand-primary/10 text-brand-primary">
                    <Briefcase size={22} />
                  </div>
                  <div className="min-w-0">
                    <h1 className="break-words text-2xl font-heading font-extrabold text-brand-text dark:text-white lg:text-3xl">
                      {job.title || job.role_type || t('common.untitledRole')}
                    </h1>
                    <p className="break-words font-medium text-slate-500">
                      {job.company || job.seniority || t('common.unknownCompany')}
                    </p>
                  </div>
                </div>

                <div className="mt-3 flex flex-wrap items-center gap-2">
                  {job.is_saved && (
                    <span className="rounded-lg bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">
                      {t('jobs.savedBadge')}
                    </span>
                  )}
                  <span className={`rounded-lg px-2.5 py-1 text-xs font-semibold ${statusBadgeMap[job.status]}`}>
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
                  {isTogglingSaved ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <Bookmark size={16} className={job.is_saved ? 'fill-current' : ''} />
                  )}
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

          <div className="glass-card rounded-2xl p-3">
            <div className="flex gap-2 overflow-x-auto">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`whitespace-nowrap rounded-xl px-3 py-2 text-sm font-semibold transition-colors ${
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

          {error && (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/20 dark:text-rose-300">
              {error}
            </div>
          )}

          <div className="glass-card min-h-[460px] rounded-3xl p-4 lg:p-5">
            {activeTab === 'overview' && (
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <div className="space-y-4">
                  <div className="rounded-2xl border border-slate-200/70 bg-white/70 p-4 dark:border-slate-800 dark:bg-slate-950/20">
                    <h2 className="mb-2 text-sm font-bold uppercase tracking-wider text-slate-500">{t('jobDetails.executiveSummary')}</h2>
                    <p className="text-sm leading-relaxed text-slate-700 dark:text-slate-300">{job.summary}</p>
                  </div>

                  <div className="rounded-2xl border border-slate-200/70 bg-white/70 p-4 dark:border-slate-800 dark:bg-slate-950/20">
                    <h3 className="mb-3 text-sm font-bold uppercase tracking-wider text-slate-500">{t('jobDetails.requiredSkills')}</h3>
                    <ul className="max-h-52 space-y-2 overflow-y-auto pr-1">
                      {job.required_skills?.map((skill, i) => (
                        <li key={i} className="flex items-start text-sm text-slate-700 dark:text-slate-300">
                          <CheckCircle2 size={15} className="mr-2 mt-0.5 shrink-0 text-brand-primary" />
                          <span>{skill}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="rounded-2xl border border-slate-200/70 bg-white/70 p-4 dark:border-slate-800 dark:bg-slate-950/20">
                    <h3 className="mb-3 text-sm font-bold uppercase tracking-wider text-slate-500">{t('jobDetails.niceToHave')}</h3>
                    <ul className="max-h-52 space-y-2 overflow-y-auto pr-1">
                      {job.nice_to_have_skills?.map((skill, i) => (
                        <li key={i} className="flex items-start text-sm text-slate-600 dark:text-slate-400">
                          <ChevronRight size={15} className="mr-2 mt-0.5 shrink-0 text-slate-400" />
                          <span>{skill}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="rounded-2xl border border-slate-200/70 bg-white/70 p-4 dark:border-slate-800 dark:bg-slate-950/20">
                    <h3 className="mb-3 text-sm font-bold uppercase tracking-wider text-slate-500">{t('jobDetails.responsibilities')}</h3>
                    <ul className="max-h-52 list-disc space-y-2 overflow-y-auto pl-4 pr-1">
                      {job.responsibilities?.map((responsibility, i) => (
                        <li key={i} className="text-sm text-slate-700 dark:text-slate-300">{responsibility}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'match' && (
              <Suspense fallback={<JobDetailsTabFallback />}>
                <JobDetailsMatchPanel
                  cvs={cvs}
                  selectedCvId={selectedCvId}
                  setSelectedCvId={(value) => setSelectedCvId(value)}
                  isMatchLoading={isMatchLoading}
                  handleMatch={handleMatch}
                  matchResult={matchResult}
                  matchWhyBlocks={matchWhyBlocks}
                  copiedSection={copiedSection}
                  handleCopyText={handleCopyText}
                  matchLevelTextClasses={matchLevelTextClasses}
                  displayMissingSkills={displayMissingSkills}
                  matchSuggestions={matchSuggestions}
                  matchReorderSuggestions={matchReorderSuggestions}
                  t={t}
                />
              </Suspense>
            )}

            {activeTab === 'comparison' && (
              <Suspense fallback={<JobDetailsTabFallback />}>
                <JobDetailsComparisonPanel
                  cvs={cvs}
                  compareCvIdA={compareCvIdA}
                  compareCvIdB={compareCvIdB}
                  setCompareCvIdA={(value) => setCompareCvIdA(value)}
                  setCompareCvIdB={(value) => setCompareCvIdB(value)}
                  isCompareLoading={isCompareLoading}
                  handleCompare={handleCompare}
                  comparisonResult={comparisonResult}
                  cvA={cvA}
                  cvB={cvB}
                  comparisonExplanationBlocks={comparisonExplanationBlocks}
                  copiedSection={copiedSection}
                  handleCopyText={handleCopyText}
                  t={t}
                />
              </Suspense>
            )}

            {activeTab === 'improvements' && (
              <Suspense fallback={<JobDetailsTabFallback />}>
                <JobDetailsImprovementsPanel
                  matchResult={matchResult}
                  matchSuggestions={matchSuggestions}
                  matchNextSteps={matchNextSteps}
                  additionalMissingKeywords={additionalMissingKeywords}
                  matchReorderSuggestions={matchReorderSuggestions}
                  setActiveTab={setActiveTab}
                  t={t}
                />
              </Suspense>
            )}

            {activeTab === 'cover' && (
              <Suspense fallback={<JobDetailsTabFallback />}>
                <JobDetailsCoverPanel
                  cvs={cvs}
                  selectedCvId={selectedCvId}
                  setSelectedCvId={(value) => setSelectedCvId(value)}
                  isCoverLetterLoading={isCoverLetterLoading}
                  handleGenerateCoverLetter={handleGenerateCoverLetter}
                  coverLetter={coverLetter}
                  copiedSection={copiedSection}
                  handleCopyText={handleCopyText}
                  t={t}
                />
              </Suspense>
            )}

            {activeTab === 'tracker' && (
              <Suspense fallback={<JobDetailsTabFallback />}>
                <JobDetailsTrackerPanel
                  status={job.status}
                  statusOptions={statusOptions}
                  handleStatusChange={handleStatusChange}
                  isUpdatingStatus={isUpdatingStatus}
                  notesDraft={notesDraft}
                  setNotesDraft={setNotesDraft}
                  handleSaveNotes={handleSaveNotes}
                  isSavingNotes={isSavingNotes}
                  t={t}
                />
              </Suspense>
            )}
          </div>
        </section>

        <aside className="sticky top-[84px] hidden h-fit gap-4 xl:flex xl:flex-col">
          <div className="glass-card rounded-2xl p-4">
            <h3 className="mb-3 text-xs font-bold uppercase tracking-wider text-slate-500">Insights</h3>
            <div className="space-y-3 text-sm">
              <div className="rounded-xl bg-slate-100 px-3 py-2 dark:bg-slate-800">
                <p className="mb-1 text-xs uppercase tracking-wider text-slate-500">{t('jobDetails.recommendedCv')}</p>
                <p className="font-semibold text-slate-800 dark:text-slate-200">{bestCvLabel}</p>
              </div>
              <div className="rounded-xl bg-slate-100 px-3 py-2 dark:bg-slate-800">
                <p className="mb-1 text-xs uppercase tracking-wider text-slate-500">{t('jobDetails.matchLevel')}</p>
                <p className={`font-semibold ${matchResult ? matchLevelTextClasses[matchResult.match_level] : 'text-slate-500'}`}>
                  {matchResult ? matchResult.match_level : '--'}
                </p>
              </div>
            </div>
          </div>

          <div className="improvement-panel-sidebar-card">
            <div className="mb-4 flex items-start gap-3">
              <div className="improvement-panel-icon improvement-panel-icon-sky">
                <SearchCheck size={18} />
              </div>
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500 dark:text-slate-400">
                  {t('jobDetails.matchTitle')}
                </p>
                <h3 className="mt-1 text-base font-semibold text-slate-900 dark:text-slate-100">
                  {t('jobDetails.matchWorkspaceTitle')}
                </h3>
              </div>
            </div>

            {cvs.length === 0 ? (
              <p className="text-sm text-slate-500">{t('jobDetails.uploadCvFirst')}</p>
            ) : (
              <div className="flex flex-col gap-4">
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-700 dark:text-slate-300">
                    {t('common.selectCv')}
                  </label>
                  <select
                    value={selectedCvId}
                    onChange={(e) => setSelectedCvId(Number(e.target.value))}
                    className="input-field w-full !py-2.5 text-sm"
                  >
                    <option value="" disabled>
                      {t('common.selectCv')}
                    </option>
                    {cvs.map((cv) => (
                      <option key={cv.id} value={cv.id}>
                        {cv.name}
                      </option>
                    ))}
                  </select>
                </div>
                <button
                  onClick={handleMatch}
                  disabled={isMatchLoading || !selectedCvId}
                  className="btn-primary flex w-full items-center justify-center gap-2 !py-2.5 text-sm"
                >
                  {isMatchLoading ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />
                      {t('jobDetails.evaluating')}
                    </>
                  ) : (
                    <>
                      <Zap size={16} />
                      {t('jobDetails.runAlgorithm')}
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
