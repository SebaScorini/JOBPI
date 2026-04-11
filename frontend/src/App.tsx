import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { AppLayout } from './components/layout/AppLayout';
import { AuthLayout } from './components/layout/AuthLayout';
import { JSX, Suspense, lazy, useEffect } from 'react';
import { LanguageProvider } from './context/LanguageContext';
import { AppThemeProvider } from './context/AppThemeContext';
import { ToastProvider } from './context/ToastContext';
import { ToastViewport } from './components/Toast';

const SITE_NAME = 'JOBPI';
const SITE_BASE_URL = 'https://jobpi-app.vercel.app';
const DEFAULT_OG_IMAGE = '/favicon.svg';

const LandingPage = lazy(() => import('./pages/LandingPage').then((module) => ({ default: module.LandingPage })));
const LoginPage = lazy(() => import('./pages/LoginPage').then((module) => ({ default: module.LoginPage })));
const RegisterPage = lazy(() => import('./pages/RegisterPage').then((module) => ({ default: module.RegisterPage })));
const DashboardPage = lazy(() => import('./pages/DashboardPage').then((module) => ({ default: module.DashboardPage })));
const CVLibraryPage = lazy(() => import('./pages/CVLibraryPage').then((module) => ({ default: module.CVLibraryPage })));
const JobsPage = lazy(() => import('./pages/JobsPage').then((module) => ({ default: module.JobsPage })));
const JobAnalysisPage = lazy(() => import('./pages/JobAnalysisPage').then((module) => ({ default: module.JobAnalysisPage })));
const JobDetailsPage = lazy(() => import('./pages/JobDetailsPage').then((module) => ({ default: module.JobDetailsPage })));
const MatchesPage = lazy(() => import('./pages/MatchesPage').then((module) => ({ default: module.MatchesPage })));
const TrackerPage = lazy(() => import('./pages/TrackerPage').then((module) => ({ default: module.TrackerPage })));

type RouteSeo = {
  title: string;
  description: string;
  robots: 'index,follow' | 'noindex,nofollow';
  ogType?: 'website' | 'article';
};

const ROUTE_SEO: Record<string, RouteSeo> = {
  '/': {
    title: 'AI Resume Tool & ATS Resume Optimizer | JOBPI',
    description:
      'JOBPI is an AI job application assistant with AI resume analysis, ATS resume optimizer, AI CV analyzer, job matching AI, and AI cover letter generator.',
    robots: 'index,follow',
    ogType: 'website',
  },
  '/login': {
    title: 'Log In | JOBPI AI Job Application Assistant',
    description: 'Log in to JOBPI to continue optimizing resumes, matching CVs to jobs, and tracking applications with AI.',
    robots: 'index,follow',
    ogType: 'website',
  },
  '/register': {
    title: 'Sign Up Free | JOBPI AI Resume Tool',
    description: 'Create a free JOBPI account to use AI resume optimization, AI CV analyzer, and AI cover letter generation tools.',
    robots: 'index,follow',
    ogType: 'website',
  },
  '/dashboard': {
    title: 'Dashboard | JOBPI',
    description: 'Private JOBPI dashboard for job tracking and AI application workflows.',
    robots: 'noindex,nofollow',
  },
  '/library': {
    title: 'CV Library | JOBPI',
    description: 'Private CV library to manage multiple resumes and ATS-ready versions.',
    robots: 'noindex,nofollow',
  },
  '/jobs/new': {
    title: 'New Job Analysis | JOBPI',
    description: 'Private AI workflow for analyzing new job descriptions.',
    robots: 'noindex,nofollow',
  },
  '/jobs': {
    title: 'Jobs | JOBPI',
    description: 'Private job workspace inside JOBPI.',
    robots: 'noindex,nofollow',
  },
  '/matches': {
    title: 'Match History | JOBPI',
    description: 'Private history of CV to job match reports.',
    robots: 'noindex,nofollow',
  },
  '/tracker': {
    title: 'Application Tracker | JOBPI',
    description: 'Private AI job tracker for application status management.',
    robots: 'noindex,nofollow',
  },
};

function getRouteSeo(pathname: string): RouteSeo {
  if (pathname.startsWith('/jobs/')) {
    if (pathname === '/jobs/new') {
      return ROUTE_SEO['/jobs/new'];
    }
    return {
      title: `Job Details | ${SITE_NAME}`,
      description: 'Private job details and AI recommendation page in JOBPI.',
      robots: 'noindex,nofollow',
    };
  }

  return (
    ROUTE_SEO[pathname] ?? {
      title: `${SITE_NAME} | AI Job Application Assistant`,
      description:
        'JOBPI helps candidates optimize resumes, generate AI cover letters, and match CVs to jobs with ATS-focused recommendations.',
      robots: 'index,follow',
      ogType: 'website',
    }
  );
}

function upsertMeta(attr: 'name' | 'property', key: string, value: string) {
  let tag = document.querySelector<HTMLMetaElement>(`meta[${attr}="${key}"]`);
  if (!tag) {
    tag = document.createElement('meta');
    tag.setAttribute(attr, key);
    document.head.appendChild(tag);
  }
  tag.setAttribute('content', value);
}

function upsertCanonical(href: string) {
  let link = document.querySelector<HTMLLinkElement>('link[rel="canonical"]');
  if (!link) {
    link = document.createElement('link');
    link.setAttribute('rel', 'canonical');
    document.head.appendChild(link);
  }
  link.setAttribute('href', href);
}

function SeoManager() {
  const { pathname } = useLocation();

  useEffect(() => {
    const seo = getRouteSeo(pathname);
    const configuredSiteUrl = import.meta.env.VITE_SITE_URL as string | undefined;
    const siteUrl = (configuredSiteUrl || SITE_BASE_URL || window.location.origin).replace(/\/$/, '');
    const canonicalUrl = `${siteUrl}${pathname === '/' ? '/' : pathname}`;
    const imageUrl = `${siteUrl}${DEFAULT_OG_IMAGE}`;

    document.title = seo.title;
    upsertCanonical(canonicalUrl);
    upsertMeta('name', 'description', seo.description);
    upsertMeta('name', 'robots', seo.robots);
    upsertMeta('property', 'og:title', seo.title);
    upsertMeta('property', 'og:description', seo.description);
    upsertMeta('property', 'og:type', seo.ogType ?? 'website');
    upsertMeta('property', 'og:url', canonicalUrl);
    upsertMeta('property', 'og:image', imageUrl);
    upsertMeta('name', 'twitter:card', 'summary_large_image');
    upsertMeta('name', 'twitter:title', seo.title);
    upsertMeta('name', 'twitter:description', seo.description);
    upsertMeta('name', 'twitter:image', imageUrl);

    const schemaElement = document.getElementById('jobpi-schema');
    if (!schemaElement) {
      return;
    }

    if (pathname !== '/') {
      schemaElement.textContent = '';
      return;
    }

    schemaElement.textContent = JSON.stringify([
      {
        '@context': 'https://schema.org',
        '@type': 'Organization',
        name: SITE_NAME,
        url: siteUrl,
        logo: imageUrl,
        description:
          'JOBPI is an AI-powered job application assistant for resume optimization, CV analysis, and job tracking.',
      },
      {
        '@context': 'https://schema.org',
        '@type': 'WebApplication',
        name: SITE_NAME,
        url: siteUrl,
        applicationCategory: 'BusinessApplication',
        operatingSystem: 'Web',
        description:
          'AI resume tool and job matching AI assistant that helps improve ATS readiness and application quality.',
        offers: {
          '@type': 'Offer',
          price: '0',
          priceCurrency: 'USD',
        },
      },
      {
        '@context': 'https://schema.org',
        '@type': 'SoftwareApplication',
        name: SITE_NAME,
        url: siteUrl,
        applicationCategory: 'BusinessApplication',
        operatingSystem: 'Web',
        description:
          'AI CV analyzer, ATS resume optimizer, AI cover letter generator, and AI job tracker in one platform.',
        offers: {
          '@type': 'Offer',
          price: '0',
          priceCurrency: 'USD',
        },
      },
    ]);
  }, [pathname]);

  return null;
}

function RouteFallback() {
  return (
    <div className="min-h-screen bg-brand-background dark:bg-[#0B0F19] flex items-center justify-center">
      <div className="w-8 h-8 rounded-full border-4 border-slate-200 dark:border-slate-800 border-t-brand-primary animate-spin" />
    </div>
  );
}

// ProtectedRoute must live inside AuthProvider to access context
function ProtectedRoute({ children }: { children: JSX.Element }) {
  const { user, token, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-brand-background dark:bg-[#0B0F19] flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-4 border-slate-200 dark:border-slate-800 border-t-brand-primary animate-spin" />
      </div>
    );
  }

  if (!user && !token) {
    return <Navigate to="/" replace />;
  }

  return children;
}

function AppRouter() {
  return (
    <>
      <SeoManager />
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          {/* Public landing route */}
          <Route path="/" element={<LandingPage />} />

          {/* Public auth routes */}
          <Route element={<AuthLayout />}>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
          </Route>

          {/* Protected app routes — AuthProvider is an ancestor so useAuth works */}
          <Route
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/jobs" element={<JobsPage />} />
            <Route path="/jobs/new" element={<JobAnalysisPage />} />
            <Route path="/jobs/:jobId" element={<JobDetailsPage />} />
            <Route path="/library" element={<CVLibraryPage />} />
            <Route path="/matches" element={<MatchesPage />} />
            <Route path="/tracker" element={<TrackerPage />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Route>
        </Routes>
      </Suspense>
    </>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AppThemeProvider>
        <ToastProvider>
          <AuthProvider>
            <LanguageProvider>
              <AppRouter />
              <ToastViewport />
            </LanguageProvider>
          </AuthProvider>
        </ToastProvider>
      </AppThemeProvider>
    </BrowserRouter>
  );
}

export default App;
