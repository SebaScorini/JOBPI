import React, { useState } from 'react';
import { Outlet, NavLink } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import {
  Briefcase,
  FileText,
  ClipboardList,
  LayoutDashboard,
  LogOut,
  Moon,
  Sun,
  Menu,
  X,
  User,
} from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { LanguageSelector } from '../LanguageSelector';
import { useAppTheme } from '../../context/AppThemeContext';
import { OnboardingOverlay } from '../OnboardingOverlay';
import { motion, AnimatePresence } from 'framer-motion';
import { PageTransition } from './PageTransition';
import { useMotionPreferences } from '../../hooks/useMotionPreferences';

export function AppLayout() {
  const { user, logout } = useAuth();
  const { t } = useLanguage();
  const { resolvedTheme, toggleDarkMode } = useAppTheme();
  const [isSidebarOpen, setSidebarOpen] = useState(false);
  const { allowRichMotion } = useMotionPreferences();

  const handleLogout = () => {
    logout();
    window.location.assign('/');
  };

  const navItems = [
    { to: '/dashboard', icon: LayoutDashboard, label: t('nav.dashboard') },
    { to: '/jobs', icon: Briefcase, label: t('nav.jobAnalysis') },
    { to: '/library', icon: FileText, label: t('nav.cvLibrary') },
    { to: '/tracker', icon: ClipboardList, label: t('nav.tracker') },
  ];

  const toggleSidebar = () => setSidebarOpen(!isSidebarOpen);
  const closeSidebar = () => setSidebarOpen(false);

  return (
    <div className="min-h-screen bg-brand-background dark:bg-[#0B0F19] transition-colors duration-500 flex selection:bg-brand-primary/20">
      <OnboardingOverlay />
      {/* Mobile overlay */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/30 backdrop-blur-sm z-40 lg:hidden"
          onClick={closeSidebar}
        />
      )}

      {/* Sidebar */}
      <AnimatePresence>
        <motion.aside
          initial={false}
          animate={{ x: isSidebarOpen ? 0 : 'calc(-100% - 1rem)' }}
          transition={
            allowRichMotion
              ? { type: 'spring', stiffness: 300, damping: 30 }
              : { duration: 0.18, ease: 'easeOut' }
          }
          className={`fixed lg:static inset-y-0 left-0 z-50 w-64 glass-card-solid border-r flex flex-col lg:!transform-none ${
            isSidebarOpen ? '' : '-translate-x-full lg:translate-x-0'
          }`}
        >
        <div className="p-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-brand-primary/10 flex items-center justify-center">
              <span className="w-2 h-2 rounded-full bg-brand-primary animate-pulse"></span>
            </div>
            <span className="font-heading font-bold text-xl tracking-tight text-brand-text dark:text-white">
              JobPi
            </span>
          </div>
          <button onClick={closeSidebar} className="lg:hidden text-slate-500">
            <X size={20} />
          </button>
        </div>

        <nav className="flex-1 px-4 space-y-2 relative z-10">
          <p className="px-2 text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
            {t('nav.menu')}
          </p>
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={closeSidebar}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl font-medium transition-all duration-200 ${
                  isActive
                    ? 'bg-brand-primary text-white shadow-md'
                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-brand-primary dark:hover:text-brand-secondary'
                }`
              }
            >
              <item.icon size={18} />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-slate-200 dark:border-slate-800 relative z-10">
          <div className="flex items-center gap-3 px-2 mb-4">
            <div className="w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-700 flex items-center justify-center flex-shrink-0">
              <User size={16} className="text-slate-500 dark:text-slate-400" />
            </div>
            <div className="overflow-hidden">
                <p className="text-sm font-semibold truncate text-brand-text dark:text-slate-200">
                {user?.email ?? t('common.signedIn')}
              </p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 w-full px-3 py-2 rounded-xl text-sm font-medium text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-900/10 transition-colors"
          >
            <LogOut size={16} />
            {t('nav.signOut')}
          </button>
        </div>
        </motion.aside>
      </AnimatePresence>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0 h-screen relative z-10">
        <header className="h-16 border-b border-slate-200/50 dark:border-slate-800/50 glass-card bg-white/70 dark:bg-[#151B2B]/70 flex items-center justify-between px-4 lg:px-8 sticky top-0 z-30">
          <button
            onClick={toggleSidebar}
            className="lg:hidden p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
          >
            <Menu size={20} />
          </button>
          
          <div className="flex items-center gap-4 ml-auto">
            <LanguageSelector
              className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm transition-colors focus:border-brand-primary focus:outline-none dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
            />
            <button
              onClick={toggleDarkMode}
              className="p-2.5 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:text-brand-primary dark:hover:text-brand-secondary hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
              aria-label={t('common.themeToggle')}
            >
              {resolvedTheme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-3 lg:p-5 relative">
          <div className="w-full h-full">
            <PageTransition>
              <Outlet />
            </PageTransition>
          </div>
        </div>
      </main>
    </div>
  );
}
