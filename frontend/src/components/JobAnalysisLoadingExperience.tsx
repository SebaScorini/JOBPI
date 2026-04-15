import { BrainCircuit, CheckCircle2, Sparkles, TimerReset, Wand2 } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

interface JobAnalysisLoadingExperienceProps {
  company: string;
  title: string;
  t: (key: string, params?: Record<string, string | number>) => string;
}

export function JobAnalysisLoadingExperience({
  company,
  title,
  t,
}: JobAnalysisLoadingExperienceProps) {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [activeStage, setActiveStage] = useState(0);

  const stages = useMemo(
    () => [
      {
        icon: BrainCircuit,
        title: t('jobAnalysis.stageExtract'),
        body: t('jobAnalysis.stageExtractBody'),
      },
      {
        icon: Sparkles,
        title: t('jobAnalysis.stageSkills'),
        body: t('jobAnalysis.stageSkillsBody'),
      },
      {
        icon: Wand2,
        title: t('jobAnalysis.stageTailor'),
        body: t('jobAnalysis.stageTailorBody'),
      },
      {
        icon: CheckCircle2,
        title: t('jobAnalysis.stagePrep'),
        body: t('jobAnalysis.stagePrepBody'),
      },
    ],
    [t],
  );

  useEffect(() => {
    const timer = window.setInterval(() => {
      setElapsedSeconds((current) => current + 1);
    }, 1000);

    const rotator = window.setInterval(() => {
      setActiveStage((current) => (current + 1) % stages.length);
    }, 3800);

    return () => {
      window.clearInterval(timer);
      window.clearInterval(rotator);
    };
  }, [stages.length]);

  const activeStageData = stages[activeStage];
  const ActiveStageIcon = activeStageData.icon;
  const minutes = Math.floor(elapsedSeconds / 60);
  const seconds = elapsedSeconds % 60;
  const formattedElapsed = `${minutes}:${String(seconds).padStart(2, '0')}`;

  return (
    <div className="relative overflow-hidden rounded-[2rem] border border-brand-primary/15 bg-[radial-gradient(circle_at_top,rgba(14,165,233,0.14),transparent_38%),linear-gradient(135deg,rgba(255,255,255,0.96),rgba(241,245,249,0.9))] p-6 dark:border-brand-secondary/20 dark:bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.18),transparent_34%),linear-gradient(135deg,rgba(11,15,25,0.98),rgba(21,27,43,0.94))] md:p-8">
      <div className="pointer-events-none absolute inset-0 opacity-70">
        <div className="job-analysis-orb job-analysis-orb-primary" />
        <div className="job-analysis-orb job-analysis-orb-secondary" />
        <div className="job-analysis-grid absolute inset-0" />
      </div>

      <div className="relative z-10 space-y-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-brand-primary dark:text-brand-secondary">
              {t('jobAnalysis.analysisRunning')}
            </p>
            <h2 className="max-w-2xl text-2xl font-heading font-extrabold leading-tight text-brand-text dark:text-white md:text-3xl">
              {t('jobAnalysis.analysisHeadline', {
                title: title || t('common.untitledRole'),
                company: company || t('common.unknownCompany'),
              })}
            </h2>
            <p className="max-w-2xl text-sm leading-7 text-slate-600 dark:text-slate-300">
              {t('jobAnalysis.analysisBody')}
            </p>
          </div>

          <div className="inline-flex items-center gap-3 self-start rounded-2xl border border-white/60 bg-white/75 px-4 py-3 shadow-sm dark:border-slate-800/80 dark:bg-slate-950/40">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-brand-primary/10 text-brand-primary dark:bg-brand-secondary/10 dark:text-brand-secondary">
              <TimerReset size={20} />
            </div>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                {t('jobAnalysis.elapsed')}
              </p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">{formattedElapsed}</p>
            </div>
          </div>
        </div>

        <div className="grid gap-5 xl:grid-cols-[minmax(0,1.3fr)_minmax(300px,0.7fr)]">
          <div className="rounded-[1.75rem] border border-white/70 bg-white/80 p-5 shadow-[0_18px_60px_rgba(15,23,42,0.08)] backdrop-blur dark:border-slate-800/70 dark:bg-slate-950/35 dark:shadow-[0_18px_60px_rgba(2,8,23,0.45)]">
            <div className="flex flex-col gap-5 lg:flex-row lg:items-center">
              <div className="job-analysis-core mx-auto shrink-0 lg:mx-0">
                <div className="job-analysis-core-ring" />
                <div className="job-analysis-core-ring job-analysis-core-ring-delayed" />
                <div className="job-analysis-core-center">
                  <ActiveStageIcon size={30} />
                </div>
              </div>

              <div className="min-w-0 flex-1 space-y-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500 dark:text-slate-400">
                    {t('jobAnalysis.currentStage')}
                  </p>
                  <h3 className="mt-2 text-xl font-bold text-slate-900 dark:text-white">
                    {activeStageData.title}
                  </h3>
                  <p className="mt-2 text-sm leading-7 text-slate-600 dark:text-slate-300">
                    {activeStageData.body}
                  </p>
                </div>

                <div className="space-y-3">
                  {stages.map((stage, index) => {
                    const StageIcon = stage.icon;
                    const isPast = index < activeStage;
                    const isCurrent = index === activeStage;

                    return (
                      <div
                        key={stage.title}
                        className={`flex items-start gap-3 rounded-2xl border px-4 py-3 transition-all ${
                          isCurrent
                            ? 'border-brand-primary/30 bg-brand-primary/10 dark:border-brand-secondary/30 dark:bg-brand-secondary/10'
                            : isPast
                              ? 'border-emerald-200/80 bg-emerald-50/80 dark:border-emerald-900/50 dark:bg-emerald-950/20'
                              : 'border-slate-200/80 bg-slate-50/70 dark:border-slate-800/80 dark:bg-slate-900/30'
                        }`}
                      >
                        <div
                          className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${
                            isCurrent
                              ? 'bg-brand-primary text-white dark:bg-brand-secondary dark:text-slate-950'
                              : isPast
                                ? 'bg-emerald-500 text-white'
                                : 'bg-slate-200 text-slate-500 dark:bg-slate-800 dark:text-slate-400'
                          }`}
                        >
                          <StageIcon size={17} />
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-semibold text-slate-900 dark:text-white">{stage.title}</p>
                          <p className="mt-1 text-xs leading-6 text-slate-500 dark:text-slate-400">{stage.body}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div className="rounded-[1.75rem] border border-white/70 bg-white/80 p-5 shadow-sm backdrop-blur dark:border-slate-800/70 dark:bg-slate-950/35">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500 dark:text-slate-400">
                {t('jobAnalysis.analysisSignals')}
              </p>
              <div className="mt-4 space-y-3">
                <div className="rounded-2xl border border-slate-200/80 bg-slate-50/80 px-4 py-3 dark:border-slate-800/80 dark:bg-slate-900/40">
                  <p className="text-sm font-semibold text-slate-900 dark:text-white">{t('jobAnalysis.signalOneTitle')}</p>
                  <p className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">{t('jobAnalysis.signalOneBody')}</p>
                </div>
                <div className="rounded-2xl border border-slate-200/80 bg-slate-50/80 px-4 py-3 dark:border-slate-800/80 dark:bg-slate-900/40">
                  <p className="text-sm font-semibold text-slate-900 dark:text-white">{t('jobAnalysis.signalTwoTitle')}</p>
                  <p className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">{t('jobAnalysis.signalTwoBody')}</p>
                </div>
                <div className="rounded-2xl border border-slate-200/80 bg-slate-50/80 px-4 py-3 dark:border-slate-800/80 dark:bg-slate-900/40">
                  <p className="text-sm font-semibold text-slate-900 dark:text-white">{t('jobAnalysis.signalThreeTitle')}</p>
                  <p className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">{t('jobAnalysis.signalThreeBody')}</p>
                </div>
              </div>
            </div>

            <div className="rounded-[1.75rem] border border-brand-primary/15 bg-brand-primary/5 p-5 dark:border-brand-secondary/20 dark:bg-brand-secondary/5">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-primary dark:text-brand-secondary">
                {t('jobAnalysis.whileYouWait')}
              </p>
              <p className="mt-3 text-sm leading-7 text-slate-700 dark:text-slate-300">
                {t('jobAnalysis.waitNote')}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
