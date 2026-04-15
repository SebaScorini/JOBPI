import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Mail, Loader2, ArrowLeft, MailCheck } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { useToast } from '../context/ToastContext';

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [emailSent, setEmailSent] = useState(false);

  const { resetPassword } = useAuth();
  const { t } = useLanguage();
  const { showToast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!email.trim() || !email.includes('@')) {
      setError(t('auth.enterValidEmail') || 'Please enter a valid email address.');
      return;
    }

    setIsLoading(true);

    try {
      await resetPassword(email.trim());
      setEmailSent(true);
    } catch (err: any) {
      const message = err?.message || 'Failed to send password reset email.';
      setError(message);
      showToast(message, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  if (emailSent) {
    return (
      <div className="space-y-6 text-center animate-in fade-in zoom-in-95 duration-300">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-950/60">
          <MailCheck size={32} className="text-blue-600 dark:text-blue-400" />
        </div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          {t('auth.resetEmailSent') || 'Reset link sent'}
        </h2>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          {t('auth.resetEmailSentDescription') || "If an account with that email exists, we've sent a password reset link to "}
          <strong className="text-slate-700 dark:text-slate-200">{email}</strong>.
        </p>
        <Link
          to="/login"
          className="btn-primary mt-4 inline-flex items-center justify-center gap-2"
        >
          <ArrowLeft size={16} />
          {t('auth.backToLogin') || 'Back to Sign In'}
        </Link>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5 animate-in fade-in duration-300">
      <div className="text-center">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          {t('auth.forgotPassword') || 'Forgot your password?'}
        </h2>
        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
          {t('auth.forgotPasswordDescription') || "Enter your email and we'll send you a link to reset your password."}
        </p>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm font-medium text-rose-600">
          {error}
        </div>
      )}

      <div>
        <label htmlFor="forgot-email" className="mb-2 block text-sm font-semibold">
          {t('auth.emailAddress')}
        </label>
        <input
          id="forgot-email"
          type="email"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            if (error) setError('');
          }}
          className="input-field"
          placeholder="user@example.com"
        />
      </div>

      <button type="submit" disabled={isLoading} className="btn-primary mt-2 flex items-center justify-center gap-2">
        {isLoading ? <Loader2 size={18} className="animate-spin" /> : <Mail size={18} />}
        {isLoading
          ? (t('auth.sendingResetLink') || 'Sending...')
          : (t('auth.sendResetLink') || 'Send Reset Link')}
      </button>

      <p className="mt-6 text-center text-sm font-medium text-slate-500">
        <Link to="/login" className="text-brand-primary hover:underline inline-flex items-center gap-1">
          <ArrowLeft size={14} />
          {t('auth.backToLogin') || 'Back to Sign In'}
        </Link>
      </p>
    </form>
  );
}
