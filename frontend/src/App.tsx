import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { AppLayout } from './components/layout/AppLayout';
import { AuthLayout } from './components/layout/AuthLayout';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { DashboardPage } from './pages/DashboardPage';
import { CVLibraryPage } from './pages/CVLibraryPage';
import { JobsPage } from './pages/JobsPage';
import { JobAnalysisPage } from './pages/JobAnalysisPage';
import { JobDetailsPage } from './pages/JobDetailsPage';
import { MatchesPage } from './pages/MatchesPage';
import { LandingPage } from './pages/LandingPage';
import { JSX, useEffect } from 'react';
import { LanguageProvider } from './context/LanguageContext';
import { TrackerPage } from './pages/TrackerPage';
import { Analytics } from '@vercel/analytics/react';

const DEFAULT_TITLE = 'JOBPI';
const SITE_NAME = 'JOBPI';

function getRouteTitle(pathname: string): string {
  if (pathname === '/') return `Home | ${SITE_NAME}`;
  if (pathname === '/dashboard') return `Dashboard | ${SITE_NAME}`;
  if (pathname === '/library') return `CV Library | ${SITE_NAME}`;
  if (pathname === '/jobs/new') return `Job Analysis | ${SITE_NAME}`;
  if (pathname === '/tracker') return `Tracker | ${SITE_NAME}`;
  if (pathname === '/login') return `Login | ${SITE_NAME}`;
  if (pathname === '/register') return `Register | ${SITE_NAME}`;
  if (pathname === '/jobs') return `Jobs | ${SITE_NAME}`;
  if (pathname.startsWith('/jobs/')) {
    const jobId = pathname.split('/').filter(Boolean).pop();
    return jobId ? `Job ${jobId} | ${SITE_NAME}` : `Job Details | ${SITE_NAME}`;
  }
  if (pathname === '/matches') return `Matches | ${SITE_NAME}`;
  return DEFAULT_TITLE;
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
    const title = getRouteTitle(pathname);
    const configuredSiteUrl = import.meta.env.VITE_SITE_URL as string | undefined;
    const siteUrl = (configuredSiteUrl || window.location.origin).replace(/\/$/, '');
    const canonicalUrl = `${siteUrl}${pathname === '/' ? '/' : pathname}`;

    document.title = title;
    upsertCanonical(canonicalUrl);
    upsertMeta('property', 'og:title', title);
    upsertMeta('property', 'og:url', canonicalUrl);
    upsertMeta('name', 'twitter:title', title);
  }, [pathname]);

  return null;
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
    return <Navigate to="/login" replace />;
  }

  return children;
}

function AppRouter() {
  return (
    <>
      <SeoManager />
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
    </>
  );
}

function App() {
  return (
    // BrowserRouter is outermost so routing hooks work everywhere.
    // AuthProvider wraps AppRouter so useAuth() is always in context.
    <BrowserRouter>
      <AuthProvider>
        <LanguageProvider>
          <AppRouter />
          <Analytics />
        </LanguageProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
