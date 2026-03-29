import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
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
import { JSX } from 'react';
import { LanguageProvider } from './context/LanguageContext';
import { TrackerPage } from './pages/TrackerPage';

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
        </LanguageProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
