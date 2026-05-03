import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  FileText,
  Layers,
  Loader2,
  Sparkles,
  Target,
} from 'lucide-react';
import { apiService } from '../services/api';
import type {
  InterviewQuestion,
  InterviewSession,
  InterviewSessionCreate,
  InterviewSessionType,
  JobAnalysisResponse,
  StoredCV,
} from '../types';
import { useLanguage } from '../context/LanguageContext';
import { useToast } from '../context/ToastContext';

interface StarGuide {
  situation: string;
  task: string;
  action: string;
  result: string;
}

interface AnswerFeedback {
  score: number;
  explanation: string;
  suggestions: string[];
}

function formatDate(value: string, language: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleDateString(language, { month: 'short', day: 'numeric', year: 'numeric' });
}

function buildStarGuide(question: InterviewQuestion, job: JobAnalysisResponse | null, t: any): StarGuide {
  const coreSkills = job?.required_skills?.slice(0, 3) ?? [];
  const skillHint = coreSkills.length ? coreSkills.join(', ') : t('interviewPrep.coreSkillsFromRole');
  const roleHint = job?.title || job?.role_type || t('interviewPrep.theRole');
  const category = question.category ? question.category.toLowerCase() : '';

  // Base guide
  let situation = t('interviewPrep.starSituationDesc', { roleHint });
  let task = t('interviewPrep.starTaskDesc');
  let action = t('interviewPrep.starActionDesc', { skillHint });
  let result = t('interviewPrep.starResultDesc');

  // Personalize based on question category
  if (category.includes('leadership') || category.includes('conflict') || category.includes('team')) {
    action = t('interviewPrep.starLeadershipAction');
    result = t('interviewPrep.starLeadershipResult');
  } else if (category.includes('technical') || category.includes('problem') || category.includes('system')) {
    action = t('interviewPrep.starTechnicalAction');
    result = t('interviewPrep.starTechnicalResult');
  } else if (category.includes('failure') || category.includes('mistake') || category.includes('challenge')) {
    situation = t('interviewPrep.starFailureSituation', { roleHint });
    action = t('interviewPrep.starFailureAction');
    result = t('interviewPrep.starFailureResult');
  }

  return { situation, task, action, result };
}

function buildMarkdownExport(
  session: InterviewSession,
  job: JobAnalysisResponse | null,
  notesByQuestion: Record<number, string>,
  language: string,
  t: any,
): string {
  const header = `${t('interviewPrep.exportHeader')}\n\n## ${job?.title ?? t('interviewPrep.exportInterviewSession')}\n${job?.company ? `**${t('interviewPrep.exportCompany')}:** ${job.company}\n` : ''}`;
  const localizedType = session.session_type === 'mixed' ? t('interviewPrep.sessionTypeMixed') : 
                        session.session_type === 'behavioral' ? t('interviewPrep.sessionTypeBehavioral') : 
                        session.session_type === 'technical' ? t('interviewPrep.sessionTypeTechnical') : 
                        session.session_type;

  const localizedStatus = session.status === 'completed' ? t('statuses.completed') : 
                          session.status === 'in_progress' ? t('statuses.in_progress') : 
                          session.status;

  const meta = [
    `**${t('interviewPrep.exportSessionType')}:** ${localizedType}`,
    `**${t('interviewPrep.exportStatus')}:** ${localizedStatus}`,
    `**${t('interviewPrep.exportCreated')}:** ${formatDate(session.created_at, language)}`,
  ].join('\n');

  const questionBlocks = session.questions
    .map((question) => {
      const note = notesByQuestion[question.index]?.trim();
      const noteBlock = note ? `\n**${t('interviewPrep.exportDraftAnswer')}:**\n${note}` : '';
      return `### ${t('interviewPrep.exportQuestion')} ${question.index + 1}\n${question.question}\n\n**${t('interviewPrep.exportWhyItMatters')}:** ${question.rationale}${noteBlock}`;
    })
    .join('\n\n');

  return [header, meta, `## ${t('interviewPrep.exportQuestionsHeader')}`, questionBlocks].filter(Boolean).join('\n\n');
}

export function InterviewPrepPage() {
  const { aiLanguage, language, t } = useLanguage();
  const { showToast } = useToast();
  const { jobId } = useParams<{ jobId: string }>();

  const jobIdValue = useMemo(() => (jobId ? Number(jobId) : null), [jobId]);

  const [jobs, setJobs] = useState<JobAnalysisResponse[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<number | ''>(jobIdValue ?? '');
  const [job, setJob] = useState<JobAnalysisResponse | null>(null);
  const [cvs, setCvs] = useState<StoredCV[]>([]);
  const [sessions, setSessions] = useState<InterviewSession[]>([]);
  const [activeSession, setActiveSession] = useState<InterviewSession | null>(null);
  const [selectedCvId, setSelectedCvId] = useState<number | ''>('');
  const [sessionType, setSessionType] = useState<InterviewSessionType>('mixed');
  const [notesByQuestion, setNotesByQuestion] = useState<Record<number, string>>({});
  const [expandedQuestions, setExpandedQuestions] = useState<Record<number, boolean>>({});
  const [submittingQuestion, setSubmittingQuestion] = useState<Record<number, boolean>>({});
  const [feedbacks, setFeedbacks] = useState<Record<number, AnswerFeedback>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sortedSessions = useMemo(() => {
    return [...sessions].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }, [sessions]);

  const activeQuestions = useMemo(() => {
    const questions = activeSession?.questions ?? [];
    return [...questions].sort((a, b) => a.index - b.index);
  }, [activeSession]);

  useEffect(() => {
    let cancelled = false;

    async function loadBaseData() {
      setIsLoading(true);
      setError(null);

      try {
        const [cvData, jobsData] = await Promise.all([
          apiService.listCVs(),
          apiService.listJobs(),
        ]);

        if (cancelled) return;

        setCvs(cvData);
        setJobs(jobsData);
        setSelectedCvId((current) =>
          current && cvData.some((cv) => cv.id === current) ? current : (cvData[0]?.id ?? ''),
        );
      } catch (err) {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : t('interviewPrep.errorLoad');
        setError(message);
        showToast(message, 'error');
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    loadBaseData();
    return () => {
      cancelled = true;
    };
  }, [showToast, t]);

  useEffect(() => {
    if (!selectedJobId) {
      setJob(null);
      setSessions([]);
      setActiveSession(null);
      return;
    }

    let cancelled = false;

    async function loadJobSpecificData() {
      setIsLoading(true);
      try {
        const [jobData, sessionData] = await Promise.all([
          apiService.getJob(Number(selectedJobId)),
          apiService.listInterviewSessions(Number(selectedJobId)),
        ]);

        if (cancelled) return;

        const orderedSessions = [...sessionData].sort(
          (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
        );
        setJob(jobData);
        setSessions(orderedSessions);
        // Do not auto-open existing sessions when the user selects a job.
        // Let the user start a new session or explicitly load a previous one.
        setActiveSession(null);
      } catch (err) {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : t('interviewPrep.errorSession');
        setError(message);
        showToast(message, 'error');
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    loadJobSpecificData();
    return () => {
      cancelled = true;
    };
  }, [selectedJobId, showToast, t]);

  const handleStartSession = useCallback(async () => {
    if (!selectedJobId || !selectedCvId) return;

    setIsStarting(true);
    setError(null);

    try {
      const payload: InterviewSessionCreate = {
        cv_id: Number(selectedCvId),
        session_type: sessionType,
        language: aiLanguage,
      };
      const session = await apiService.startInterviewSession(Number(selectedJobId), payload);
      setActiveSession(session);
      setNotesByQuestion({});
      setExpandedQuestions({});
      setSessions((current) => {
        const next = [session, ...current.filter((item) => item.id !== session.id)];
        return next;
      });
      showToast(t('interviewPrep.sessionStarted'), 'success');
    } catch (err) {
      const message = err instanceof Error ? err.message : t('interviewPrep.errorStart');
      setError(message);
      showToast(message, 'error');
    } finally {
      setIsStarting(false);
    }
  }, [aiLanguage, selectedJobId, selectedCvId, sessionType, showToast, t]);

  const handleLoadSession = useCallback(async (sessionId: number) => {
    if (!selectedJobId) return;

    setError(null);

    try {
      const session = await apiService.getInterviewSession(Number(selectedJobId), sessionId);
      setActiveSession(session);
      setNotesByQuestion({});
      setExpandedQuestions({});
      setFeedbacks({});
      setSubmittingQuestion({});
    } catch (err) {
      const message = err instanceof Error ? err.message : t('interviewPrep.errorSession');
      setError(message);
      showToast(message, 'error');
    }
  }, [selectedJobId, showToast, t]);

  const handleSubmitAnswer = useCallback(async (index: number) => {
    const answer = notesByQuestion[index]?.trim();
    if (!answer) return;

    setSubmittingQuestion((prev) => ({ ...prev, [index]: true }));

    // Mock API delay to simulate answer evaluation
    await new Promise((resolve) => setTimeout(resolve, 1500));

    // Mock structured feedback response
    setFeedbacks((prev) => ({
      ...prev,
      [index]: {
        score: Math.floor(Math.random() * 20) + 75, // 75-95 score
        explanation: 'Good structure using the STAR method. You clearly defined the scenario and your specific actions. However, the impact could be quantified further.',
        suggestions: [
          'Add concrete metrics (e.g., "reduced latency by 20%").',
          'Explicitly tie your actions back to the core requirements of this role.',
        ],
      },
    }));

    setSubmittingQuestion((prev) => ({ ...prev, [index]: false }));
    showToast(t('interviewPrep.feedbackSuccess'), 'success');
  }, [notesByQuestion, showToast, t]);

  const handleCopyMarkdown = useCallback(async () => {
    if (!activeSession) {
      showToast(t('interviewPrep.exportEmpty'), 'warning');
      return;
    }

    try {
      const markdown = buildMarkdownExport(activeSession, job, notesByQuestion, language, t);
      await navigator.clipboard.writeText(markdown);
      showToast(t('interviewPrep.copiedMarkdown'), 'success');
    } catch (err) {
      const message = err instanceof Error ? err.message : t('interviewPrep.errorCopy');
      showToast(message, 'error');
    }
  }, [activeSession, job, language, notesByQuestion, showToast, t]);

  const handleDownloadMarkdown = useCallback(() => {
    if (!activeSession) {
      showToast(t('interviewPrep.exportEmpty'), 'warning');
      return;
    }

    try {
      const markdown = buildMarkdownExport(activeSession, job, notesByQuestion, language, t);
      const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `interview-prep-${activeSession.id}.md`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      const message = err instanceof Error ? err.message : t('interviewPrep.errorDownload');
      showToast(message, 'error');
    }
  }, [activeSession, job, language, notesByQuestion, showToast, t]);

  const handleToggleQuestion = useCallback((index: number) => {
    setExpandedQuestions((current) => ({
      ...current,
      [index]: !current[index],
    }));
  }, []);

  const handleNoteChange = useCallback((index: number, value: string) => {
    setNotesByQuestion((current) => ({
      ...current,
      [index]: value,
    }));
  }, []);

  const selectedCv = cvs.find((cv) => cv.id === Number(selectedCvId)) ?? null;

  const renderSetupForm = (isSidebar = false) => (
    <div className={isSidebar ? 'space-y-3' : 'mx-auto mt-8 max-w-md space-y-5 text-left'}>
      {!jobIdValue && (
        <div>
          <label
            htmlFor={`job-select-${isSidebar ? 'side' : 'main'}`}
            className="mb-1.5 block text-sm font-semibold text-slate-700 dark:text-slate-300"
          >
            {t('interviewPrep.selectJob', { defaultValue: 'Select Job' })}
          </label>
          <select
            id={`job-select-${isSidebar ? 'side' : 'main'}`}
            value={selectedJobId}
            onChange={(event) => setSelectedJobId(Number(event.target.value))}
            className="input-field w-full text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary"
            aria-describedby={jobs.length === 0 ? `job-help-${isSidebar ? 'side' : 'main'}` : undefined}
          >
            <option value="" disabled>
              {t('common.selectJob')}
            </option>
            {jobs.map((j) => (
              <option key={j.id} value={j.id}>
                {j.title} {j.company ? `${t('common.at', { defaultValue: 'at' })} ${j.company}` : ''}
              </option>
            ))}
          </select>
          {jobs.length === 0 && (
            <p id={`job-help-${isSidebar ? 'side' : 'main'}`} className="mt-1 text-xs text-rose-500">
              {t('interviewPrep.noJob', { defaultValue: 'No jobs available. Please analyze a job first.' })}
            </p>
          )}
        </div>
      )}
      <div>
        <label
          htmlFor={`cv-select-${isSidebar ? 'side' : 'main'}`}
          className="mb-1.5 block text-sm font-semibold text-slate-700 dark:text-slate-300"
        >
          {t('interviewPrep.selectCv')}
        </label>
        <select
          id={`cv-select-${isSidebar ? 'side' : 'main'}`}
          value={selectedCvId}
          onChange={(event) => {
            const v = event.target.value;
            const parsed = v === '' ? '' : Number(v);
            setSelectedCvId(Number.isNaN(parsed as number) ? '' : (parsed as number | ''));
          }}
          className="input-field w-full text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary"
          aria-describedby={cvs.length === 0 ? `cv-help-${isSidebar ? 'side' : 'main'}` : undefined}
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
        {cvs.length === 0 && (
          <p id={`cv-help-${isSidebar ? 'side' : 'main'}`} className="mt-1 text-xs text-rose-500">
            {t('interviewPrep.noCv')}
          </p>
        )}
      </div>

      <div>
        <label
          htmlFor={`type-select-${isSidebar ? 'side' : 'main'}`}
          className="mb-1.5 block text-sm font-semibold text-slate-700 dark:text-slate-300"
        >
          {t('interviewPrep.sessionType')}
        </label>
        <select
          id={`type-select-${isSidebar ? 'side' : 'main'}`}
          value={sessionType}
          onChange={(event) => setSessionType(event.target.value as InterviewSessionType)}
          className="input-field w-full text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary"
        >
          <option value="mixed">{t('interviewPrep.sessionTypeMixed')}</option>
          <option value="behavioral">{t('interviewPrep.sessionTypeBehavioral')}</option>
          <option value="technical">{t('interviewPrep.sessionTypeTechnical')}</option>
        </select>
      </div>

      <button
        type="button"
        onClick={handleStartSession}
        disabled={!selectedCvId || isStarting}
        className="btn-primary mt-4 flex w-full items-center justify-center gap-2 py-2.5 text-base focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-2"
        aria-live="polite"
      >
        {isStarting ? (
          <>
            <Loader2 size={18} className="animate-spin" />
            {t('interviewPrep.startingSession')}
          </>
        ) : (
          <>
            <Sparkles size={18} />
            {t('interviewPrep.startSession')}
          </>
        )}
      </button>
    </div>
  );

  if (isLoading) {
    return (
      <div className="animate-in fade-in space-y-4 duration-300">
        <div className="skeleton-block h-6 w-32 rounded-xl" />
        <div className="glass-card rounded-3xl p-5">
          <div className="space-y-4">
            <div className="skeleton-block h-10 w-1/2 rounded-xl" />
            <div className="space-y-2">
              <div className="skeleton-block h-4 w-full rounded-xl" />
              <div className="skeleton-block h-4 w-5/6 rounded-xl" />
              <div className="skeleton-block h-4 w-4/6 rounded-xl" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (jobIdValue && !job && !isLoading) {
    return (
      <div className="py-20 text-center">
        <h2 className="mb-4 text-2xl font-bold">{t('interviewPrep.emptyTitle')}</h2>
        <Link to="/jobs" className="text-brand-primary hover:underline">{t('jobDetails.returnToJobs')}</Link>
      </div>
    );
  }

  if (!jobIdValue && jobs.length === 0 && !isLoading) {
    return (
      <div className="py-20 text-center">
        <h2 className="mb-4 text-2xl font-bold">{t('interviewPrep.noJob', { defaultValue: 'No jobs available. Please analyze a job first.' })}</h2>
        <Link to="/jobs" className="text-brand-primary hover:underline">{t('jobDetails.returnToJobs', { defaultValue: 'Go to Jobs' })}</Link>
      </div>
    );
  }

  return (
    <div className="animate-in fade-in space-y-4 pb-8 duration-300">
      {jobIdValue ? (
        <Link to={`/jobs/${jobIdValue}`} className="inline-flex items-center text-sm font-semibold text-slate-500 transition-colors hover:text-brand-primary">
          <ArrowLeft size={16} className="mr-2" /> {t('interviewPrep.backToJob')}
        </Link>
      ) : null}

      <div className="glass-card rounded-3xl p-4 lg:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h1 className="text-2xl font-heading font-extrabold text-brand-text dark:text-white lg:text-3xl">
              {t('interviewPrep.title', { defaultValue: 'Interview Simulator' })}
            </h1>
            <p className="mt-2 text-sm text-slate-500">{t('interviewPrep.subtitle', { defaultValue: 'Practice your interview skills globally.' })}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {!jobIdValue && selectedJobId && (
              <button 
                onClick={() => setSelectedJobId('')} 
                className="inline-flex items-center rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-sm font-semibold text-slate-600 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
              >
                <ArrowLeft size={16} className="mr-2" /> 
                {t('interviewPrep.changeJob')}
              </button>
            )}
            {activeSession && (
              <>
                <button
                  type="button"
                  onClick={handleCopyMarkdown}
                  className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 transition-colors hover:bg-slate-100 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                >
                  <FileText size={16} />
                  {t('interviewPrep.copyMarkdown')}
                </button>
                <button
                  type="button"
                  onClick={handleDownloadMarkdown}
                  className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 transition-colors hover:bg-slate-100 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                >
                  <Layers size={16} />
                  {t('interviewPrep.downloadMarkdown')}
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
        <section className="min-w-0 space-y-4">
          {error && (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/20 dark:text-rose-300">
              {error}
            </div>
          )}

          {!activeSession ? (
            <div className="glass-card rounded-3xl p-8 text-center lg:p-12">
              <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-primary/10 text-brand-primary">
                <Sparkles size={28} />
              </div>
              <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                {t('interviewPrep.readyToPractice')}
              </h2>
              <p className="mx-auto mt-2 max-w-lg text-base text-slate-500">
                {t('interviewPrep.configureMockInterview')}
              </p>
              
              <div className="mt-8 border-t border-slate-100 pt-8 dark:border-slate-800/60">
                {renderSetupForm(false)}
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              <div className="glass-card flex items-center justify-between rounded-3xl p-4 lg:p-5">
                <div>
                  <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                    {t('interviewPrep.activeSession', { defaultValue: 'Active Session' })}
                  </h2>
                  <p className="text-sm text-slate-500 capitalize">
                    {activeSession.session_type === 'mixed' ? t('interviewPrep.sessionTypeMixed') : 
                     activeSession.session_type === 'behavioral' ? t('interviewPrep.sessionTypeBehavioral') : 
                     activeSession.session_type === 'technical' ? t('interviewPrep.sessionTypeTechnical') : 
                     activeSession.session_type}
                  </p>
                </div>
                <button
                  onClick={() => setActiveSession(null)}
                  className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-600 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                >
                  <ArrowLeft size={16} />
                  {t('interviewPrep.backToSetup', { defaultValue: 'Back to Setup' })}
                </button>
              </div>

              {activeQuestions.map((question) => {
                const guide = buildStarGuide(question, job, t);
                const isExpanded = Boolean(expandedQuestions[question.index]);
                const noteValue = notesByQuestion[question.index] ?? '';
                const isSubmitting = submittingQuestion[question.index];
                const feedback = feedbacks[question.index];
                
                const textareaId = `answer-${question.index}`;
                const starId = `star-guide-${question.index}`;

                return (
                  <article key={question.index} className="glass-card overflow-hidden rounded-3xl border border-slate-200/60 transition-all dark:border-slate-800/60">
                    <div className="p-5 lg:p-6">
                      <div className="flex flex-col gap-4">
                        <div>
                          <span className="mb-3 inline-block rounded-full bg-slate-100 px-3 py-1 text-xs font-bold uppercase tracking-widest text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                            {t('interviewPrep.questionTitle', { count: question.index + 1 })}
                          </span>
                          <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100 lg:text-xl">
                            {question.question}
                          </h3>
                          <div className="mt-3 rounded-xl bg-brand-primary/5 p-4 text-sm text-brand-primary/90 dark:bg-brand-primary/10 dark:text-brand-primary/80">
                            <span className="font-semibold">{t('interviewPrep.rationaleLabel')}:</span> {question.rationale}
                          </div>
                        </div>
                      </div>

                      <div className="mt-6 border-t border-slate-100 pt-6 dark:border-slate-800/60">
                        <div className="mb-4 flex items-center justify-between">
                          <label htmlFor={textareaId} className="text-sm font-bold text-slate-900 dark:text-slate-100">
                            {t('interviewPrep.yourAnswer')}
                          </label>
                          <button
                            type="button"
                            onClick={() => handleToggleQuestion(question.index)}
                            aria-expanded={isExpanded}
                            aria-controls={starId}
                            className="inline-flex items-center gap-1.5 rounded text-xs font-semibold text-brand-primary transition-colors hover:text-brand-primary/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary"
                          >
                            <Target size={14} />
                            {isExpanded ? t('interviewPrep.hideStarGuide') : t('interviewPrep.starGuide')}
                          </button>
                        </div>

                        {isExpanded && (
                          <div id={starId} className="mb-5 grid gap-4 rounded-2xl bg-slate-50 p-4 md:grid-cols-2 dark:bg-slate-900/50">
                            <div>
                              <strong className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                                {t('interviewPrep.starSituation')}
                              </strong>
                              <p className="mt-1 text-sm text-slate-700 dark:text-slate-300">{guide.situation}</p>
                            </div>
                            <div>
                              <strong className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                                {t('interviewPrep.starTask')}
                              </strong>
                              <p className="mt-1 text-sm text-slate-700 dark:text-slate-300">{guide.task}</p>
                            </div>
                            <div>
                              <strong className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                                {t('interviewPrep.starAction')}
                              </strong>
                              <p className="mt-1 text-sm text-slate-700 dark:text-slate-300">{guide.action}</p>
                            </div>
                            <div>
                              <strong className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                                {t('interviewPrep.starResult')}
                              </strong>
                              <p className="mt-1 text-sm text-slate-700 dark:text-slate-300">{guide.result}</p>
                            </div>
                          </div>
                        )}

                        <textarea
                          id={textareaId}
                          rows={4}
                          value={noteValue}
                          onChange={(event) => handleNoteChange(question.index, event.target.value)}
                          disabled={isSubmitting}
                          placeholder={t('interviewPrep.typeYourResponse')}
                          className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 shadow-sm transition-all placeholder:text-slate-400 focus-visible:border-brand-primary focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-primary/10 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200"
                        />

                        <div className="mt-4 flex justify-end">
                          <button
                            type="button"
                            onClick={() => handleSubmitAnswer(question.index)}
                            disabled={!noteValue.trim() || isSubmitting}
                            className="btn-primary inline-flex items-center gap-2 px-6 py-2.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-2"
                          >
                            {isSubmitting ? (
                              <>
                                <Loader2 size={16} className="animate-spin" />
                                {t('interviewPrep.evaluating')}
                              </>
                            ) : (
                              <>{feedback ? t('interviewPrep.updateAnswer') : t('interviewPrep.submitAnswer')}</>
                            )}
                          </button>
                        </div>

                        {feedback && (
                          <div
                            className="mt-6 animate-in fade-in slide-in-from-top-2 rounded-2xl border border-emerald-200/60 bg-emerald-50/80 p-5 dark:border-emerald-900/40 dark:bg-emerald-950/20"
                            aria-live="polite"
                            role="status"
                          >
                            <h4 className="flex items-center gap-2 text-sm font-bold text-emerald-800 dark:text-emerald-400">
                              <Sparkles size={16} />
                              {t('interviewPrep.aiEvaluation', { score: feedback.score })}
                            </h4>
                            <p className="mt-2 text-sm text-emerald-700 dark:text-emerald-300">
                              {feedback.explanation}
                            </p>
                            <div className="mt-4 border-t border-emerald-100 pt-3 dark:border-emerald-900/40">
                              <strong className="text-[11px] font-bold uppercase tracking-wider text-emerald-800/70 dark:text-emerald-400/70">
                                {t('interviewPrep.suggestionsToImprove')}
                              </strong>
                              <ul className="mt-2 list-inside list-disc space-y-1.5 text-sm text-emerald-700 dark:text-emerald-300">
                                {feedback.suggestions.map((s, i) => (
                                  <li key={i}>{s}</li>
                                ))}
                              </ul>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>

        <aside className="order-2 flex flex-col gap-4 xl:sticky xl:top-[84px] xl:order-none xl:h-fit">


          <div className="glass-card rounded-2xl p-4">
            <h3 className="mb-3 text-xs font-bold uppercase tracking-wider text-slate-500">{t('interviewPrep.activeSessionTitle')}</h3>
            {activeSession ? (
              <div className="space-y-3 text-sm">
                <div className="rounded-xl bg-slate-100 px-3 py-2 dark:bg-slate-800">
                  <p className="text-xs uppercase tracking-wider text-slate-500">{t('interviewPrep.sessionType')}</p>
                  <p className="font-semibold text-slate-900 dark:text-slate-100 capitalize">
                    {activeSession.session_type === 'mixed' ? t('interviewPrep.sessionTypeMixed') : 
                     activeSession.session_type === 'behavioral' ? t('interviewPrep.sessionTypeBehavioral') : 
                     activeSession.session_type === 'technical' ? t('interviewPrep.sessionTypeTechnical') : 
                     activeSession.session_type}
                  </p>
                </div>
                <div className="rounded-xl bg-slate-100 px-3 py-2 dark:bg-slate-800">
                  <p className="text-xs uppercase tracking-wider text-slate-500">{t('interviewPrep.sessionQuestions')}</p>
                  <p className="font-semibold text-slate-900 dark:text-slate-100">{activeSession.questions.length}</p>
                </div>
                <div className="rounded-xl bg-slate-100 px-3 py-2 dark:bg-slate-800">
                  <p className="text-xs uppercase tracking-wider text-slate-500">{t('interviewPrep.sessionStatus')}</p>
                  <p className="font-semibold text-slate-900 dark:text-slate-100 capitalize">
                    {activeSession.status === 'completed' ? t('statuses.completed') : 
                     activeSession.status === 'in_progress' ? t('statuses.in_progress') : 
                     activeSession.status}
                  </p>
                </div>
              </div>
            ) : (
              <p className="text-sm text-slate-500">{t('interviewPrep.noSessions')}</p>
            )}
          </div>

          <div className="glass-card rounded-2xl p-4">
            <h3 className="mb-3 text-xs font-bold uppercase tracking-wider text-slate-500">{t('interviewPrep.recentSessions')}</h3>
            {sortedSessions.length === 0 ? (
              <p className="text-sm text-slate-500">{t('interviewPrep.noSessions')}</p>
            ) : (
              <div className="space-y-3">
                {sortedSessions.slice(0, 4).map((sessionItem) => (
                  <button
                    key={sessionItem.id}
                    type="button"
                    onClick={() => handleLoadSession(sessionItem.id)}
                    className="flex w-full flex-col items-start gap-1 rounded-xl border border-slate-200 px-3 py-2 text-left text-sm text-slate-700 transition hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
                  >
                    <div className="flex w-full items-center justify-between">
                      <span className="font-semibold">
                        {sessionItem.session_type === 'mixed' ? t('interviewPrep.sessionTypeMixed') : 
                         sessionItem.session_type === 'behavioral' ? t('interviewPrep.sessionTypeBehavioral') : 
                         sessionItem.session_type === 'technical' ? t('interviewPrep.sessionTypeTechnical') : 
                         sessionItem.session_type}
                      </span>
                      <span className="text-xs text-slate-500">{formatDate(sessionItem.created_at, language)}</span>
                    </div>
                    <span className="text-xs text-slate-500">
                      {sessionItem.status === 'completed' ? t('statuses.completed', { defaultValue: 'Completed' }) : 
                       sessionItem.status === 'in_progress' ? t('statuses.in_progress', { defaultValue: 'In Progress' }) : 
                       sessionItem.status}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="glass-card rounded-2xl p-4">
            <h3 className="mb-3 text-xs font-bold uppercase tracking-wider text-slate-500">{t('interviewPrep.jobSnapshot')}</h3>
            <div className="space-y-3 text-sm">
              <div className="flex items-center gap-2 text-slate-700 dark:text-slate-200">
                <Target size={16} className="text-brand-primary" />
                <span>{job?.title || job?.role_type || ''}</span>
              </div>
              {selectedCv ? (
                <div className="flex items-center gap-2 text-slate-700 dark:text-slate-200">
                  <FileText size={16} className="text-brand-primary" />
                  <span>{selectedCv.name}</span>
                </div>
              ) : null}
              <div className="rounded-xl bg-slate-100 px-3 py-2 text-xs text-slate-500 dark:bg-slate-800">
                {job?.required_skills?.slice(0, 4).map((skill) => (
                  <span key={skill} className="mr-2 inline-flex items-center rounded-full bg-white px-2 py-0.5 text-[11px] text-slate-600 dark:bg-slate-900 dark:text-slate-300">
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
