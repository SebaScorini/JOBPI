import React, { useEffect, useState } from 'react';
import { apiService } from '../services/api';
import { CVJobMatch } from '../types';
import { Loader2, Zap, LayoutDashboard } from 'lucide-react';

export function MatchesPage() {
  const [matches, setMatches] = useState<CVJobMatch[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchMatches() {
      try {
        const data = await apiService.listMatches();
        setMatches(data);
      } catch (err) {
        console.error('Failed to load matches', err);
      } finally {
        setIsLoading(false);
      }
    }
    fetchMatches();
  }, []);

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-6">
        <div>
          <h1 className="text-3xl font-heading font-extrabold tracking-tight text-brand-text dark:text-white">
            Match History
          </h1>
          <p className="text-slate-500 mt-2">Review your past evaluations and fitment results.</p>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="animate-spin text-brand-primary h-8 w-8" />
        </div>
      ) : matches.length === 0 ? (
        <div className="text-center py-20 px-4 rounded-3xl border border-dashed border-slate-300 dark:border-slate-800">
           <LayoutDashboard size={48} className="mx-auto text-slate-300 dark:text-slate-600 mb-4" />
           <p className="text-xl font-semibold text-slate-600 dark:text-slate-400 mb-2">No Match History</p>
           <p className="text-slate-500 max-w-sm mx-auto">Run a match analysis from a targeted Job description page.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {matches.map((match) => (
            <div key={match.id} className="glass-card-solid p-6 rounded-2xl flex flex-col h-full">
              <div className="flex items-center justify-between mb-4">
                <div className="w-10 h-10 rounded-xl bg-brand-primary/10 flex items-center justify-center text-brand-primary">
                  <Zap size={20} />
                </div>
                <div className={`px-3 py-1 text-sm font-bold rounded-full ${
                  match.result?.likely_fit_level === 'Strong' ? 'bg-brand-cta/20 text-brand-cta' :
                  match.result?.likely_fit_level === 'Moderate' ? 'bg-amber-100 text-amber-600' :
                  'bg-rose-100 text-rose-600'
                 }`}>
                  {match.result?.likely_fit_level || 'Unknown'} Match
                </div>
              </div>
              <h3 className="text-lg font-heading font-bold text-brand-text dark:text-white mb-2 line-clamp-2">
                Job ID: {match.job_id} / CV ID: {match.cv_id}
              </h3>
              <p className="text-slate-500 dark:text-slate-400 text-sm mb-4 line-clamp-3 leading-relaxed flex-1">
                 {match.result?.fit_summary || 'No summary available.'}
              </p>
              <div className="mt-auto text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase flex items-center gap-2">
                 <span>Score: {match.heuristic_score}%</span>
                 <span className="w-1 h-1 rounded-full bg-slate-300 dark:bg-slate-700"></span>
                 <span>Date: {new Date(match.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
