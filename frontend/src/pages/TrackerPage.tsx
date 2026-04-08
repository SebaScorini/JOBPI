import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiService } from '../services/api';
import { JobAnalysisResponse, JobApplicationStatus, PaginationMeta } from '../types';
import { Briefcase, ArrowRight } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { SkeletonLoader } from '../components/SkeletonLoader';
import { useToast } from '../context/ToastContext';
import { PaginationControls } from '../components/PaginationControls';

const statusBadgeMap: Record<JobApplicationStatus, string> = {
  saved: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
  applied: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  interview: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  rejected: 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300',
  offer: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
};

const statusOrder: JobApplicationStatus[] = ['applied', 'interview', 'offer', 'saved', 'rejected'];

export function TrackerPage() {
  const PAGE_SIZE = 12;
  const { t, language } = useLanguage();
  const { showToast } = useToast();
  const [jobs, setJobs] = useState<JobAnalysisResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
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
        });
        setJobs(data.items);
        setPagination(data.pagination);
      } catch (error) {
        const message = error instanceof Error ? error.message : t('jobs.failedLoad');
        showToast(message, 'error');
      } finally {
        setIsLoading(false);
      }
    }

    fetchJobs();
  }, [pagination.offset, showToast, t]);

  const sortedJobs = useMemo(
    () =>
      [...jobs].sort((a, b) => {
        const statusDelta = statusOrder.indexOf(a.status) - statusOrder.indexOf(b.status);
        if (statusDelta !== 0) {
          return statusDelta;
        }
        return new Date(b.created_at ?? 0).getTime() - new Date(a.created_at ?? 0).getTime();
      }),
    [jobs],
  );

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-6">
        <div>
          <h1 className="text-3xl font-heading font-extrabold tracking-tight text-brand-text dark:text-white">
            {t('jobDetails.trackerTitle')}
          </h1>
          <p className="text-slate-500 mt-2">{t('jobs.subtitle')}</p>
        </div>
      </div>

      {isLoading ? (
        <div className="glass-card-solid rounded-2xl p-5">
          <SkeletonLoader lines={6} />
        </div>
      ) : sortedJobs.length === 0 ? (
        <div className="text-center py-20 px-4 rounded-3xl border border-dashed border-slate-300 dark:border-slate-800">
          <Briefcase size={48} className="mx-auto text-slate-300 dark:text-slate-600 mb-4" />
          <p className="text-xl font-semibold text-slate-600 dark:text-slate-400 mb-2">{t('jobs.emptyTitle')}</p>
          <p className="text-slate-500 max-w-sm mx-auto">{t('jobs.emptySubtitle')}</p>
        </div>
      ) : (
        <div className="space-y-4">
          {sortedJobs.map((job) => (
            <Link
              key={job.id}
              to={`/jobs/${job.id}`}
              className="interactive-card glass-card-solid p-5 rounded-2xl flex flex-col gap-3 md:flex-row md:items-center md:justify-between group"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-2">
                  <h2 className="text-lg font-heading font-bold text-brand-text dark:text-white break-words">
                    {job.title || job.role_type || t('common.untitledRole')}
                  </h2>
                  <span className={`px-2.5 py-1 text-xs font-semibold rounded-lg ${statusBadgeMap[job.status]}`}>
                    {t(`statuses.${job.status}`)}
                  </span>
                </div>
                <p className="text-sm text-slate-500 break-words">
                  {job.company || t('common.unknownCompany')}
                </p>
                <p className="text-sm text-slate-600 dark:text-slate-400 mt-2 line-clamp-2">
                  {job.notes?.trim() || job.summary}
                </p>
                {job.applied_date && (
                  <p className="text-xs text-slate-500 mt-2">
                    {t('jobs.appliedOn', {
                      date: new Date(job.applied_date).toLocaleDateString(language),
                    })}
                  </p>
                )}
              </div>

              <ArrowRight size={18} className="shrink-0 text-slate-400 group-hover:text-brand-primary group-hover:translate-x-1 transition-all" />
            </Link>
          ))}
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
