import React, { useEffect } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export function AuthLayout() {
  const { user, isLoading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isLoading && user) {
      navigate('/');
    }
  }, [user, isLoading, navigate]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-brand-background dark:bg-[#0B0F19]">
        <div className="w-8 h-8 rounded-full border-4 border-slate-200 dark:border-slate-800 border-t-brand-primary animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-brand-background dark:bg-[#0B0F19] text-slate-900 dark:text-slate-100 flex items-center justify-center p-4 selection:bg-brand-primary/20">
      {/* Decorative gradient glow */}
      <div className="fixed top-0 left-0 right-0 h-[600px] bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-brand-primary/20 via-brand-primary/5 to-transparent dark:from-brand-primary/10 dark:via-brand-primary/[0.02] pointer-events-none z-0 transition-colors duration-500" />
      
      <div className="w-full max-w-md relative z-10 glass-card p-8 sm:p-12 rounded-[2rem]">
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-2xl bg-brand-primary/10 flex items-center justify-center text-brand-primary">
              <span className="w-2.5 h-2.5 rounded-full bg-brand-primary shadow-[0_0_8px_rgba(3,105,161,0.5)]"></span>
            </div>
            <h1 className="text-2xl font-heading font-extrabold tracking-tight">JobPi</h1>
          </div>
          <p className="text-slate-500 font-medium">Target your next position with precision.</p>
        </div>
        
        <Outlet />
      </div>
    </div>
  );
}
