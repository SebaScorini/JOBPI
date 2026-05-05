import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AtSign,
  Briefcase,
  Check,
  Clipboard,
  Copy,
  FileText,
  Loader2,
  Mail,
  MessageSquare,
  Sparkles,
  UserRound,
} from 'lucide-react';
import { apiService } from '../services/api';
import { useLanguage } from '../context/LanguageContext';
import { useToast } from '../context/ToastContext';
import { Card } from '../components/ui/Card';
import { SkeletonLoader } from '../components/SkeletonLoader';
import type { ColdOutreach, JobAnalysisResponse, LinkedInProfile, StoredCV } from '../types';

type LinkedInTab = 'profile' | 'outreach';
type CopiedTarget = 'headline' | 'about' | 'outreach' | null;

function formatJobLabel(job: JobAnalysisResponse): string {
  return job.company ? `${job.title} at ${job.company}` : job.title;
}

function formatDate(value: string, language: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleDateString(language, { month: 'short', day: 'numeric', year: 'numeric' });
}

interface CopyButtonProps {
  label: string;
  copied: boolean;
  onCopy: () => void;
}

function CopyButton({ label, copied, onCopy }: CopyButtonProps) {
  return (
    <button
      type="button"
      onClick={onCopy}
      className="inline-flex h-9 items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-600 transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
    >
      {copied ? <Check size={15} /> : <Copy size={15} />}
      {label}
    </button>
  );
}

interface ResultSectionProps {
  title: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}

function ResultSection({ title, children, action }: ResultSectionProps) {
  return (
    <div className="rounded-2xl border border-slate-200/70 bg-white/75 p-4 dark:border-slate-800 dark:bg-slate-950/30">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">{title}</h3>
        {action}
      </div>
      {children}
    </div>
  );
}

export function LinkedInOptimizerPage() {
  const { aiLanguage, language, t } = useLanguage();
  const { showToast } = useToast();

  const [activeTab, setActiveTab] = useState<LinkedInTab>('profile');
  const [cvs, setCvs] = useState<StoredCV[]>([]);
  const [jobs, setJobs] = useState<JobAnalysisResponse[]>([]);
  const [selectedCvId, setSelectedCvId] = useState<number | ''>('');
  const [profileJobIds, setProfileJobIds] = useState<number[]>([]);
  const [selectedOutreachJobId, setSelectedOutreachJobId] = useState<number | ''>('');
  const [hiringManagerName, setHiringManagerName] = useState('');
  const [profileResult, setProfileResult] = useState<LinkedInProfile | null>(null);
  const [outreachResult, setOutreachResult] = useState<ColdOutreach | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isProfileGenerating, setIsProfileGenerating] = useState(false);
  const [isOutreachGenerating, setIsOutreachGenerating] = useState(false);
  const [copiedTarget, setCopiedTarget] = useState<CopiedTarget>(null);
  const [error, setError] = useState<string | null>(null);

  const selectedCv = cvs.find((cv) => cv.id === Number(selectedCvId)) ?? null;
  const selectedOutreachJob = jobs.find((job) => job.id === Number(selectedOutreachJobId)) ?? null;
  const selectedProfileJobs = jobs.filter((job) => profileJobIds.includes(job.id)).slice(0, 5);

  const tabs = useMemo(
    () => [
      { id: 'profile' as const, label: t('linkedin.profileTab'), icon: UserRound },
      { id: 'outreach' as const, label: t('linkedin.outreachTab'), icon: MessageSquare },
    ],
    [t],
  );

  useEffect(() => {
    let cancelled = false;

    async function loadWorkspaceData() {
      setIsLoading(true);
      setError(null);

      try {
        const [cvData, jobData] = await Promise.all([apiService.listCVs(), apiService.listJobs()]);
        if (cancelled) {
          return;
        }
        setCvs(cvData);
        setJobs(jobData);
        setSelectedCvId((current) => (current && cvData.some((cv) => cv.id === current) ? current : (cvData[0]?.id ?? '')));
        setSelectedOutreachJobId((current) =>
          current && jobData.some((job) => job.id === current) ? current : (jobData[0]?.id ?? ''),
        );

        setProfileJobIds((current) => {
          const valid = current.filter((id) => jobData.some((job) => job.id === id)).slice(0, 5);
          return valid.length ? valid : jobData.slice(0, 3).map((job) => job.id);
        });
      } catch (err) {
        if (cancelled) {
          return;
        }
        const message = err instanceof Error ? err.message : t('linkedin.failedLoad');
        setError(message);
        showToast(message, 'error');
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    loadWorkspaceData();
    return () => {
      cancelled = true;
    };
  }, [showToast, t]);

  useEffect(() => {
    if (!selectedCvId) {
      setProfileResult(null);
      return;
    }

    let cancelled = false;

    async function loadCachedProfile() {
      try {
        const cached = await apiService.getCachedLinkedInProfile(Number(selectedCvId), profileJobIds, aiLanguage);
        if (!cancelled) {
          setProfileResult(cached);
        }
      } catch {
        if (!cancelled) {
          setProfileResult(null);
        }
      }
    }

    loadCachedProfile();
    return () => {
      cancelled = true;
    };
  }, [aiLanguage, profileJobIds, selectedCvId]);

  useEffect(() => {
    if (!selectedCvId || !selectedOutreachJobId) {
      setOutreachResult(null);
      return;
    }

    let cancelled = false;

    async function loadCachedOutreach() {
      try {
        const cached = await apiService.getCachedColdOutreach(
          Number(selectedOutreachJobId),
          Number(selectedCvId),
          hiringManagerName,
          aiLanguage,
        );
        if (!cancelled) {
          setOutreachResult(cached);
        }
      } catch {
        if (!cancelled) {
          setOutreachResult(null);
        }
      }
    }

    loadCachedOutreach();
    return () => {
      cancelled = true;
    };
  }, [aiLanguage, hiringManagerName, selectedCvId, selectedOutreachJobId]);



  const handleCopy = useCallback(async (target: CopiedTarget, text: string) => {
    if (!text.trim()) {
      return;
    }

    try {
      await navigator.clipboard.writeText(text);
      setCopiedTarget(target);
      showToast(t('linkedin.copied'), 'success');
      window.setTimeout(() => setCopiedTarget(null), 1800);
    } catch (err) {
      const message = err instanceof Error ? err.message : t('linkedin.failedCopy');
      showToast(message, 'error');
    }
  }, [showToast, t]);

  const handleProfileJobToggle = useCallback((jobId: number) => {
    setProfileJobIds((current) => {
      if (current.includes(jobId)) {
        return current.filter((id) => id !== jobId);
      }
      return [...current, jobId].slice(0, 5);
    });
  }, []);

  const handleGenerateProfile = useCallback(async () => {
    if (!selectedCvId) {
      showToast(t('linkedin.noCvs'), 'warning');
      return;
    }

    setIsProfileGenerating(true);
    setError(null);
    try {
      const result = await apiService.generateLinkedInProfile(Number(selectedCvId), profileJobIds, aiLanguage);
      setProfileResult(result);
    } catch (err) {
      const message = err instanceof Error ? err.message : t('linkedin.failedProfile');
      setError(message);
      showToast(message, 'error');
    } finally {
      setIsProfileGenerating(false);
    }
  }, [aiLanguage, profileJobIds, selectedCvId, showToast, t]);

  const handleGenerateOutreach = useCallback(async () => {
    if (!selectedCvId || !selectedOutreachJobId) {
      showToast(!selectedCvId ? t('linkedin.noCvs') : t('linkedin.noJobs'), 'warning');
      return;
    }

    setIsOutreachGenerating(true);
    setError(null);
    try {
      const result = await apiService.generateColdOutreach(
        Number(selectedOutreachJobId),
        Number(selectedCvId),
        hiringManagerName,
        aiLanguage,
      );
      setOutreachResult(result);
    } catch (err) {
      const message = err instanceof Error ? err.message : t('linkedin.failedOutreach');
      setError(message);
      showToast(message, 'error');
    } finally {
      setIsOutreachGenerating(false);
    }
  }, [aiLanguage, hiringManagerName, selectedCvId, selectedOutreachJobId, showToast, t]);



  if (isLoading) {
    return (
      <div className="animate-in fade-in space-y-4 duration-300">
        <Card className="rounded-3xl p-5">
          <div className="skeleton-block h-10 w-72 max-w-full rounded-xl" />
          <div className="mt-4 grid gap-4 lg:grid-cols-3">
            <div className="skeleton-block h-48 rounded-2xl" />
            <div className="skeleton-block h-48 rounded-2xl" />
            <div className="skeleton-block h-48 rounded-2xl" />
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="animate-in fade-in space-y-4 pb-8 duration-300">
      <Card className="rounded-3xl p-4 lg:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-brand-primary/10 px-3 py-1 text-xs font-bold uppercase tracking-wider text-brand-primary">
              <AtSign size={14} />
              LinkedIn
            </div>
            <h1 className="break-words text-2xl font-heading font-extrabold text-brand-text dark:text-white lg:text-3xl">
              {t('linkedin.title')}
            </h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500 dark:text-slate-400">
              {t('linkedin.subtitle')}
            </p>
          </div>
          <div className="rounded-2xl bg-slate-100 px-4 py-3 text-sm text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            <span className="font-semibold">{selectedCv?.name ?? t('common.selectCv')}</span>
          </div>
        </div>
      </Card>

      <div className="glass-card rounded-2xl p-3">
        <div className="flex gap-2 overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`inline-flex h-11 shrink-0 items-center gap-2 whitespace-nowrap rounded-xl px-4 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary ${
                activeTab === tab.id
                  ? 'bg-brand-primary text-white shadow-md'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700'
              }`}
            >
              <tab.icon size={17} />
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

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
        <aside className="space-y-4 xl:sticky xl:top-[84px] xl:h-fit">
          <Card className="rounded-3xl p-4">
            <div className="space-y-4">
              <div>
                <label htmlFor="linkedin-cv" className="mb-1.5 block text-sm font-semibold text-slate-700 dark:text-slate-300">
                  {t('linkedin.selectCv')}
                </label>
                <select
                  id="linkedin-cv"
                  value={selectedCvId}
                  onChange={(event) => setSelectedCvId(event.target.value ? Number(event.target.value) : '')}
                  className="input-field w-full text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary"
                >
                  <option value="" disabled>{t('common.selectCv')}</option>
                  {cvs.map((cv) => (
                    <option key={cv.id} value={cv.id}>{cv.name}</option>
                  ))}
                </select>
                {cvs.length === 0 && <p className="mt-1 text-xs text-rose-500">{t('linkedin.noCvs')}</p>}
              </div>

              {activeTab === 'profile' && (
                <div>
                  <p className="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-300">{t('linkedin.selectJobs')}</p>
                  <div className="max-h-80 space-y-2 overflow-y-auto pr-1">
                    {jobs.map((job) => {
                      const checked = profileJobIds.includes(job.id);
                      return (
                        <label
                          key={job.id}
                          className={`flex cursor-pointer items-start gap-3 rounded-xl border px-3 py-2 text-sm transition ${
                            checked
                              ? 'border-brand-primary/50 bg-brand-primary/10 text-brand-text dark:text-slate-100'
                              : 'border-slate-200 bg-white/70 text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900/50 dark:text-slate-300 dark:hover:bg-slate-800'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => handleProfileJobToggle(job.id)}
                            className="mt-1 h-4 w-4 rounded border-slate-300 text-brand-primary focus:ring-brand-primary"
                          />
                          <span className="min-w-0">
                            <span className="block truncate font-semibold">{job.title}</span>
                            <span className="block truncate text-xs opacity-75">{job.company || t('common.unknownCompany')}</span>
                          </span>
                        </label>
                      );
                    })}
                  </div>
                  {jobs.length === 0 && <p className="text-xs text-rose-500">{t('linkedin.noJobs')}</p>}
                </div>
              )}

              {activeTab === 'outreach' && (
                <>
                  <div>
                    <label htmlFor="outreach-job" className="mb-1.5 block text-sm font-semibold text-slate-700 dark:text-slate-300">
                      {t('linkedin.selectJob')}
                    </label>
                    <select
                      id="outreach-job"
                      value={selectedOutreachJobId}
                      onChange={(event) => setSelectedOutreachJobId(event.target.value ? Number(event.target.value) : '')}
                      className="input-field w-full text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary"
                    >
                      <option value="" disabled>{t('common.selectJob')}</option>
                      {jobs.map((job) => (
                        <option key={job.id} value={job.id}>{formatJobLabel(job)}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label htmlFor="hiring-manager" className="mb-1.5 block text-sm font-semibold text-slate-700 dark:text-slate-300">
                      {t('linkedin.hiringManagerName')}
                    </label>
                    <input
                      id="hiring-manager"
                      value={hiringManagerName}
                      onChange={(event) => setHiringManagerName(event.target.value)}
                      maxLength={120}
                      placeholder={t('linkedin.hiringManagerPlaceholder')}
                      className="input-field w-full text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary"
                    />
                  </div>
                </>
              )}


            </div>
          </Card>
        </aside>

        <section className="min-w-0">
          {activeTab === 'profile' && (
            <Card className="rounded-3xl p-4 lg:p-5">
              <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">{t('linkedin.profileTitle')}</h2>
                  <p className="mt-1 text-sm text-slate-500">{t('linkedin.profileSubtitle')}</p>
                </div>
                <button
                  type="button"
                  onClick={handleGenerateProfile}
                  disabled={!selectedCvId || isProfileGenerating}
                  className="btn-primary inline-flex h-11 items-center justify-center gap-2 px-4 text-sm disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isProfileGenerating ? <Loader2 size={17} className="animate-spin" /> : <Sparkles size={17} />}
                  {isProfileGenerating ? t('linkedin.optimizingProfile') : t('linkedin.generateProfile')}
                </button>
              </div>

              {isProfileGenerating && <SkeletonLoader lines={8} />}

              {!isProfileGenerating && !profileResult && (
                <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500 dark:border-slate-700">
                  {t('linkedin.emptyProfile')}
                </div>
              )}

              {!isProfileGenerating && profileResult && (
                <div className="space-y-4">
                  <ResultSection
                    title={t('linkedin.headline')}
                    action={<CopyButton label={t('common.copyToClipboard')} copied={copiedTarget === 'headline'} onCopy={() => handleCopy('headline', profileResult.headline)} />}
                  >
                    <p className="text-lg font-semibold leading-7 text-slate-900 dark:text-slate-100">{profileResult.headline}</p>
                  </ResultSection>
                  <ResultSection
                    title={t('linkedin.aboutSummary')}
                    action={<CopyButton label={t('common.copyToClipboard')} copied={copiedTarget === 'about'} onCopy={() => handleCopy('about', profileResult.about_summary)} />}
                  >
                    <p className="whitespace-pre-wrap text-sm leading-7 text-slate-700 dark:text-slate-300">{profileResult.about_summary}</p>
                  </ResultSection>
                  <div className="grid gap-4 lg:grid-cols-2">
                    <ResultSection title={t('linkedin.keywords')}>
                      <div className="flex flex-wrap gap-2">
                        {profileResult.keywords.map((keyword) => (
                          <span key={keyword} className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                            {keyword}
                          </span>
                        ))}
                      </div>
                    </ResultSection>
                    <ResultSection title={t('linkedin.optimizationTips')}>
                      <ul className="space-y-2 text-sm text-slate-700 dark:text-slate-300">
                        {profileResult.optimization_tips.map((tip) => (
                          <li key={tip} className="flex gap-2">
                            <Check size={15} className="mt-0.5 shrink-0 text-brand-primary" />
                            <span>{tip}</span>
                          </li>
                        ))}
                      </ul>
                    </ResultSection>
                  </div>
                </div>
              )}
            </Card>
          )}

          {activeTab === 'outreach' && (
            <Card className="rounded-3xl p-4 lg:p-5">
              <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">{t('linkedin.outreachTitle')}</h2>
                  <p className="mt-1 text-sm text-slate-500">{selectedOutreachJob ? formatJobLabel(selectedOutreachJob) : t('linkedin.outreachSubtitle')}</p>
                </div>
                <button
                  type="button"
                  onClick={handleGenerateOutreach}
                  disabled={!selectedCvId || !selectedOutreachJobId || isOutreachGenerating}
                  className="btn-primary inline-flex h-11 items-center justify-center gap-2 px-4 text-sm disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isOutreachGenerating ? <Loader2 size={17} className="animate-spin" /> : <MessageSquare size={17} />}
                  {isOutreachGenerating ? t('linkedin.craftingOutreach') : t('linkedin.generateOutreach')}
                </button>
              </div>

              {isOutreachGenerating && <SkeletonLoader lines={5} />}
              {!isOutreachGenerating && !outreachResult && (
                <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500 dark:border-slate-700">
                  {t('linkedin.emptyOutreach')}
                </div>
              )}
              {!isOutreachGenerating && outreachResult && (
                <div className="space-y-4">
                  <ResultSection
                    title={t('linkedin.connectionMessage')}
                    action={<CopyButton label={t('common.copyToClipboard')} copied={copiedTarget === 'outreach'} onCopy={() => handleCopy('outreach', outreachResult.connection_message)} />}
                  >
                    <p className="text-base leading-7 text-slate-800 dark:text-slate-200">{outreachResult.connection_message}</p>
                    <p className="mt-3 text-xs font-semibold text-slate-500">
                      {t('linkedin.characterCount', { count: outreachResult.connection_message.length })}
                    </p>
                  </ResultSection>
                  <ResultSection title={t('linkedin.personalizationNotes')}>
                    <ul className="space-y-2 text-sm text-slate-700 dark:text-slate-300">
                      {outreachResult.personalization_notes.map((note) => (
                        <li key={note} className="flex gap-2">
                          <Briefcase size={15} className="mt-0.5 shrink-0 text-brand-primary" />
                          <span>{note}</span>
                        </li>
                      ))}
                    </ul>
                  </ResultSection>
                </div>
              )}
            </Card>
          )}


        </section>
      </div>
    </div>
  );
}
