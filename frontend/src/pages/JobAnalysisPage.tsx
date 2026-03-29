import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import { Loader2, Zap } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';

export function JobAnalysisPage() {
  const { aiLanguage, t } = useLanguage();
  const [title, setTitle] = useState('');
  const [company, setCompany] = useState('');
  const [description, setDescription] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const response = await apiService.analyzeJob({ title, company, description, language: aiLanguage });
      navigate(`/jobs/${response.job_id}`);
    } catch (err: any) {
      setError(err.message || t('jobAnalysis.unexpectedError'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-3xl animate-in fade-in duration-300">
      <div className="flex items-center gap-4 mb-8">
        <div className="w-12 h-12 rounded-2xl bg-brand-primary/10 flex items-center justify-center text-brand-primary">
          <Zap size={24} />
        </div>
        <div>
          <h1 className="text-3xl font-heading font-extrabold tracking-tight text-brand-text dark:text-white">
            {t('jobAnalysis.title')}
          </h1>
          <p className="text-slate-500 mt-1">{t('jobAnalysis.subtitle')}</p>
        </div>
      </div>

      <div className="glass-card p-6 md:p-8 rounded-[2rem]">
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
             <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-600 font-medium">
               {error}
             </div>
          )}
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label htmlFor="title" className="block text-sm font-semibold mb-2 text-slate-700 dark:text-slate-300">{t('jobAnalysis.jobTitle')}</label>
              <input
                id="title"
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="input-field"
                placeholder={t('jobAnalysis.titlePlaceholder')}
              />
            </div>
            <div>
              <label htmlFor="company" className="block text-sm font-semibold mb-2 text-slate-700 dark:text-slate-300">{t('jobAnalysis.company')}</label>
              <input
                id="company"
                type="text"
                required
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                className="input-field"
                placeholder={t('jobAnalysis.companyPlaceholder')}
              />
            </div>
          </div>

          <div>
            <label htmlFor="description" className="block text-sm font-semibold mb-2 text-slate-700 dark:text-slate-300">{t('jobAnalysis.description')}</label>
            <textarea
              id="description"
              required
              rows={12}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="input-field resize-none leading-relaxed"
              placeholder={t('jobAnalysis.descriptionPlaceholder')}
            />
          </div>

          <div className="pt-4 border-t border-slate-200 dark:border-slate-800">
             <button
               type="submit"
               disabled={isLoading || !title.trim() || !company.trim() || !description.trim()}
               className="btn-primary w-full md:w-auto px-8 flex items-center justify-center gap-2 text-base ml-auto"
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
    </div>
  );
}
