import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiService } from '../services/api';
import { JobAnalysisResponse } from '../types';
import { Target, FileText, ArrowRight, Briefcase } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { SkeletonCard, SkeletonLoader } from '../components/SkeletonLoader';
import { useToast } from '../context/ToastContext';
import { motion, AnimatePresence } from 'framer-motion';

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1
    }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 300, damping: 24 } }
};

const MotionLink = motion.create(Link);

export function DashboardPage() {
  const { user } = useAuth();
  const { t } = useLanguage();
  const { showToast } = useToast();
  const userLabel = user?.email?.split('@')[0] ?? 'there';
  const [recentJobs, setRecentJobs] = useState<JobAnalysisResponse[]>([]);
  const [jobCount, setJobCount] = useState(0);
  const [cvCount, setCvCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadDashboard() {
      try {
        const [jobsData, cvsData] = await Promise.all([
          apiService.listJobsPage({ limit: 5 }).catch(() => ({
            items: [],
            pagination: { total: 0, limit: 5, offset: 0, has_more: false },
          })),
          apiService.listCVsPage({ limit: 1 }).catch(() => ({
            items: [],
            pagination: { total: 0, limit: 1, offset: 0, has_more: false },
          })),
        ]);
        setJobCount(jobsData.pagination.total);
        setRecentJobs(jobsData.items);
        setCvCount(cvsData.pagination.total);
      } finally {
        setIsLoading(false);
      }
    }
    loadDashboard();
  }, [showToast]);

  return (
    <AnimatePresence mode="wait">
      {isLoading ? (
        <motion.div 
          key="loading"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0, transition: { duration: 0.2 } }}
          className="space-y-4"
        >
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-1">
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
            </div>
            <div className="glass-card-solid rounded-2xl p-5">
              <div className="mb-4 flex items-center justify-between gap-4">
                <div className="skeleton-block h-7 w-40 rounded-xl" />
                <div className="skeleton-block h-6 w-16 rounded-xl" />
              </div>
              <SkeletonLoader lines={5} />
            </div>
          </div>
        </motion.div>
      ) : (
        <motion.div 
          key="content"
          variants={containerVariants}
          initial="hidden"
          animate="show"
          className="space-y-4"
        >
          <motion.header variants={itemVariants} className="mb-2">
            <h1 className="text-3xl lg:text-4xl font-extrabold tracking-tight text-brand-text dark:text-white mb-1">
              {t('dashboard.welcome', { name: userLabel })}
            </h1>
            <p className="text-sm lg:text-base text-slate-500 dark:text-slate-400">
              {t('dashboard.subtitle')}
            </p>
          </motion.header>

          <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)] gap-4">
            <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-1 gap-4">
              <motion.div variants={itemVariants} className="glass-card-solid p-5 rounded-2xl flex flex-col justify-between interactive-card">
                <div>
                  <div className="w-10 h-10 rounded-xl bg-sky-100 dark:bg-sky-500/10 flex items-center justify-center text-sky-600 dark:text-sky-400 mb-3">
                    <Briefcase size={20} />
                  </div>
                  <h3 className="text-xs font-semibold text-slate-500 mb-1 uppercase tracking-wider">{t('dashboard.analyzedRoles')}</h3>
                  <p className="text-3xl font-heading font-bold text-slate-900 dark:text-white">{jobCount}</p>
                </div>
              </motion.div>

              <motion.div variants={itemVariants} className="glass-card-solid p-5 rounded-2xl flex flex-col justify-between interactive-card">
                <div>
                  <div className="w-10 h-10 rounded-xl bg-emerald-100 dark:bg-emerald-500/10 flex items-center justify-center text-emerald-600 dark:text-emerald-400 mb-3">
                    <FileText size={20} />
                  </div>
                  <h3 className="text-xs font-semibold text-slate-500 mb-1 uppercase tracking-wider">{t('dashboard.storedCvs')}</h3>
                  <p className="text-3xl font-heading font-bold text-slate-900 dark:text-white">{cvCount}</p>
                </div>
              </motion.div>

              <motion.div variants={itemVariants} className="glass-card p-5 rounded-2xl border-brand-primary/20 dark:border-brand-primary/20 flex flex-col justify-center items-start bg-brand-primary/5">
                <Target size={24} className="text-brand-primary mb-3" />
                <h3 className="text-base font-bold text-brand-text dark:text-white mb-1">{t('dashboard.targetRole')}</h3>
                <p className="text-xs text-slate-500 mb-3">{t('dashboard.targetRoleDesc')}</p>
                <MotionLink 
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  to="/jobs/new" 
                  className="btn-primary inline-flex justify-center items-center w-auto px-4 !py-2 text-xs"
                >
                  {t('dashboard.startAnalysis')}
                </MotionLink>
              </motion.div>
            </section>

            <motion.section variants={itemVariants} className="glass-card-solid p-5 rounded-2xl min-h-[360px] flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-heading font-bold text-slate-900 dark:text-white">{t('dashboard.recentJobs')}</h2>
                <Link to="/jobs" className="text-sm font-semibold text-brand-primary hover:text-brand-secondary flex items-center gap-1">
                  {t('dashboard.viewAll')} <ArrowRight size={16} />
                </Link>
              </div>

              {recentJobs.length === 0 ? (
                <div className="text-center my-auto py-10 px-4 rounded-2xl border border-dashed border-slate-300 dark:border-slate-800">
                  <Briefcase size={34} className="mx-auto text-slate-300 dark:text-slate-600 mb-3" />
                  <p className="text-base font-semibold text-slate-600 dark:text-slate-400">{t('dashboard.noJobs')}</p>
                  <p className="text-sm text-slate-500 mt-1 mb-4">{t('dashboard.noJobsDesc')}</p>
                  <MotionLink 
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    to="/jobs/new" 
                    className="btn-secondary inline-flex justify-center items-center w-auto px-5 !py-2 text-sm"
                  >
                    {t('dashboard.analyzeJob')}
                  </MotionLink>
                </div>
              ) : (
                <motion.div variants={containerVariants} className="grid gap-3 overflow-y-auto pr-1 max-h-[320px]">
                  {recentJobs.map((job) => (
                    <MotionLink
                      key={job.job_id}
                      variants={itemVariants}
                      whileHover={{ scale: 1.015, y: -2 }}
                      whileTap={{ scale: 0.98 }}
                      to={`/jobs/${job.job_id}`}
                      className="glass-card p-4 rounded-xl flex items-center justify-between group shadow-sm hover:shadow-md transition-shadow"
                    >
                      <div className="min-w-0">
                        <h3 className="font-semibold text-base text-slate-900 dark:text-white group-hover:text-brand-primary transition-colors break-words">
                          {job.title || job.role_type || t('common.untitledRole')}
                        </h3>
                        <p className="text-xs text-slate-500 break-words">{job.company || job.seniority || t('common.unknownCompany')}</p>
                      </div>
                      <ArrowRight className="text-slate-400 group-hover:text-brand-primary group-hover:translate-x-1 transition-all shrink-0" size={18} />
                    </MotionLink>
                  ))}
                </motion.div>
              )}
            </motion.section>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
