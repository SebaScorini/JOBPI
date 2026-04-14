import { JSX, Suspense, lazy, useEffect } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { LanguageProvider } from './context/LanguageContext';
import { AppThemeProvider } from './context/AppThemeContext';
import { ToastProvider } from './context/ToastContext';
import { ToastViewport } from './components/Toast';
import { RouteFallback } from './components/RouteFallback';

const AuthLayout = lazy(() =>
  import('./components/layout/AuthLayout').then((module) => ({ default: module.AuthLayout })),
);
const AppLayout = lazy(() =>
  import('./components/layout/AppLayout').then((module) => ({ default: module.AppLayout })),
);
const LandingPage = lazy(() =>
  import('./pages/LandingPage').then((module) => ({ default: module.LandingPage })),
);
const LoginPage = lazy(() =>
  import('./pages/LoginPage').then((module) => ({ default: module.LoginPage })),
);
const RegisterPage = lazy(() =>
  import('./pages/RegisterPage').then((module) => ({ default: module.RegisterPage })),
);
const DashboardPage = lazy(() =>
  import('./pages/DashboardPage').then((module) => ({ default: module.DashboardPage })),
);
const CVLibraryPage = lazy(() =>
  import('./pages/CVLibraryPage').then((module) => ({ default: module.CVLibraryPage })),
);
const JobsPage = lazy(() =>
  import('./pages/JobsPage').then((module) => ({ default: module.JobsPage })),
);
const JobAnalysisPage = lazy(() =>
  import('./pages/JobAnalysisPage').then((module) => ({ default: module.JobAnalysisPage })),
);
const JobDetailsPage = lazy(() =>
  import('./pages/JobDetailsPage').then((module) => ({ default: module.JobDetailsPage })),
);
const MatchesPage = lazy(() =>
  import('./pages/MatchesPage').then((module) => ({ default: module.MatchesPage })),
);
const TrackerPage = lazy(() =>
  import('./pages/TrackerPage').then((module) => ({ default: module.TrackerPage })),
);

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

function LazyRoute({
  children,
  variant,
}: {
  children: JSX.Element;
  variant: 'public' | 'auth' | 'app';
}) {
  return <Suspense fallback={<RouteFallback variant={variant} />}>{children}</Suspense>;
}

function ProtectedRoute({ children }: { children: JSX.Element }) {
  const { user, token, isLoading } = useAuth();

  if (isLoading) {
    return <RouteFallback variant="app" />;
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
        <Route
          path="/"
          element={
            <LazyRoute variant="public">
              <LandingPage />
            </LazyRoute>
          }
        />
        <Route
          element={
            <LazyRoute variant="auth">
              <AuthLayout />
            </LazyRoute>
          }
        >
          <Route
            path="/login"
            element={
              <LazyRoute variant="auth">
                <LoginPage />
              </LazyRoute>
            }
          />
          <Route
            path="/register"
            element={
              <LazyRoute variant="auth">
                <RegisterPage />
              </LazyRoute>
            }
          />
        </Route>
        <Route
          element={
            <ProtectedRoute>
              <LazyRoute variant="app">
                <AppLayout />
              </LazyRoute>
            </ProtectedRoute>
          }
        >
          <Route
            path="/dashboard"
            element={
              <LazyRoute variant="app">
                <DashboardPage />
              </LazyRoute>
            }
          />
          <Route
            path="/jobs"
            element={
              <LazyRoute variant="app">
                <JobsPage />
              </LazyRoute>
            }
          />
          <Route
            path="/jobs/new"
            element={
              <LazyRoute variant="app">
                <JobAnalysisPage />
              </LazyRoute>
            }
          />
          <Route
            path="/jobs/:jobId"
            element={
              <LazyRoute variant="app">
                <JobDetailsPage />
              </LazyRoute>
            }
          />
          <Route
            path="/library"
            element={
              <LazyRoute variant="app">
                <CVLibraryPage />
              </LazyRoute>
            }
          />
          <Route
            path="/matches"
            element={
              <LazyRoute variant="app">
                <MatchesPage />
              </LazyRoute>
            }
          />
          <Route
            path="/tracker"
            element={
              <LazyRoute variant="app">
                <TrackerPage />
              </LazyRoute>
            }
          />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Routes>
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
