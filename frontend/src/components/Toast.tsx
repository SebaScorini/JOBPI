import { AlertCircle, CheckCircle2, Info, X, AlertTriangle } from 'lucide-react';
import { useToast } from '../context/ToastContext';

const toastStyles = {
  success: {
    icon: CheckCircle2,
    classes: 'border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900/50 dark:bg-emerald-950/70 dark:text-emerald-200',
  },
  error: {
    icon: AlertCircle,
    classes: 'border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/70 dark:text-rose-200',
  },
  warning: {
    icon: AlertTriangle,
    classes: 'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/70 dark:text-amber-200',
  },
  info: {
    icon: Info,
    classes: 'border-sky-200 bg-sky-50 text-sky-800 dark:border-sky-900/50 dark:bg-sky-950/70 dark:text-sky-200',
  },
} as const;

export function ToastViewport() {
  const { toasts, dismissToast } = useToast();

  return (
    <div className="pointer-events-none fixed inset-x-4 bottom-4 z-[100] flex flex-col items-end gap-3 sm:inset-x-auto sm:right-4 sm:w-full sm:max-w-sm">
      {toasts.map((toast) => {
        const Icon = toastStyles[toast.type].icon;

        return (
          <div
            key={toast.id}
            className={`pointer-events-auto w-full rounded-2xl border px-4 py-3 shadow-lg backdrop-blur-sm animate-in slide-in-from-bottom-3 duration-300 ${toastStyles[toast.type].classes}`}
            role="status"
            aria-live="polite"
          >
            <div className="flex items-start gap-3">
              <Icon size={18} className="mt-0.5 shrink-0" />
              <p className="min-w-0 flex-1 text-sm font-medium leading-6">{toast.message}</p>
              <button
                type="button"
                onClick={() => dismissToast(toast.id)}
                className="rounded-lg p-1 opacity-70 transition-opacity hover:opacity-100"
                aria-label="Dismiss notification"
              >
                <X size={16} />
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
