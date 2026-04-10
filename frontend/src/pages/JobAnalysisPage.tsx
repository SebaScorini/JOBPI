import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import { Loader2, Zap } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { jobAnalysisSchema, MAX_JOB_DESCRIPTION_CHARS } from '../utils/validation';
import { useToast } from '../context/ToastContext';
import { SkeletonLoader } from '../components/SkeletonLoader';

interface JobAnalysisFieldErrors {
  title?: string;
  company?: string;
  description?: string;
}

export function JobAnalysisPage() {
  const { aiLanguage, t } = useLanguage();
  const { showToast } = useToast();
  const [title, setTitle] = useState('');
  const [company, setCompany] = useState('');
  const [description, setDescription] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<JobAnalysisFieldErrors>({});

  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const parsed = jobAnalysisSchema.safeParse({ title, company, description });
    if (!parsed.success) {
      const nextErrors: JobAnalysisFieldErrors = {};
      for (const issue of parsed.error.issues) {
        const fieldName = issue.path[0];
        if (fieldName === 'title' || fieldName === 'company' || fieldName === 'description') {
          nextErrors[fieldName] = issue.message;
        }
      }
      setFieldErrors(nextErrors);
      return;
    }

    setFieldErrors({});
    setIsLoading(true);

    try {
      const response = await apiService.analyzeJob({
        title: parsed.data.title,
        company: parsed.data.company,
        description: parsed.data.description,
        language: aiLanguage,
      });
      showToast('Analysis complete.', 'success');
      navigate(`/jobs/${response.job_id}`);
    } catch (err: any) {
      const message = err.message || t('jobAnalysis.unexpectedError');
      setError(message);
      showToast(message, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="animate-in fade-in duration-300">
      <div className="mb-8 flex items-center gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-primary/10 text-brand-primary">
          <Zap size={24} />
        </div>
        <div>
          <h1 className="text-3xl font-heading font-extrabold tracking-tight text-brand-text dark:text-white">
            {t('jobAnalysis.title')}
          </h1>
          <p className="mt-1 text-slate-500">{t('jobAnalysis.subtitle')}</p>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_280px]">
        <div className="glass-card rounded-[2rem] p-6 md:p-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 font-medium text-rose-600">
                {error}
              </div>
            )}

            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              <div>
                <label htmlFor="title" className="mb-2 block text-sm font-semibold text-slate-700 dark:text-slate-300">
                  {t('jobAnalysis.jobTitle')}
                </label>
                <input
                  id="title"
                  type="text"
                  value={title}
                  onChange={(e) => {
                    setTitle(e.target.value);
                    if (fieldErrors.title) {
                      setFieldErrors((current) => ({ ...current, title: undefined }));
                    }
                  }}
                  className={`input-field ${fieldErrors.title ? 'input-field-error' : ''}`}
                  placeholder={t('jobAnalysis.titlePlaceholder')}
                />
                {fieldErrors.title && <p className="mt-2 text-xs font-medium text-rose-600">{fieldErrors.title}</p>}
              </div>
              <div>
                <label htmlFor="company" className="mb-2 block text-sm font-semibold text-slate-700 dark:text-slate-300">
                  {t('jobAnalysis.company')}
                </label>
                <input
                  id="company"
                  type="text"
                  value={company}
                  onChange={(e) => {
                    setCompany(e.target.value);
                    if (fieldErrors.company) {
                      setFieldErrors((current) => ({ ...current, company: undefined }));
                    }
                  }}
                  className={`input-field ${fieldErrors.company ? 'input-field-error' : ''}`}
                  placeholder={t('jobAnalysis.companyPlaceholder')}
                />
                {fieldErrors.company && <p className="mt-2 text-xs font-medium text-rose-600">{fieldErrors.company}</p>}
              </div>
            </div>

            <div>
              <div className="mb-2 flex items-center justify-between gap-3">
                <label htmlFor="description" className="block text-sm font-semibold text-slate-700 dark:text-slate-300">
                  {t('jobAnalysis.description')}
                </label>
                <span className="text-xs text-slate-500">
                  {description.length}/{MAX_JOB_DESCRIPTION_CHARS}
                </span>
              </div>
              <textarea
                id="description"
                rows={12}
                value={description}
                onChange={(e) => {
                  setDescription(e.target.value);
                  if (fieldErrors.description) {
                    setFieldErrors((current) => ({ ...current, description: undefined }));
                  }
                }}
                className={`input-field resize-none leading-relaxed ${fieldErrors.description ? 'input-field-error' : ''}`}
                placeholder={t('jobAnalysis.descriptionPlaceholder')}
              />
              {fieldErrors.description && (
                <p className="mt-2 text-xs font-medium text-rose-600">{fieldErrors.description}</p>
              )}
            </div>

            <div className="border-t border-slate-200 pt-4 dark:border-slate-800">
              <button
                type="submit"
                disabled={isLoading}
                className="btn-primary ml-auto flex w-full items-center justify-center gap-2 px-8 text-base md:w-auto"
              >
                {isLoading ? (
                  <>
                    <Loader2 size={20} className="animate-spin" />
                    {t('jobAnalysis.decoding')}
                  </>
                ) : (
                  <>
                    <Zap size={20} />
                    {t('jobAnalysis.extractInsights')}
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        <aside className="glass-card rounded-3xl p-5">
          <h2 className="mb-4 text-sm font-bold uppercase tracking-wider text-slate-500">{t('jobAnalysis.previewTitle')}</h2>
          {isLoading ? (
            <div className="space-y-4">
              <div className="skeleton-block h-7 w-2/3 rounded-xl" />
              <SkeletonLoader lines={6} />
              <div className="grid grid-cols-2 gap-3">
                <div className="skeleton-block h-20 rounded-2xl" />
                <div className="skeleton-block h-20 rounded-2xl" />
              </div>
            </div>
          ) : (
            <div className="space-y-4 text-sm text-slate-600 dark:text-slate-300">
              <p className="leading-7">
                {t('jobAnalysis.previewDesc')}
              </p>
              <div className="rounded-2xl border border-slate-200/70 bg-white/70 p-4 dark:border-slate-800 dark:bg-slate-950/20">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{t('jobAnalysis.previewWhatYouGet')}</p>
                <ul className="mt-3 list-disc space-y-2 pl-5 leading-6">
                  <li>{t('jobAnalysis.previewItem1')}</li>
                  <li>{t('jobAnalysis.previewItem2')}</li>
                  <li>{t('jobAnalysis.previewItem3')}</li>
                </ul>
              </div>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
