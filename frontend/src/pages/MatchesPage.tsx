import React, { useEffect, useState } from 'react';
import { apiService } from '../services/api';
import { CVJobMatch, PaginationMeta } from '../types';
import { Zap, LayoutDashboard } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { SkeletonCard } from '../components/SkeletonLoader';
import { useToast } from '../context/ToastContext';
import { PaginationControls } from '../components/PaginationControls';

export function MatchesPage() {
  const PAGE_SIZE = 8;
  const { t, language } = useLanguage();
  const { showToast } = useToast();
  const [matches, setMatches] = useState<CVJobMatch[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [pagination, setPagination] = useState<PaginationMeta>({
    total: 0,
    limit: PAGE_SIZE,
    offset: 0,
    has_more: false,
  });
  const matchLevelClasses = {
    strong: 'bg-emerald-100 text-emerald-700',
    medium: 'bg-amber-100 text-amber-700',
    weak: 'bg-rose-100 text-rose-700',
  } as const;

  useEffect(() => {
    async function fetchMatches() {
      try {
        const data = await apiService.listMatchesPage({
          limit: PAGE_SIZE,
          offset: pagination.offset,
        });
        setMatches(data.items);
        setPagination(data.pagination);
      } catch (err) {
        const message = err instanceof Error ? err.message : t('matches.failedLoad');
        showToast(message, 'error');
      } finally {
        setIsLoading(false);
      }
    }
    fetchMatches();
  }, [pagination.offset, showToast, t]);

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-6">
        <div>
          <h1 className="text-3xl font-heading font-extrabold tracking-tight text-brand-text dark:text-white">
            {t('matches.title')}
          </h1>
          <p className="text-slate-500 mt-2">{t('matches.subtitle')}</p>
        </div>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <SkeletonCard key={index} />
          ))}
        </div>
      ) : matches.length === 0 ? (
        <div className="text-center py-24 px-4 rounded-3xl border border-dashed border-slate-300 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/20">
           <div className="w-20 h-20 rounded-2xl bg-white dark:bg-slate-900 shadow-sm border border-slate-200 dark:border-slate-800 flex items-center justify-center mx-auto mb-6">
             <Zap size={32} className="text-brand-primary" fill="currentColor" fillOpacity={0.2} />
           </div>
           <p className="text-2xl font-bold font-heading text-slate-800 dark:text-slate-100 mb-2">{t('matches.emptyTitle', 'No matches found')}</p>
           <p className="text-slate-500 max-w-md mx-auto mb-8">{t('matches.emptySubtitle', 'Compare your CV against job postings to see how well you match and get personalized tips.')}</p>
           <Link to="/jobs/new" className="btn-primary inline-flex justify-center items-center py-3 w-56 text-[15px] font-semibold mx-auto group">
             Go to Job Analysis
           </Link>
        </div>
      ) : (
        <div className="space-y-5">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {matches.map((match) => (
              <div key={match.id} className="glass-card-solid p-6 rounded-2xl flex flex-col h-full">
                <div className="mb-4 flex items-center justify-between">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-primary/10 text-brand-primary">
                    <Zap size={20} />
                  </div>
                  <div className={`rounded-full px-3 py-1 text-sm font-bold ${
                    matchLevelClasses[match.match_level]
                   }`}>
                    {t('matches.matchBadge', { level: match.match_level })}
                  </div>
                </div>
                <h3 className="mb-2 break-words text-lg font-heading font-bold text-brand-text dark:text-white">
                  {t('matches.jobAndCv', { jobId: match.job_id, cvId: match.cv_id })}
                </h3>
                <p className="mb-4 max-h-32 flex-1 overflow-y-auto pr-1 text-sm leading-relaxed text-slate-500 dark:text-slate-400">
                  {match.why_this_cv || match.result?.fit_summary || t('jobDetails.noSummary')}
                </p>
                {match.strengths?.length > 0 && (
                  <div className="mb-4 flex flex-wrap gap-2">
                    {match.strengths.slice(0, 2).map((strength) => (
                      <span key={strength} className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
                        {strength}
                      </span>
                    ))}
                  </div>
                )}
                <div className="mt-auto flex items-center gap-2 text-xs font-semibold uppercase text-slate-400 dark:text-slate-500">
                  <span>{t('common.score')}: {Math.round(match.heuristic_score * 100)}%</span>
                  <span className="h-1 w-1 rounded-full bg-slate-300 dark:bg-slate-700"></span>
                  <span>{t('common.date')}: {new Date(match.created_at).toLocaleDateString(language)}</span>
                </div>
              </div>
            ))}
          </div>
          <PaginationControls
            pagination={pagination}
            itemLabel={t('matches.resultsLabel')}
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
