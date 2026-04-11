import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiService } from '../services/api';
import { JobAnalysisResponse, PaginationMeta } from '../types';
import { Briefcase, ArrowRight, Loader2, Plus, Trash2, Bookmark } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { SkeletonCard } from '../components/SkeletonLoader';
import { useToast } from '../context/ToastContext';
import { PaginationControls } from '../components/PaginationControls';

const statusBadgeMap: Record<string, string> = {
  saved: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
  applied: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  interview: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  rejected: 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300',
  offer: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
};

export function JobsPage() {
  const PAGE_SIZE = 9;
  const { t, language } = useLanguage();
  const { showToast } = useToast();
  const [jobs, setJobs] = useState<JobAnalysisResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [deletingJobId, setDeletingJobId] = useState<number | null>(null);
  const [savingJobId, setSavingJobId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [savedFilter, setSavedFilter] = useState<'all' | 'saved' | 'unsaved'>('all');
  const [pagination, setPagination] = useState<PaginationMeta>({
    total: 0,
    limit: PAGE_SIZE,
    offset: 0,
    has_more: false,
  });

  useEffect(() => {
    async function fetchJobs() {
      try {
        const data = await apiService.listJobsPage({
          limit: PAGE_SIZE,
          offset: pagination.offset,
          saved: savedFilter === 'all' ? undefined : savedFilter === 'saved',
        });
        setJobs(data.items);
        setPagination(data.pagination);
        setError(null);
      } catch (err) {
        const message = err instanceof Error ? err.message : t('jobs.failedLoad');
        setError(message);
        showToast(message, 'error');
      } finally {
        setIsLoading(false);
      }
    }
    fetchJobs();
  }, [pagination.offset, savedFilter, showToast, t]);

  const handleDeleteJob = async (jobId: number) => {
    const confirmed = window.confirm(t('jobs.confirmDelete'));
    if (!confirmed) {
      return;
    }

    setDeletingJobId(jobId);
    setError(null);
    try {
      await apiService.deleteJob(jobId);
      const nextOffset =
        jobs.length === 1 && pagination.offset > 0
          ? Math.max(0, pagination.offset - PAGE_SIZE)
          : pagination.offset;

      if (nextOffset !== pagination.offset) {
        setPagination((current) => ({ ...current, offset: nextOffset }));
      } else {
        setJobs((currentJobs) => currentJobs.filter((job) => job.job_id !== jobId));
        setPagination((current) => ({
          ...current,
          total: Math.max(0, current.total - 1),
          has_more: current.offset + current.limit < Math.max(0, current.total - 1),
        }));
      }
      showToast('Job deleted.', 'success');
    } catch (err: any) {
      const message = err.message || t('jobs.failedDelete');
      setError(message);
      showToast(message, 'error');
    } finally {
      setDeletingJobId(null);
    }
  };

  const handleToggleSaved = async (jobId: number) => {
    setSavingJobId(jobId);
    setError(null);
    try {
      const updated = await apiService.toggleSavedJob(jobId);
      const shouldDisappear =
        (savedFilter === 'saved' && !updated.is_saved) ||
        (savedFilter === 'unsaved' && updated.is_saved);

      if (shouldDisappear) {
        const nextOffset =
          jobs.length === 1 && pagination.offset > 0
            ? Math.max(0, pagination.offset - PAGE_SIZE)
            : pagination.offset;

        if (nextOffset !== pagination.offset) {
          setPagination((current) => ({ ...current, offset: nextOffset }));
        } else {
          setJobs((currentJobs) => currentJobs.filter((job) => job.job_id !== jobId));
          setPagination((current) => ({
            ...current,
            total: Math.max(0, current.total - 1),
            has_more: current.offset + current.limit < Math.max(0, current.total - 1),
          }));
        }
      } else {
        setJobs((currentJobs) =>
          currentJobs.map((job) => (job.job_id === jobId ? updated : job)),
        );
      }

      showToast(updated.is_saved ? t('jobs.savedAdded') : t('jobs.savedRemoved'), 'success');
    } catch (err: any) {
      const message = err.message || t('jobs.failedSaveToggle');
      setError(message);
      showToast(message, 'error');
    } finally {
      setSavingJobId(null);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-6">
        <div>
          <h1 className="text-3xl font-heading font-extrabold tracking-tight text-brand-text dark:text-white">
            {t('jobs.title')}
          </h1>
          <p className="text-slate-500 mt-2">{t('jobs.subtitle')}</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={savedFilter}
            onChange={(e) => {
              setSavedFilter(e.target.value as 'all' | 'saved' | 'unsaved');
              setPagination((current) => ({ ...current, offset: 0 }));
            }}
            className="h-11 rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-700 outline-none transition focus:border-brand-primary dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
          >
            <option value="all">{t('jobs.filtersAll')}</option>
            <option value="saved">{t('jobs.filtersSaved')}</option>
            <option value="unsaved">{t('jobs.filtersUnsaved')}</option>
          </select>
          <Link to="/jobs/new" className="btn-primary flex items-center justify-center gap-2 w-auto px-6">
            <Plus size={18} />
            {t('jobs.newTarget')}
          </Link>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/20 dark:text-rose-300">
          {error}
        </div>
      )}

      {isLoading ? (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <SkeletonCard key={index} />
          ))}
        </div>
      ) : jobs.length === 0 ? (
        <div className="text-center py-24 px-4 rounded-3xl border border-dashed border-slate-300 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/20">
          <div className="w-20 h-20 rounded-2xl bg-white dark:bg-slate-900 shadow-sm border border-slate-200 dark:border-slate-800 flex items-center justify-center mx-auto mb-6 group-hover:scale-105 transition-transform">
            <Briefcase size={32} className="text-brand-primary" fill="currentColor" fillOpacity={0.2} />
          </div>
          <p className="text-2xl font-bold font-heading text-slate-800 dark:text-slate-100 mb-2">{t('jobs.emptyTitle')}</p>
          <p className="text-slate-500 max-w-md mx-auto mb-8 text-[15px] leading-relaxed">
            {t('jobs.emptySubtitle')}
          </p>
          <Link to="/jobs/new" className="btn-primary inline-flex justify-center items-center py-3 w-56 text-[15px] font-semibold mx-auto group shadow-lg shadow-brand-primary/20">
            <Plus size={18} className="mr-2" />
            {t('jobs.firstAnalysis')}
          </Link>
        </div>
      ) : (
        <div className="space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {jobs.map((job) => (
              <article
                key={job.job_id}
                className="interactive-card glass-card-solid p-6 rounded-2xl flex flex-col justify-between group h-full"
              >
                <div>
                  <div className="flex justify-between items-start mb-4">
                    <div className="w-10 h-10 rounded-xl bg-brand-primary/10 flex items-center justify-center text-brand-primary">
                      <Briefcase size={20} />
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => handleToggleSaved(job.job_id)}
                        disabled={savingJobId === job.job_id}
                        className={`inline-flex h-9 w-9 items-center justify-center rounded-xl border transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${
                          job.is_saved
                            ? 'border-amber-200 bg-amber-50 text-amber-600 hover:bg-amber-100 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-300'
                            : 'border-slate-200 text-slate-500 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800'
                        }`}
                        aria-label={job.is_saved ? t('jobs.unsaveAction') : t('jobs.saveAction')}
                        title={job.is_saved ? t('jobs.unsaveAction') : t('jobs.saveAction')}
                      >
                        {savingJobId === job.job_id ? (
                          <Loader2 size={16} className="animate-spin" />
                        ) : (
                          <Bookmark size={16} className={job.is_saved ? 'fill-current' : ''} />
                        )}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteJob(job.job_id)}
                        disabled={deletingJobId === job.job_id}
                        className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-rose-200 text-rose-600 transition-colors hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-rose-900/50 dark:text-rose-300 dark:hover:bg-rose-950/30"
                        aria-label={t('jobs.deleteAction')}
                        title={t('jobs.deleteAction')}
                      >
                        {deletingJobId === job.job_id ? <Loader2 size={16} className="animate-spin" /> : <Trash2 size={16} />}
                      </button>
                      <Link
                        to={`/jobs/${job.job_id}`}
                        className="inline-flex h-9 w-9 items-center justify-center rounded-xl text-slate-400 transition-all hover:text-brand-primary hover:translate-x-1"
                        aria-label={t('jobs.openJob')}
                      >
                        <ArrowRight size={20} />
                      </Link>
                    </div>
                  </div>
                  <Link to={`/jobs/${job.job_id}`} className="block">
                    <h3 className="font-heading font-bold text-xl text-brand-text dark:text-white mb-2 leading-tight group-hover:text-brand-primary transition-colors break-words">
                      {job.title || job.role_type || t('common.untitledRole')}
                    </h3>
                    <p className="text-slate-500 font-medium mb-4">
                      {job.company || job.seniority || t('common.unknownCompany')}
                    </p>
                    <div className="mb-4 flex flex-wrap items-center gap-2">
                      {job.is_saved && (
                        <span className="rounded-lg bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">
                          {t('jobs.savedBadge')}
                        </span>
                      )}
                      <span className={`px-2.5 py-1 text-xs font-semibold rounded-lg ${statusBadgeMap[job.status] ?? statusBadgeMap.saved}`}>
                        {t(`statuses.${job.status}`)}
                      </span>
                      {job.applied_date && (
                        <span className="text-xs text-slate-500">
                          {t('jobs.appliedOn', {
                            date: new Date(job.applied_date).toLocaleDateString(language),
                          })}
                        </span>
                      )}
                    </div>
                    <div className="mt-auto flex flex-wrap gap-2">
                      {job.required_skills?.slice(0, 3).map((skill, i) => (
                        <span key={i} className="rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                          {skill}
                        </span>
                      ))}
                      {(job.required_skills?.length || 0) > 3 && (
                        <span className="rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-500 dark:bg-slate-800">
                          +{job.required_skills.length - 3}
                        </span>
                      )}
                    </div>
                  </Link>
                </div>
              </article>
            ))}
          </div>
          <PaginationControls
            pagination={pagination}
            itemLabel={t('jobs.resultsLabel')}
            onPrevious={() =>
              setPagination((current) => ({
                ...current,
                offset: Math.max(0, current.offset - PAGE_SIZE),
              }))
            }
            onNext={() =>
              setPagination((current) => ({
                ...current,
                offset: current.offset + PAGE_SIZE,
              }))
            }
          />
        </div>
      )}
    </div>
  );
}
