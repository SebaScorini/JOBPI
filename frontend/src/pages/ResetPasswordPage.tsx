import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { KeyRound, Loader2, CheckCircle2, Circle } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { useToast } from '../context/ToastContext';
import { getPasswordRequirementState } from '../utils/validation';
import { supabase } from '../lib/supabase';
import type { EmailOtpType } from '@supabase/supabase-js';

export function ResetPasswordPage() {
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isValidToken, setIsValidToken] = useState(false);
  const [isCheckingToken, setIsCheckingToken] = useState(true);

  const { updatePassword } = useAuth();
  const { t } = useLanguage();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const passwordRequirements = getPasswordRequirementState(password);
  const passwordRequirementItems = [
    { key: 'minLength', label: t('auth.passwordRequirementMinLength'), met: passwordRequirements.minLength },
    { key: 'uppercase', label: t('auth.passwordRequirementUppercase'), met: passwordRequirements.uppercase },
    { key: 'lowercase', label: t('auth.passwordRequirementLowercase'), met: passwordRequirements.lowercase },
    { key: 'digit', label: t('auth.passwordRequirementNumber'), met: passwordRequirements.digit },
  ];

  useEffect(() => {
    let isMounted = true;

    const applyRecoveryState = (valid: boolean, message?: string) => {
      if (!isMounted) return;
      setIsValidToken(valid);
      if (message) {
        setError(message);
      }
      setIsCheckingToken(false);
    };

    const resolveRecoverySession = async () => {
      const searchParams = new URLSearchParams(window.location.search);
      const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ''));
      const tokenHash = searchParams.get('token_hash');
      const type = searchParams.get('type');
      const hashError = hashParams.get('error_description') || hashParams.get('error');

      if (hashError) {
        applyRecoveryState(false, decodeURIComponent(hashError));
        return;
      }

      if (tokenHash && type) {
        const { error: verifyError } = await supabase.auth.verifyOtp({
          token_hash: tokenHash,
          type: type as EmailOtpType,
        });

        if (verifyError) {
          applyRecoveryState(false, verifyError.message);
          return;
        }
      }

      const {
        data: { session },
      } = await supabase.auth.getSession();

      applyRecoveryState(!!session);
    };

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, nextSession) => {
      if (event === 'PASSWORD_RECOVERY' || (event === 'SIGNED_IN' && nextSession)) {
        applyRecoveryState(true);
      }
    });

    void resolveRecoverySession();

    return () => {
      isMounted = false;
      subscription.unsubscribe();
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError(t('auth.passwordsDoNotMatch') || 'Passwords do not match.');
      return;
    }

    if (!passwordRequirements.minLength || !passwordRequirements.uppercase ||
        !passwordRequirements.lowercase || !passwordRequirements.digit) {
      setError(t('auth.passwordRequirementsNotMet') || 'Please meet all password requirements.');
      return;
    }

    setIsLoading(true);

    try {
      await updatePassword(password);
      showToast(t('auth.passwordUpdated') || 'Password updated successfully!', 'success');
      navigate('/dashboard', { replace: true });
    } catch (err: any) {
      const message = err?.message || 'Failed to update password.';
      setError(message);
      showToast(message, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  if (isCheckingToken) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 size={32} className="animate-spin text-brand-primary" />
      </div>
    );
  }

  if (!isValidToken) {
    return (
      <div className="space-y-6 text-center animate-in fade-in duration-300">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-rose-100 dark:bg-rose-950/60">
          <KeyRound size={32} className="text-rose-600 dark:text-rose-400" />
        </div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          {t('auth.invalidResetLink') || 'Invalid or expired link'}
        </h2>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          {t('auth.invalidResetLinkDescription') || 'This password reset link is invalid or has expired. Please request a new one.'}
        </p>
        <button
          onClick={() => navigate('/forgot-password')}
          className="btn-primary mt-4 inline-flex items-center justify-center gap-2"
        >
          {t('auth.requestNewLink') || 'Request New Link'}
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5 animate-in fade-in duration-300">
      <div className="text-center">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          {t('auth.resetPassword') || 'Set a new password'}
        </h2>
        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
          {t('auth.resetPasswordDescription') || 'Enter your new password below.'}
        </p>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm font-medium text-rose-600">
          {error}
        </div>
      )}

      <div>
        <label htmlFor="new-password" className="mb-2 block text-sm font-semibold">
          {t('auth.newPassword') || 'New Password'}
        </label>
        <input
          id="new-password"
          type="password"
          value={password}
          onChange={(e) => {
            setPassword(e.target.value);
            if (error) setError('');
          }}
          className="input-field"
          placeholder="Enter new password"
        />
        <div className="mt-3 rounded-2xl border border-slate-200 bg-gradient-to-br from-slate-50 to-white p-4 shadow-sm dark:border-slate-800 dark:from-slate-900 dark:to-slate-950">
          <ul className="space-y-2">
            {passwordRequirementItems.map((item) => {
              const Icon = item.met ? CheckCircle2 : Circle;
              return (
                <li
                  key={item.key}
                  className={`flex items-center gap-3 rounded-xl border px-3 py-2 text-sm transition-all ${
                    item.met
                      ? 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300'
                      : 'border-slate-200 bg-white text-slate-500 dark:border-slate-800 dark:bg-slate-950/60 dark:text-slate-400'
                  }`}
                >
                  <Icon size={16} className={item.met ? 'shrink-0' : 'shrink-0 opacity-70'} />
                  <span className={item.met ? 'font-medium' : ''}>{item.label}</span>
                </li>
              );
            })}
          </ul>
        </div>
      </div>

      <div>
        <label htmlFor="confirm-password" className="mb-2 block text-sm font-semibold">
          {t('auth.confirmPassword') || 'Confirm Password'}
        </label>
        <input
          id="confirm-password"
          type="password"
          value={confirmPassword}
          onChange={(e) => {
            setConfirmPassword(e.target.value);
            if (error) setError('');
          }}
          className="input-field"
          placeholder="Confirm new password"
        />
      </div>

      <button type="submit" disabled={isLoading} className="btn-primary mt-2 flex items-center justify-center gap-2">
        {isLoading ? <Loader2 size={18} className="animate-spin" /> : <KeyRound size={18} />}
        {isLoading
          ? (t('auth.updatingPassword') || 'Updating...')
          : (t('auth.updatePassword') || 'Update Password')}
      </button>
    </form>
  );
}
