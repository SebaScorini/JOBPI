import React, { useEffect, useState } from 'react';
import { apiService } from '../services/api';
import { X, UploadCloud, Briefcase, Zap } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../context/LanguageContext';

const ONBOARDING_DISMISSED_KEY = 'jobpi_onboarding_dismissed';

export function OnboardingOverlay() {
  const [isVisible, setIsVisible] = useState(false);
  const [step, setStep] = useState(1);
  const navigate = useNavigate();
  const { t } = useLanguage();

  useEffect(() => {
    const checkOnboarding = async () => {
      if (localStorage.getItem(ONBOARDING_DISMISSED_KEY)) {
        return;
      }
      try {
        const cvs = await apiService.listCVsPage({ limit: 1 });
        if (cvs.pagination.total === 0) {
          setIsVisible(true);
        } else {
          // If they have CVs, dismiss permanently
          localStorage.setItem(ONBOARDING_DISMISSED_KEY, 'true');
        }
      } catch (e) {
        // Ignore API failures on overlay
      }
    };
    checkOnboarding();
  }, []);

  if (!isVisible) return null;

  const handleDismiss = () => {
    localStorage.setItem(ONBOARDING_DISMISSED_KEY, 'true');
    setIsVisible(false);
  };

  const steps = [
    {
      icon: <UploadCloud size={40} className="text-brand-primary mx-auto mb-4" />,
      title: t('onboarding.welcomeTitle'),
      desc: t('onboarding.welcomeDesc'),
      cta: t('onboarding.ctaNext'),
      action: () => setStep(2)
    },
    {
      icon: <Briefcase size={40} className="text-brand-primary mx-auto mb-4" />,
      title: t('onboarding.pasteTitle'),
      desc: t('onboarding.pasteDesc'),
      cta: t('onboarding.ctaNext'),
      action: () => setStep(3)
    },
    {
      icon: <Zap size={40} className="text-brand-primary mx-auto mb-4" />,
      title: t('onboarding.matchTitle'),
      desc: t('onboarding.matchDesc'),
      cta: t('onboarding.ctaGetStarted'),
      action: () => { navigate('/library'); handleDismiss(); }
    }
  ];

  const currentStep = steps[step - 1];

  return (
    <div className="fixed inset-0 z-[100] bg-slate-900/40 dark:bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-300">
      <div className="bg-white dark:bg-[#1A2234] border border-slate-200 dark:border-slate-800 w-full max-w-md rounded-[2rem] p-6 sm:p-8 relative shadow-2xl animate-in zoom-in-95 duration-300">
        <button
          onClick={handleDismiss}
          className="absolute top-4 right-4 p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          aria-label="Skip onboarding"
        >
          <X size={20} />
        </button>

        <div className="text-center mt-4">
          {currentStep.icon}
          <h2 className="text-2xl font-heading font-bold text-slate-900 dark:text-white mb-3">
            {currentStep.title}
          </h2>
          <p className="text-slate-500 dark:text-slate-400 mb-8 leading-relaxed">
            {currentStep.desc}
          </p>

          <div className="flex flex-col gap-4">
            <button
              onClick={currentStep.action}
              className="btn-primary w-full py-3.5 text-[15px] shadow-lg shadow-brand-primary/20 hover:shadow-brand-primary/30"
            >
              {currentStep.cta}
            </button>
            <div className="flex items-center justify-center gap-2 mt-2">
              {steps.map((_, idx) => (
                <div
                  key={idx}
                  className={`h-2 rounded-full transition-all duration-300 ${
                    idx + 1 === step
                      ? 'w-6 bg-brand-primary'
                      : 'w-2 bg-slate-200 dark:bg-slate-700'
                  }`}
                />
              ))}
            </div>
            {step < steps.length && (
              <button
                onClick={handleDismiss}
                className="text-sm font-semibold text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 mt-2"
              >
                {t('onboarding.skipTutorial')}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
