import React from 'react';
import { PaginationMeta } from '../types';
import { useLanguage } from '../context/LanguageContext';

interface PaginationControlsProps {
  pagination: PaginationMeta;
  itemLabel: string;
  onPrevious: () => void;
  onNext: () => void;
  className?: string;
}

export function PaginationControls({
  pagination,
  itemLabel,
  onPrevious,
  onNext,
  className = '',
}: PaginationControlsProps) {
  const { t } = useLanguage();
  const start = pagination.total === 0 ? 0 : pagination.offset + 1;
  const end = Math.min(pagination.offset + pagination.limit, pagination.total);
  const canGoPrevious = pagination.offset > 0;
  const canGoNext = pagination.has_more;

  return (
    <div
      className={`flex flex-col gap-3 rounded-2xl border border-slate-200/80 bg-white/70 p-3 dark:border-slate-800 dark:bg-slate-950/20 sm:flex-row sm:items-center sm:justify-between ${className}`}
    >
      <p className="text-sm text-slate-500 dark:text-slate-400">
        {t('common.paginationSummary', {
          start,
          end,
          total: pagination.total,
          label: itemLabel,
        })}
      </p>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onPrevious}
          disabled={!canGoPrevious}
          className="rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-600 transition-colors hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          {t('common.previous')}
        </button>
        <button
          type="button"
          onClick={onNext}
          disabled={!canGoNext}
          className="rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-600 transition-colors hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          {t('common.next')}
        </button>
      </div>
    </div>
  );
}
