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
import { motion, AnimatePresence, Variants } from 'framer-motion';
import { useMotionPreferences } from '../hooks/useMotionPreferences';

const MotionLink = motion.create(Link);

const staggerContainer: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.15
    }
  }
};

const fadeUpVariant: Variants = {
  hidden: { opacity: 0, y: 30 },
  show: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 300, damping: 24 } }
};

const scaleUpVariant: Variants = {
  hidden: { opacity: 0, scale: 0.95 },
  show: { opacity: 1, scale: 1, transition: { type: 'spring', stiffness: 300, damping: 24 } }
};

export function LandingPage() {
  const { user, session, isLoading } = useAuth();
  const { t } = useLanguage();
  const { resolvedTheme, toggleDarkMode } = useAppTheme();
  const { allowRichMotion } = useMotionPreferences();

  const sectionVariants: Variants = allowRichMotion
    ? staggerContainer
    : {
        hidden: { opacity: 0 },
        show: { opacity: 1 },
      };

  const revealVariant: Variants = allowRichMotion
    ? fadeUpVariant
    : {
        hidden: { opacity: 0 },
        show: { opacity: 1 },
      };

  const cardVariant: Variants = allowRichMotion
    ? scaleUpVariant
    : {
        hidden: { opacity: 0 },
        show: { opacity: 1 },
      };

  const features = [
    { icon: BrainCircuit, title: t('landing.features.analysisTitle'), desc: t('landing.features.analysisDesc') },
    { icon: Library, title: t('landing.features.libraryTitle'), desc: t('landing.features.libraryDesc') },
    { icon: Sparkles, title: t('landing.features.matchingTitle'), desc: t('landing.features.matchingDesc') },
    { icon: Upload, title: t('landing.features.uploadsTitle'), desc: t('landing.features.uploadsDesc') },
    { icon: LayoutDashboard, title: t('landing.features.dashboardTitle'), desc: t('landing.features.dashboardDesc') },
    { icon: Zap, title: t('landing.features.fastTitle'), desc: t('landing.features.fastDesc') },
  ];

  const steps = [
    { num: 1, title: t('landing.steps.uploadTitle'), desc: t('landing.steps.uploadDesc') },
    { num: 2, title: t('landing.steps.pasteTitle'), desc: t('landing.steps.pasteDesc') },
    { num: 3, title: t('landing.steps.matchTitle'), desc: t('landing.steps.matchDesc') },
  ];

  const benefits = [
    t('landing.benefits.time'),
    t('landing.benefits.choose'),
    t('landing.benefits.callback'),
    t('landing.benefits.organize'),
  ];

  if (isLoading) {
    return (
      <div className="min-h-screen bg-brand-background dark:bg-[#0B0F19] flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-4 border-slate-200 dark:border-slate-800 border-t-brand-primary animate-spin" />
      </div>
    );
  }

  if (user || session) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="min-h-screen bg-brand-background text-brand-text transition-colors duration-300 selection:bg-brand-primary/20 dark:bg-[#0B0F19] dark:text-slate-200 overflow-hidden">
      <motion.header 
        initial={allowRichMotion ? { y: -20, opacity: 0 } : { opacity: 0 }}
        animate={allowRichMotion ? { y: 0, opacity: 1 } : { opacity: 1 }}
        transition={{ duration: allowRichMotion ? 0.5 : 0.2, ease: "easeOut" }}
        className="container mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-6 sm:px-6"
      >
        <motion.div 
          whileHover={allowRichMotion ? { scale: 1.05 } : undefined}
          whileTap={allowRichMotion ? { scale: 0.95 } : undefined}
          className="flex items-center gap-2 cursor-pointer"
        >
          <div className="rounded-xl bg-brand-primary p-2 text-white shadow-lg shadow-brand-primary/20">
            <BrainCircuit size={24} />
          </div>
          <span className="text-xl font-heading font-bold text-slate-900 dark:text-white">JOBPI</span>
        </motion.div>
        
        <div className="flex w-full items-center justify-end gap-3 sm:w-auto">
          <LanguageSelector className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm transition-colors focus:border-brand-primary focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300" />
          <motion.button
            whileHover={allowRichMotion ? { scale: 1.1, rotate: 15 } : undefined}
            whileTap={allowRichMotion ? { scale: 0.9 } : undefined}
            type="button"
            onClick={toggleDarkMode}
            className="rounded-xl bg-slate-100 p-2.5 text-slate-500 transition-colors dark:bg-slate-800 dark:text-slate-400"
            aria-label={t('common.themeToggle')}
          >
            <AnimatePresence mode="wait" initial={false}>
              <motion.div
                key={resolvedTheme}
                initial={allowRichMotion ? { y: -20, opacity: 0, rotate: -90 } : { opacity: 0 }}
                animate={allowRichMotion ? { y: 0, opacity: 1, rotate: 0 } : { opacity: 1 }}
                exit={allowRichMotion ? { y: 20, opacity: 0, rotate: 90 } : { opacity: 0 }}
                transition={{ duration: allowRichMotion ? 0.2 : 0.12 }}
              >
                {resolvedTheme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
              </motion.div>
            </AnimatePresence>
          </motion.button>
          
          <div className="hidden items-center gap-4 sm:flex">
            <MotionLink 
              whileHover={allowRichMotion ? { y: -2 } : undefined}
              whileTap={allowRichMotion ? { scale: 0.95 } : undefined}
              to="/login" 
              className="cursor-pointer px-4 py-2 font-medium transition-colors hover:text-brand-primary"
            >
              {t('landing.logIn')}
            </MotionLink>
            <MotionLink 
              whileHover={allowRichMotion ? { scale: 1.05, y: -2 } : undefined}
              whileTap={allowRichMotion ? { scale: 0.95 } : undefined}
              to="/register" 
              className="cursor-pointer rounded-xl bg-brand-cta px-5 py-2.5 text-sm font-medium text-white shadow-[0_4px_12px_rgba(34,197,94,0.25)] transition-all hover:shadow-[0_6px_16px_rgba(34,197,94,0.35)]"
            >
              {t('landing.signUpFree')}
            </MotionLink>
          </div>
        </div>
      </motion.header>

      <main>
        <section className="relative mx-auto max-w-7xl px-4 pb-24 pt-16 text-center sm:px-6 sm:pb-32 sm:pt-20">
          <motion.div 
            animate={allowRichMotion ? { scale: [1, 1.05, 1], opacity: [0.5, 0.8, 0.5] } : undefined}
            transition={allowRichMotion ? { duration: 8, repeat: Infinity, ease: "easeInOut" } : undefined}
            className="pointer-events-none absolute left-1/2 top-1/2 -z-10 h-[600px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-brand-primary/10 blur-[120px] dark:bg-brand-secondary/5" 
          />

          <motion.div 
            variants={sectionVariants}
            initial="hidden"
            animate="show"
          >
            <motion.div variants={revealVariant} className="mb-8 inline-flex items-center gap-2 rounded-full border border-blue-100 bg-blue-50 px-3 py-1 text-sm font-medium text-brand-primary dark:border-blue-800/50 dark:bg-blue-900/30 dark:text-blue-400">
              <motion.div animate={allowRichMotion ? { rotate: [0, 10, -10, 0] } : undefined} transition={allowRichMotion ? { repeat: Infinity, duration: 2, ease: "easeInOut" } : undefined}>
                <Sparkles size={16} />
              </motion.div>
              <span>{t('landing.badge')}</span>
            </motion.div>

            <motion.h1 variants={revealVariant} className="mb-6 text-5xl font-heading font-bold leading-[1.1] tracking-tight text-slate-900 dark:text-white md:text-7xl">
              {t('landing.heroTitle')}
            </motion.h1>

            <motion.p variants={revealVariant} className="mx-auto mb-10 max-w-2xl text-lg text-slate-600 dark:text-slate-400 md:text-xl">
              {t('landing.heroSubtitle')}
            </motion.p>

            <motion.div variants={revealVariant} className="flex flex-col items-center justify-center gap-4 sm:flex-row">
              <MotionLink 
                whileHover={allowRichMotion ? { scale: 1.05, y: -2 } : undefined}
                whileTap={allowRichMotion ? { scale: 0.95 } : undefined}
                to="/register" 
                className="flex w-full cursor-pointer items-center justify-center gap-2 rounded-xl bg-brand-cta px-8 py-3.5 text-base font-semibold text-white shadow-[0_4px_12px_rgba(34,197,94,0.25)] transition-shadow hover:shadow-[0_6px_16px_rgba(34,197,94,0.35)] sm:w-auto"
              >
                {t('landing.getStarted')} <ArrowRight size={18} />
              </MotionLink>
              <MotionLink 
                whileHover={allowRichMotion ? { scale: 1.05, y: -2 } : undefined}
                whileTap={allowRichMotion ? { scale: 0.95 } : undefined}
                to="/login" 
                className="w-full cursor-pointer rounded-xl border border-slate-200 bg-white px-8 py-3.5 font-semibold text-slate-700 shadow-sm transition-colors hover:border-slate-300 hover:bg-slate-50 dark:border-slate-800 dark:bg-[#151B2B] dark:text-slate-300 dark:hover:border-slate-700 dark:hover:bg-[#1A2235] sm:w-auto"
              >
                {t('landing.logIn')}
              </MotionLink>
            </motion.div>
          </motion.div>
        </section>

        <section className="border-y border-slate-200/50 bg-white/50 py-20 dark:border-slate-800/50 dark:bg-[#111726]/50 sm:py-24 backdrop-blur-sm">
          <motion.div 
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: "-100px" }}
            variants={sectionVariants}
            className="mx-auto max-w-7xl px-4 sm:px-6"
          >
            <motion.div variants={revealVariant} className="mb-16 text-center">
              <h2 className="mb-4 text-3xl font-heading font-bold text-slate-900 dark:text-white">{t('landing.featuresTitle')}</h2>
              <p className="mx-auto max-w-2xl text-slate-600 dark:text-slate-400">{t('landing.featuresSubtitle')}</p>
            </motion.div>

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {features.map((feature, idx) => (
                <motion.div 
                  key={idx} 
                  variants={cardVariant}
                  whileHover={allowRichMotion ? { y: -8, scale: 1.02 } : undefined}
                  className="glass-card-solid interactive-card rounded-2xl p-6 shadow-sm hover:shadow-xl transition-shadow"
                >
                  <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-brand-primary/10 text-brand-primary dark:bg-brand-primary/20 dark:text-brand-secondary">
                    <feature.icon size={24} />
                  </div>
                  <h3 className="mb-2 text-lg font-bold text-slate-900 dark:text-white">{feature.title}</h3>
                  <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-400">{feature.desc}</p>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </section>

        <section className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-24">
          <motion.div 
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: "-100px" }}
            variants={sectionVariants}
          >
            <motion.div variants={revealVariant} className="mb-16 text-center">
              <h2 className="mb-4 text-3xl font-heading font-bold text-slate-900 dark:text-white">{t('landing.howItWorks')}</h2>
              <p className="text-slate-600 dark:text-slate-400">{t('landing.howItWorksSubtitle')}</p>
            </motion.div>

            <div className="relative grid gap-8 md:grid-cols-3">
              <div className="absolute left-[15%] right-[15%] top-[40px] z-0 hidden h-0.5 bg-gradient-to-r from-brand-primary/10 via-brand-primary/30 to-brand-primary/10 dark:from-slate-800 dark:via-brand-secondary/30 dark:to-slate-800 md:block" />

              {steps.map((step, idx) => (
                <motion.div 
                  key={idx} 
                  variants={revealVariant}
                  whileHover={allowRichMotion ? { scale: 1.05 } : undefined}
                  className="relative z-10 flex flex-col items-center text-center group"
                >
                  <motion.div 
                    whileHover={allowRichMotion ? { rotate: 360 } : undefined}
                    transition={allowRichMotion ? { duration: 0.6 } : undefined}
                    className="mb-6 flex h-16 w-16 items-center justify-center rounded-full border-4 border-brand-background bg-white text-xl font-bold text-brand-primary shadow-lg dark:border-[#0B0F19] dark:bg-[#151B2B] dark:text-brand-secondary group-hover:border-brand-primary/30 transition-colors"
                  >
                    {step.num}
                  </motion.div>
                  <h3 className="mb-3 text-xl font-bold text-slate-900 dark:text-white">{step.title}</h3>
                  <p className="text-slate-600 dark:text-slate-400">{step.desc}</p>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </section>

        <section className="bg-brand-primary py-20 text-white sm:py-24 overflow-hidden relative">
          <motion.div 
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: "-50px" }}
            variants={sectionVariants}
            className="mx-auto max-w-7xl px-4 sm:px-6 relative z-10"
          >
            <div className="grid items-center gap-12 md:grid-cols-2">
              <motion.div variants={revealVariant}>
                <h2 className="mb-6 text-3xl font-heading font-bold md:text-4xl">{t('landing.whyTitle')}</h2>
                <p className="mb-8 text-lg leading-relaxed text-blue-100">{t('landing.whySubtitle')}</p>
                <motion.ul variants={sectionVariants} className="space-y-4">
                  {benefits.map((benefit, idx) => (
                    <motion.li key={idx} variants={revealVariant} className="flex items-center gap-3">
                      <CheckCircle className="text-brand-cta shrink-0" size={20} />
                      <span className="font-medium">{benefit}</span>
                    </motion.li>
                  ))}
                </motion.ul>
              </motion.div>
              
              <motion.div 
                variants={cardVariant}
                className="relative"
              >
                <motion.div 
                  animate={allowRichMotion ? { y: [-10, 10, -10] } : undefined}
                  transition={allowRichMotion ? { repeat: Infinity, duration: 6, ease: "easeInOut" } : undefined}
                  className="relative z-10 rounded-2xl border border-white/20 bg-white/10 p-6 shadow-2xl backdrop-blur-md"
                >
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
                </motion.div>
                
                <motion.div 
                  animate={allowRichMotion ? { scale: [1, 1.2, 1], opacity: [0.3, 0.6, 0.3] } : undefined}
                  transition={allowRichMotion ? { duration: 4, repeat: Infinity, ease: "easeInOut" } : undefined}
                  className="absolute -right-6 -top-6 z-0 h-24 w-24 rounded-full bg-brand-cta/50 blur-2xl" 
                />
                <motion.div 
                  animate={allowRichMotion ? { scale: [1, 1.3, 1], opacity: [0.3, 0.5, 0.3] } : undefined}
                  transition={allowRichMotion ? { duration: 5, repeat: Infinity, ease: "easeInOut", delay: 1 } : undefined}
                  className="absolute -bottom-8 -left-8 z-0 h-32 w-32 rounded-full bg-blue-400/40 blur-2xl" 
                />
              </motion.div>
            </div>
          </motion.div>
          
          <div className="pointer-events-none absolute left-0 right-0 top-0 h-full w-full bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-white/5 to-transparent mix-blend-overlay"></div>
        </section>

        <section className="mx-auto max-w-4xl px-4 py-20 text-center sm:px-6 sm:py-32">
          <motion.div
            initial="hidden"
            whileInView="show"
            viewport={{ once: true }}
            variants={staggerContainer}
          >
            <motion.h2 
              variants={revealVariant}
              className="mb-6 text-3xl font-heading font-bold text-slate-900 dark:text-white md:text-5xl"
            >
              {t('landing.readyTitle')}
            </motion.h2>
            <motion.p variants={revealVariant} className="mb-10 text-xl text-slate-600 dark:text-slate-400">
              {t('landing.readySubtitle')}
            </motion.p>
            <motion.div variants={revealVariant}>
              <MotionLink 
                whileHover={allowRichMotion ? { scale: 1.05, y: -4 } : undefined}
                whileTap={allowRichMotion ? { scale: 0.95 } : undefined}
                to="/register" 
                className="inline-flex cursor-pointer items-center gap-2 rounded-xl bg-brand-cta px-8 py-4 font-bold text-white shadow-[0_4px_12px_rgba(34,197,94,0.25)] transition-shadow hover:shadow-[0_8px_24px_rgba(34,197,94,0.4)]"
              >
                {t('landing.createFreeAccount')} <ArrowRight size={20} />
              </MotionLink>
            </motion.div>
          </motion.div>
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
          <div className="flex gap-6">
            <MotionLink 
              whileHover={allowRichMotion ? { y: -2, color: 'var(--color-brand-primary)' } : undefined}
              to="/login" 
              className="text-sm font-medium text-slate-500 transition-colors"
            >
              {t('landing.logIn')}
            </MotionLink>
            <MotionLink 
              whileHover={allowRichMotion ? { y: -2, color: 'var(--color-brand-primary)' } : undefined}
              to="/register" 
              className="text-sm font-medium text-slate-500 transition-colors"
            >
              {t('auth.createAccount')}
            </MotionLink>
          </div>
        </div>
      </footer>
    </div>
  );
}
