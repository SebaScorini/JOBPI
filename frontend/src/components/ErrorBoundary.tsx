import { Component, type ErrorInfo, type ReactNode } from 'react';
import { useLanguage } from '../context/LanguageContext';

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Optional static fallback element */
  fallback?: ReactNode;
  /** Optional callback for error telemetry */
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  /** When any value in this array changes, the boundary resets itself (useful for auto-reset on navigation) */
  resetKeys?: unknown[];
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * Class-based error boundary that catches render-time exceptions and displays
 * a styled fallback instead of a white screen.
 *
 * Usage:
 * ```tsx
 * <ErrorBoundary resetKeys={[pathname]}>
 *   <SomeRoute />
 * </ErrorBoundary>
 * ```
 */
class ErrorBoundaryInner extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('[ErrorBoundary] Uncaught error:', error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  componentDidUpdate(prevProps: ErrorBoundaryProps): void {
    if (!this.state.hasError) {
      return;
    }
    const prevKeys = prevProps.resetKeys ?? [];
    const nextKeys = this.props.resetKeys ?? [];
    const changed = nextKeys.length !== prevKeys.length || nextKeys.some((key, i) => key !== prevKeys[i]);
    if (changed) {
      this.setState({ hasError: false, error: null });
    }
  }

  handleReset = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (!this.state.hasError) {
      return this.props.children;
    }

    if (this.props.fallback) {
      return this.props.fallback;
    }

    return <ErrorFallback error={this.state.error} onReset={this.handleReset} />;
  }
}

/** Styled fallback UI shown when an error is caught */
function ErrorFallback({ error, onReset }: { error: Error | null; onReset: () => void }) {
  let t: (key: string) => string;
  try {
    // eslint-disable-next-line react-hooks/rules-of-hooks
    const lang = useLanguage();
    t = lang.t;
  } catch {
    t = (key: string) => {
      const fallbacks: Record<string, string> = {
        'errorBoundary.title': 'Something went wrong',
        'errorBoundary.message': 'An unexpected error occurred. Please try again or navigate to the dashboard.',
        'errorBoundary.retry': 'Try Again',
        'errorBoundary.goHome': 'Go to Dashboard',
        'errorBoundary.details': 'Error details',
      };
      return fallbacks[key] ?? key;
    };
  }

  const isDev = import.meta.env.DEV;

  return (
    <div className="flex min-h-[320px] items-center justify-center px-4 py-8" role="alert">
      <div className="w-full max-w-lg rounded-3xl border border-red-200/80 bg-white/90 p-8 shadow-lg backdrop-blur dark:border-red-900/40 dark:bg-slate-950/50">
        {/* Icon */}
        <div className="mb-5 flex items-center gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-red-500/10">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="h-6 w-6 text-red-500"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
              {t('errorBoundary.title')}
            </h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              {t('errorBoundary.message')}
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex flex-wrap items-center gap-3">
          <button
            id="error-boundary-retry"
            type="button"
            onClick={onReset}
            className="inline-flex items-center gap-2 rounded-xl bg-brand-primary px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-brand-primary/90 focus:outline-none focus:ring-2 focus:ring-brand-primary/40 focus:ring-offset-2 dark:focus:ring-offset-slate-950"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4" aria-hidden="true">
              <path
                fillRule="evenodd"
                d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H4.68a.75.75 0 00-.75.75v3.552a.75.75 0 001.5 0v-1.927l.247.247a7 7 0 0011.713-3.14.75.75 0 00-1.44-.423zM4.688 8.576a5.5 5.5 0 019.201-2.466l.312.311H11.77a.75.75 0 000 1.5h3.552a.75.75 0 00.75-.75V3.62a.75.75 0 00-1.5 0v1.927l-.247-.247A7 7 0 002.612 8.44a.75.75 0 001.44.423z"
                clipRule="evenodd"
              />
            </svg>
            {t('errorBoundary.retry')}
          </button>

          <a
            id="error-boundary-dashboard"
            href="/dashboard"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-200 focus:ring-offset-2 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700 dark:focus:ring-offset-slate-950"
          >
            {t('errorBoundary.goHome')}
          </a>
        </div>

        {/* Dev-only error details */}
        {isDev && error && (
          <details className="mt-6 rounded-xl border border-slate-200 bg-slate-50/50 p-4 dark:border-slate-800 dark:bg-slate-900/50">
            <summary className="cursor-pointer text-xs font-medium text-slate-500 dark:text-slate-400">
              {t('errorBoundary.details')}
            </summary>
            <pre className="mt-2 overflow-x-auto whitespace-pre-wrap break-words text-xs text-red-600 dark:text-red-400">
              {error.message}
              {'\n'}
              {error.stack}
            </pre>
          </details>
        )}
      </div>
    </div>
  );
}

/** Wrapper that passes location-based resetKeys automatically */
export function ErrorBoundary({
  children,
  resetKeys,
  ...rest
}: ErrorBoundaryProps) {
  return (
    <ErrorBoundaryInner resetKeys={resetKeys} {...rest}>
      {children}
    </ErrorBoundaryInner>
  );
}

export default ErrorBoundary;
