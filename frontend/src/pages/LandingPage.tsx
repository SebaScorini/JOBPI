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
    {
      icon: BrainCircuit,
      title: 'AI Resume Analysis & ATS Resume Optimizer',
      desc: 'Run an AI resume tool that finds missing skills, weak phrasing, and ATS gaps so your CV is ready for modern screening systems.',
    },
    {
      icon: Sparkles,
      title: 'CV to Job Matching AI',
      desc: 'Use a CV analyzer that compares your profile against real job requirements and explains why one version performs better.',
    },
    {
      icon: Upload,
      title: 'Multi-CV Resume Management',
      desc: 'Upload and organize multiple CV versions by role, language, and focus area to improve application quality and speed.',
    },
    {
      icon: Library,
      title: 'AI Cover Letter Generator',
      desc: 'Generate tailored cover letters based on your CV and target job description in seconds with actionable edits.',
    },
    {
      icon: LayoutDashboard,
      title: 'AI Job Tracker',
      desc: 'Track each application stage in one dashboard so you never lose momentum, deadlines, or interview follow-ups.',
    },
    {
      icon: Zap,
      title: 'Fast Job Search AI Workflow',
      desc: 'From analysis to matching and cover letter generation, JOBPI keeps your workflow lightweight and focused on outcomes.',
    },
  ];

  const steps = [
    {
      num: 1,
      title: 'Upload your resume portfolio',
      desc: 'Add one or more CVs so JOBPI can compare versions for different roles and ATS expectations.',
    },
    {
      num: 2,
      title: 'Paste a target job description',
      desc: 'JOBPI extracts required skills, responsibilities, and hidden keywords from the posting.',
    },
    {
      num: 3,
      title: 'Optimize, match, and apply',
      desc: 'Get the best resume matcher AI recommendation, generate a cover letter, and track your application status.',
    },
  ];

  const benefits = [
    'Increase interview conversion with ATS-optimized resume improvements.',
    'Reduce manual effort by automating CV analysis and job matching.',
    'Improve application quality with role-specific AI recommendations.',
    'Keep your entire job search pipeline organized in one place.',
  ];

  const faqs = [
    {
      q: 'What is JOBPI?',
      a: 'JOBPI is an AI job application assistant that combines AI resume analysis, ATS resume optimization, CV-to-job matching, cover letter generation, and job tracking.',
    },
    {
      q: 'How does JOBPI help with ATS optimization?',
      a: 'Our ATS resume optimizer reviews your resume against job requirements and highlights missing keywords, weak sections, and alignment opportunities so recruiters can find your strengths faster.',
    },
    {
      q: 'Can I manage multiple CV versions?',
      a: 'Yes. JOBPI supports multi-CV management so you can keep role-specific resumes, compare fit with job descriptions, and choose the strongest version before applying.',
    },
    {
      q: 'Is JOBPI only for resumes?',
      a: 'No. JOBPI also includes an AI cover letter generator and an AI job tracker to support your full end-to-end job search workflow.',
    },
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
        <nav aria-label="Primary" className="hidden items-center gap-5 text-sm font-medium text-slate-600 dark:text-slate-300 lg:flex">
          <a href="#what-is-jobpi" className="transition-colors hover:text-brand-primary dark:hover:text-brand-secondary">
            What is JOBPI
          </a>
          <a href="#features" className="transition-colors hover:text-brand-primary dark:hover:text-brand-secondary">
            Features
          </a>
          <a href="#how-it-works" className="transition-colors hover:text-brand-primary dark:hover:text-brand-secondary">
            How it works
          </a>
          <a href="#benefits" className="transition-colors hover:text-brand-primary dark:hover:text-brand-secondary">
            Benefits
          </a>
          <a href="#faq" className="transition-colors hover:text-brand-primary dark:hover:text-brand-secondary">
            FAQ
          </a>
        </nav>
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
        <section id="what-is-jobpi" className="relative mx-auto max-w-7xl px-4 pb-24 pt-16 text-center sm:px-6 sm:pb-32 sm:pt-20">
          <div className="pointer-events-none absolute left-1/2 top-1/2 -z-10 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-brand-primary/10 blur-[120px] dark:bg-brand-secondary/5" />

          <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-blue-100 bg-blue-50 px-3 py-1 text-sm font-medium text-brand-primary dark:border-blue-800/50 dark:bg-blue-900/30 dark:text-blue-400">
            <Sparkles size={16} />
            <span>AI resume tool built for modern job seekers</span>
          </div>

          <h1 className="mb-6 text-5xl font-heading font-bold leading-[1.1] tracking-tight text-slate-900 dark:text-white md:text-7xl">
            AI Resume Tool, CV Analyzer, and Job Application Assistant in One Platform
          </h1>

          <p className="mx-auto mb-6 max-w-4xl text-lg text-slate-600 dark:text-slate-400 md:text-xl">
            JOBPI helps you optimize resumes for ATS, run AI CV analysis, match the best CV to each role, generate tailored cover letters, and track every application from one dashboard.
          </p>

          <p className="mx-auto mb-10 max-w-3xl text-base text-slate-600 dark:text-slate-400 md:text-lg">
            If you are comparing resume AI tools, CV analyzers, and job tracking apps, JOBPI gives you the complete workflow with practical recommendations you can apply immediately.
          </p>

          <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link to="/register" className="flex w-full cursor-pointer items-center justify-center gap-2 rounded-xl bg-brand-cta px-8 py-3.5 text-base font-semibold text-white shadow-[0_4px_12px_rgba(34,197,94,0.25)] transition-all hover:-translate-y-0.5 hover:shadow-[0_6px_16px_rgba(34,197,94,0.35)] sm:w-auto">
              Start Free and Optimize My Resume <ArrowRight size={18} />
            </Link>
            <Link to="/login" className="w-full cursor-pointer rounded-xl border border-slate-200 bg-white px-8 py-3.5 font-semibold text-slate-700 shadow-sm transition-all hover:border-slate-300 hover:bg-slate-50 dark:border-slate-800 dark:bg-[#151B2B] dark:text-slate-300 dark:hover:border-slate-700 dark:hover:bg-[#1A2235] sm:w-auto">
              {t('landing.logIn')}
            </Link>
          </div>
        </section>

        <section id="features" className="border-y border-slate-200/50 bg-white/50 py-20 dark:border-slate-800/50 dark:bg-[#111726]/50 sm:py-24">
          <div className="mx-auto max-w-7xl px-4 sm:px-6">
            <div className="mb-16 text-center">
              <h2 className="mb-4 text-3xl font-heading font-bold text-slate-900 dark:text-white">Features for High-Performance Job Applications</h2>
              <p className="mx-auto max-w-3xl text-slate-600 dark:text-slate-400">
                JOBPI combines the capabilities of a resume optimizer AI, job matching AI, and AI job tracker so every application is more targeted and easier to manage.
              </p>
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

        <section id="how-it-works" className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-24">
          <div className="mb-16 text-center">
            <h2 className="mb-4 text-3xl font-heading font-bold text-slate-900 dark:text-white">How JOBPI Works</h2>
            <p className="text-slate-600 dark:text-slate-400">Three streamlined steps to improve your resume-job fit and apply faster.</p>
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

        <section id="benefits" className="bg-brand-primary py-20 text-white sm:py-24">
          <div className="mx-auto max-w-7xl px-4 sm:px-6">
            <div className="grid items-center gap-12 md:grid-cols-2">
              <div>
                <h2 className="mb-6 text-3xl font-heading font-bold md:text-4xl">Benefits of Using JOBPI</h2>
                <p className="mb-8 text-lg leading-relaxed text-blue-100">
                  JOBPI is built to compete with standalone resume AI tools, CV analyzers, and tracking apps by delivering one integrated workflow focused on measurable application outcomes.
                </p>
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

        <section id="faq" className="mx-auto max-w-5xl px-4 py-20 sm:px-6 sm:py-24">
          <div className="mb-12 text-center">
            <h2 className="mb-4 text-3xl font-heading font-bold text-slate-900 dark:text-white">FAQ</h2>
            <p className="text-slate-600 dark:text-slate-400">Common questions about our AI CV analyzer, ATS resume optimizer, and job matching workflow.</p>
          </div>
          <div className="space-y-4">
            {faqs.map((item) => (
              <details key={item.q} className="glass-card-solid rounded-2xl p-5">
                <summary className="cursor-pointer text-left text-lg font-semibold text-slate-900 dark:text-white">{item.q}</summary>
                <p className="mt-3 text-slate-600 dark:text-slate-400">{item.a}</p>
              </details>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-4xl px-4 py-20 text-center sm:px-6 sm:py-24">
          <h2 className="mb-6 text-3xl font-heading font-bold text-slate-900 dark:text-white md:text-5xl">
            Ready to Improve Your Resume-Job Match Score?
          </h2>
          <p className="mb-10 text-xl text-slate-600 dark:text-slate-400">
            Start using JOBPI today to optimize your resume, generate tailored cover letters, and track every application in one AI-powered workspace.
          </p>
          <Link to="/register" className="inline-flex cursor-pointer items-center gap-2 rounded-xl bg-brand-cta px-8 py-4 font-bold text-white shadow-lg transition-all hover:-translate-y-1 hover:shadow-xl">
            Create Your Free JOBPI Account <ArrowRight size={20} />
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
          <div className="flex flex-wrap items-center justify-center gap-4">
            <a href="#what-is-jobpi" className="text-sm font-medium text-slate-500 transition-colors hover:text-brand-primary">
              What is JOBPI
            </a>
            <a href="#features" className="text-sm font-medium text-slate-500 transition-colors hover:text-brand-primary">
              Features
            </a>
            <a href="#faq" className="text-sm font-medium text-slate-500 transition-colors hover:text-brand-primary">
              FAQ
            </a>
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
