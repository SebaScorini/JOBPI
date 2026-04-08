import React from 'react';
import { Link, Navigate } from 'react-router-dom';
import {
  BrainCircuit,
  Library,
  Sparkles,
  Upload,
  LayoutDashboard,
  Zap,
  CheckCircle,
  ArrowRight,
  Moon,
  Sun,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import { LanguageSelector } from '../components/LanguageSelector';
import { useAppTheme } from '../context/AppThemeContext';

export function LandingPage() {
  const { user, token, isLoading } = useAuth();
  const { t } = useLanguage();
  const { resolvedTheme, toggleDarkMode } = useAppTheme();

  const features = [
    { icon: BrainCircuit, title: t('landing.features.analysisTitle'), desc: t('landing.features.analysisDesc') },
    { icon: Library, title: t('landing.features.libraryTitle'), desc: t('landing.features.libraryDesc') },
    { icon: Sparkles, title: t('landing.features.matchingTitle'), desc: t('landing.features.matchingDesc') },
    { icon: Upload, title: t('landing.features.uploadsTitle'), desc: t('landing.features.uploadsDesc') },
    { icon: LayoutDashboard, title: t('landing.features.dashboardTitle'), desc: t('landing.features.dashboardDesc') },
    { icon: Zap, title: t('landing.features.fastTitle'), desc: t('landing.features.fastDesc') },
  ];

  const steps = [
    { num: 1, title: t('landing.steps.uploadTitle'), desc: t('landing.steps.uploadDesc') },
    { num: 2, title: t('landing.steps.pasteTitle'), desc: t('landing.steps.pasteDesc') },
    { num: 3, title: t('landing.steps.matchTitle'), desc: t('landing.steps.matchDesc') },
  ];

  const benefits = [
    t('landing.benefits.time'),
    t('landing.benefits.choose'),
    t('landing.benefits.callback'),
    t('landing.benefits.organize'),
  ];

  if (isLoading) {
    return (
      <div className="min-h-screen bg-brand-background dark:bg-[#0B0F19] flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-4 border-slate-200 dark:border-slate-800 border-t-brand-primary animate-spin" />
      </div>
    );
  }

  if (user || token) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="min-h-screen bg-brand-background text-brand-text transition-colors duration-300 selection:bg-brand-primary/20 dark:bg-[#0B0F19] dark:text-slate-200">
      <header className="container mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-6 sm:px-6">
        <div className="flex items-center gap-2">
          <div className="rounded-xl bg-brand-primary p-2 text-white">
            <BrainCircuit size={24} />
          </div>
          <span className="text-xl font-heading font-bold text-slate-900 dark:text-white">JOBPI</span>
        </div>
        <div className="flex w-full items-center justify-end gap-3 sm:w-auto">
          <LanguageSelector className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm transition-colors focus:border-brand-primary focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300" />
          <button
            type="button"
            onClick={toggleDarkMode}
            className="rounded-xl bg-slate-100 p-2.5 text-slate-500 transition-colors hover:bg-slate-200 hover:text-brand-primary dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-slate-700 dark:hover:text-brand-secondary"
            aria-label={t('common.themeToggle')}
          >
            {resolvedTheme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          <div className="hidden items-center gap-4 sm:flex">
            <Link to="/login" className="cursor-pointer px-4 py-2 font-medium transition-colors hover:text-brand-primary">
              {t('landing.logIn')}
            </Link>
            <Link to="/register" className="cursor-pointer rounded-xl bg-brand-cta px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-all hover:-translate-y-0.5 hover:opacity-90">
              {t('landing.signUpFree')}
            </Link>
          </div>
        </div>
      </header>

      <main>
        <section className="relative mx-auto max-w-7xl px-4 pb-24 pt-16 text-center sm:px-6 sm:pb-32 sm:pt-20">
          <div className="pointer-events-none absolute left-1/2 top-1/2 -z-10 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-brand-primary/10 blur-[120px] dark:bg-brand-secondary/5" />

          <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-blue-100 bg-blue-50 px-3 py-1 text-sm font-medium text-brand-primary dark:border-blue-800/50 dark:bg-blue-900/30 dark:text-blue-400">
            <Sparkles size={16} />
            <span>{t('landing.badge')}</span>
          </div>

          <h1 className="mb-6 text-5xl font-heading font-bold leading-[1.1] tracking-tight text-slate-900 dark:text-white md:text-7xl">
            {t('landing.heroTitle')}
          </h1>

          <p className="mx-auto mb-10 max-w-2xl text-lg text-slate-600 dark:text-slate-400 md:text-xl">
            {t('landing.heroSubtitle')}
          </p>

          <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link to="/register" className="flex w-full cursor-pointer items-center justify-center gap-2 rounded-xl bg-brand-cta px-8 py-3.5 text-base font-semibold text-white shadow-[0_4px_12px_rgba(34,197,94,0.25)] transition-all hover:-translate-y-0.5 hover:shadow-[0_6px_16px_rgba(34,197,94,0.35)] sm:w-auto">
              {t('landing.getStarted')} <ArrowRight size={18} />
            </Link>
            <Link to="/login" className="w-full cursor-pointer rounded-xl border border-slate-200 bg-white px-8 py-3.5 font-semibold text-slate-700 shadow-sm transition-all hover:border-slate-300 hover:bg-slate-50 dark:border-slate-800 dark:bg-[#151B2B] dark:text-slate-300 dark:hover:border-slate-700 dark:hover:bg-[#1A2235] sm:w-auto">
              {t('landing.logIn')}
            </Link>
          </div>
        </section>

        <section className="border-y border-slate-200/50 bg-white/50 py-20 dark:border-slate-800/50 dark:bg-[#111726]/50 sm:py-24">
          <div className="mx-auto max-w-7xl px-4 sm:px-6">
            <div className="mb-16 text-center">
              <h2 className="mb-4 text-3xl font-heading font-bold text-slate-900 dark:text-white">{t('landing.featuresTitle')}</h2>
              <p className="mx-auto max-w-2xl text-slate-600 dark:text-slate-400">{t('landing.featuresSubtitle')}</p>
            </div>

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {features.map((feature, idx) => (
                <div key={idx} className="glass-card-solid interactive-card rounded-2xl p-6">
                  <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-brand-background text-brand-primary dark:bg-slate-800/80 dark:text-brand-secondary">
                    <feature.icon size={24} />
                  </div>
                  <h3 className="mb-2 text-lg font-bold text-slate-900 dark:text-white">{feature.title}</h3>
                  <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-400">{feature.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-24">
          <div className="mb-16 text-center">
            <h2 className="mb-4 text-3xl font-heading font-bold text-slate-900 dark:text-white">{t('landing.howItWorks')}</h2>
            <p className="text-slate-600 dark:text-slate-400">{t('landing.howItWorksSubtitle')}</p>
          </div>

          <div className="relative grid gap-8 md:grid-cols-3">
            <div className="absolute left-[15%] right-[15%] top-[40px] z-0 hidden h-0.5 bg-gradient-to-r from-brand-primary/10 via-brand-primary/30 to-brand-primary/10 dark:from-slate-800 dark:via-brand-secondary/30 dark:to-slate-800 md:block" />

            {steps.map((step, idx) => (
              <div key={idx} className="relative z-10 flex flex-col items-center text-center">
                <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-full border-4 border-brand-background bg-white text-xl font-bold text-brand-primary shadow-lg dark:border-[#0B0F19] dark:bg-[#151B2B] dark:text-brand-secondary">
                  {step.num}
                </div>
                <h3 className="mb-3 text-xl font-bold text-slate-900 dark:text-white">{step.title}</h3>
                <p className="text-slate-600 dark:text-slate-400">{step.desc}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="bg-brand-primary py-20 text-white sm:py-24">
          <div className="mx-auto max-w-7xl px-4 sm:px-6">
            <div className="grid items-center gap-12 md:grid-cols-2">
              <div>
                <h2 className="mb-6 text-3xl font-heading font-bold md:text-4xl">{t('landing.whyTitle')}</h2>
                <p className="mb-8 text-lg leading-relaxed text-blue-100">{t('landing.whySubtitle')}</p>
                <ul className="space-y-4">
                  {benefits.map((benefit, idx) => (
                    <li key={idx} className="flex items-center gap-3">
                      <CheckCircle className="text-brand-cta" size={20} />
                      <span className="font-medium">{benefit}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="relative">
                <div className="relative z-10 rounded-2xl border border-white/20 bg-white/10 p-6 shadow-2xl backdrop-blur-md">
                  <div className="mb-4 flex items-center justify-between border-b border-white/10 pb-4">
                    <div className="flex gap-2">
                      <div className="h-3 w-3 rounded-full bg-red-400" />
                      <div className="h-3 w-3 rounded-full bg-amber-400" />
                      <div className="h-3 w-3 rounded-full bg-brand-cta" />
                    </div>
                    <div className="h-4 w-24 rounded-full bg-white/20" />
                  </div>
                  <div className="space-y-4">
                    <div className="h-6 w-3/4 rounded-md bg-white/20" />
                    <div className="h-4 w-full rounded-md bg-white/10" />
                    <div className="h-4 w-5/6 rounded-md bg-white/10" />
                    <div className="flex gap-4 pt-4">
                      <div className="h-10 w-24 rounded-lg bg-brand-cta" />
                      <div className="h-10 w-32 rounded-lg bg-white/10" />
                    </div>
                  </div>
                </div>
                <div className="absolute -right-6 -top-6 z-0 h-24 w-24 rounded-full bg-brand-cta/40 blur-2xl" />
                <div className="absolute -bottom-8 -left-8 z-0 h-32 w-32 rounded-full bg-blue-400/30 blur-2xl" />
              </div>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-4xl px-4 py-20 text-center sm:px-6 sm:py-24">
          <h2 className="mb-6 text-3xl font-heading font-bold text-slate-900 dark:text-white md:text-5xl">
            {t('landing.readyTitle')}
          </h2>
          <p className="mb-10 text-xl text-slate-600 dark:text-slate-400">{t('landing.readySubtitle')}</p>
          <Link to="/register" className="inline-flex cursor-pointer items-center gap-2 rounded-xl bg-brand-cta px-8 py-4 font-bold text-white shadow-lg transition-all hover:-translate-y-1 hover:shadow-xl">
            {t('landing.createFreeAccount')} <ArrowRight size={20} />
          </Link>
        </section>
      </main>

      <footer className="border-t border-slate-200 bg-white dark:border-slate-800 dark:bg-[#0B0F19]">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-6 px-4 py-12 sm:px-6 md:flex-row">
          <div className="flex items-center gap-2">
            <BrainCircuit className="text-brand-primary dark:text-brand-secondary" size={24} />
            <span className="font-heading font-bold text-slate-900 dark:text-white">JOBPI</span>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-500">
            © {new Date().getFullYear()} JOBPI. {t('landing.footerRights')}
          </p>
          <div className="flex gap-6">
            <Link to="/login" className="text-sm font-medium text-slate-500 transition-colors hover:text-brand-primary">
              {t('landing.logIn')}
            </Link>
            <Link to="/register" className="text-sm font-medium text-slate-500 transition-colors hover:text-brand-primary">
              {t('auth.createAccount')}
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
