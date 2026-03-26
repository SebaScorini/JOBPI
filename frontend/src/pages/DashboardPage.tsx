import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiService } from '../services/api';
import { JobAnalysisResponse, StoredCV } from '../types';
import { Target, FileText, ArrowRight, Loader2, Briefcase } from 'lucide-react';

export function DashboardPage() {
  const { user } = useAuth();
  const userLabel = user?.email?.split('@')[0] ?? 'there';
  const [recentJobs, setRecentJobs] = useState<JobAnalysisResponse[]>([]);
  const [cvs, setCvs] = useState<StoredCV[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadDashboard() {
      try {
        const [jobsData, cvsData] = await Promise.all([
          apiService.listJobs().catch(() => []),
          apiService.listCVs().catch(() => [])
        ]);
        setRecentJobs(jobsData.slice(0, 3));
        setCvs(cvsData);
      } finally {
        setIsLoading(false);
      }
    }
    loadDashboard();
  }, []);

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="animate-spin text-brand-primary h-8 w-8" />
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      <header className="mb-8">
        <h1 className="text-4xl font-extrabold tracking-tight text-brand-text dark:text-white mb-2">
          Welcome back, {userLabel}
        </h1>
        <p className="text-lg text-slate-500 dark:text-slate-400">
          Here's an overview of your job hunting progress.
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div className="glass-card-solid p-6 rounded-2xl flex flex-col justify-between">
          <div>
            <div className="w-12 h-12 rounded-xl bg-sky-100 dark:bg-sky-500/10 flex items-center justify-center text-sky-600 dark:text-sky-400 mb-4">
              <Briefcase size={24} />
            </div>
            <h3 className="text-sm font-semibold text-slate-500 mb-1 uppercase tracking-wider">Analyzed Roles</h3>
            <p className="text-3xl font-heading font-bold text-slate-900 dark:text-white">{recentJobs.length}</p>
          </div>
        </div>

        <div className="glass-card-solid p-6 rounded-2xl flex flex-col justify-between">
          <div>
            <div className="w-12 h-12 rounded-xl bg-emerald-100 dark:bg-emerald-500/10 flex items-center justify-center text-emerald-600 dark:text-emerald-400 mb-4">
              <FileText size={24} />
            </div>
            <h3 className="text-sm font-semibold text-slate-500 mb-1 uppercase tracking-wider">Stored CVs</h3>
            <p className="text-3xl font-heading font-bold text-slate-900 dark:text-white">{cvs.length}</p>
          </div>
        </div>

        <div className="glass-card p-6 rounded-2xl border-brand-primary/20 dark:border-brand-primary/20 flex flex-col justify-center items-center text-center bg-brand-primary/5">
           <Target size={32} className="text-brand-primary mb-3" />
           <h3 className="text-lg font-bold text-brand-text dark:text-white mb-2">Target a New Role</h3>
           <p className="text-sm text-slate-500 mb-4">Paste a job description to extract target skills.</p>
           <Link to="/jobs/new" className="btn-primary inline-flex justify-center items-center w-auto px-6">
             Start Analysis
           </Link>
        </div>
      </div>

      <section className="mt-12">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-heading font-bold text-slate-900 dark:text-white">Recent Jobs</h2>
          <Link to="/jobs" className="text-sm font-semibold text-brand-primary hover:text-brand-secondary flex items-center gap-1">
            View All <ArrowRight size={16} />
          </Link>
        </div>

        {recentJobs.length === 0 ? (
          <div className="text-center py-12 px-4 rounded-3xl border border-dashed border-slate-300 dark:border-slate-800">
            <Briefcase size={40} className="mx-auto text-slate-300 dark:text-slate-600 mb-3" />
            <p className="text-lg font-semibold text-slate-600 dark:text-slate-400">No jobs analyzed yet</p>
            <p className="text-slate-500 mt-1 mb-4">Get started by analyzing your first job description.</p>
            <Link to="/jobs/new" className="btn-secondary inline-flex justify-center items-center w-auto px-6">
              Analyze Job
            </Link>
          </div>
        ) : (
          <div className="grid gap-4">
            {recentJobs.map((job) => (
              <Link 
                key={job.job_id} 
                to={`/jobs/${job.job_id}`}
                className="interactive-card glass-card-solid p-5 rounded-2xl flex items-center justify-between group"
              >
                <div>
                  <h3 className="font-bold text-lg text-slate-900 dark:text-white group-hover:text-brand-primary transition-colors">
                    {job.title || job.role_type || 'Untitled Role'}
                  </h3>
                  <p className="text-sm text-slate-500">{job.company || job.seniority || 'Unknown Company'}</p>
                </div>
                <ArrowRight className="text-slate-400 group-hover:text-brand-primary group-hover:translate-x-1 transition-all" />
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
