import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiService } from '../services/api';
import { JobAnalysisResponse } from '../types';
import { Briefcase, ArrowRight, Loader2, Plus } from 'lucide-react';

export function JobsPage() {
  const [jobs, setJobs] = useState<JobAnalysisResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchJobs() {
      try {
        const data = await apiService.listJobs();
        setJobs(data);
      } catch (err) {
        console.error('Failed to load jobs', err);
      } finally {
        setIsLoading(false);
      }
    }
    fetchJobs();
  }, []);

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-6">
        <div>
          <h1 className="text-3xl font-heading font-extrabold tracking-tight text-brand-text dark:text-white">
            Job Analysis
          </h1>
          <p className="text-slate-500 mt-2">Manage and review your saved job targets.</p>
        </div>
        <Link to="/jobs/new" className="btn-primary flex items-center justify-center gap-2 w-auto px-6">
          <Plus size={18} />
          New Target
        </Link>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="animate-spin text-brand-primary h-8 w-8" />
        </div>
      ) : jobs.length === 0 ? (
        <div className="text-center py-20 px-4 rounded-3xl border border-dashed border-slate-300 dark:border-slate-800">
          <Briefcase size={48} className="mx-auto text-slate-300 dark:text-slate-600 mb-4" />
          <p className="text-xl font-semibold text-slate-600 dark:text-slate-400 mb-2">No targeted jobs</p>
          <p className="text-slate-500 max-w-sm mx-auto mb-6">Start by analyzing a job description to extract required skills and requirements.</p>
          <Link to="/jobs/new" className="btn-primary inline-flex justify-center items-center w-auto px-8 py-3">
            Analyze First Job
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {jobs.map((job) => (
            <Link 
              key={job.job_id} 
              to={`/jobs/${job.job_id}`}
              className="interactive-card glass-card-solid p-6 rounded-2xl flex flex-col justify-between group h-full"
            >
              <div>
                <div className="flex justify-between items-start mb-4">
                  <div className="w-10 h-10 rounded-xl bg-brand-primary/10 flex items-center justify-center text-brand-primary">
                    <Briefcase size={20} />
                  </div>
                  <ArrowRight size={20} className="text-slate-400 group-hover:text-brand-primary group-hover:translate-x-1 transition-all" />
                </div>
                <h3 className="font-heading font-bold text-xl text-brand-text dark:text-white mb-2 leading-tight group-hover:text-brand-primary transition-colors line-clamp-2">
                  {job.title || job.role_type || 'Untitled Role'}
                </h3>
                <p className="text-slate-500 font-medium mb-4">
                  {job.company || job.seniority || 'Company Unknown'}
                </p>
                <div className="flex flex-wrap gap-2 mt-auto">
                  {job.required_skills?.slice(0, 3).map((skill, i) => (
                    <span key={i} className="px-2.5 py-1 text-xs font-semibold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 rounded-lg">
                      {skill}
                    </span>
                  ))}
                  {(job.required_skills?.length || 0) > 3 && (
                    <span className="px-2.5 py-1 text-xs font-semibold bg-slate-100 dark:bg-slate-800 text-slate-500 rounded-lg">
                      +{job.required_skills.length - 3}
                    </span>
                  )}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
