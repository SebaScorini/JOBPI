interface RouteFallbackProps {
  variant?: 'public' | 'auth' | 'app' | 'panel';
}

const copy = {
  public: {
    title: 'Loading experience',
    subtitle: 'Preparing the page...',
  },
  auth: {
    title: 'Loading secure area',
    subtitle: 'Preparing authentication...',
  },
  app: {
    title: 'Loading workspace',
    subtitle: 'Preparing your dashboard...',
  },
  panel: {
    title: 'Loading section',
    subtitle: 'Preparing this view...',
  },
} as const;

export function RouteFallback({ variant = 'public' }: RouteFallbackProps) {
  const content = copy[variant];

  return (
    <div className="flex min-h-[240px] items-center justify-center px-4 py-8">
      <div className="w-full max-w-lg rounded-3xl border border-slate-200/80 bg-white/80 p-6 shadow-sm backdrop-blur dark:border-slate-800 dark:bg-slate-950/30">
        <div className="mb-4 flex items-center gap-3">
          <div className="h-10 w-10 rounded-2xl bg-brand-primary/10 p-2">
            <div className="h-full w-full rounded-xl border-2 border-brand-primary/20 border-t-brand-primary animate-spin" />
          </div>
          <div className="space-y-2">
            <div className="h-4 w-36 rounded-full bg-slate-200 dark:bg-slate-800" />
            <div className="h-3 w-28 rounded-full bg-slate-100 dark:bg-slate-900" />
          </div>
        </div>
        <div className="space-y-3">
          <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">{content.title}</p>
          <p className="text-sm text-slate-500 dark:text-slate-400">{content.subtitle}</p>
          <div className="space-y-2 pt-2">
            <div className="h-3 w-full rounded-full bg-slate-100 dark:bg-slate-900" />
            <div className="h-3 w-5/6 rounded-full bg-slate-100 dark:bg-slate-900" />
            <div className="h-3 w-2/3 rounded-full bg-slate-100 dark:bg-slate-900" />
          </div>
        </div>
      </div>
    </div>
  );
}
